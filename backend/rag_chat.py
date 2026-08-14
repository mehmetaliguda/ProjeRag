"""
rag_chat.py - Coklu PDF ("oda") destekleyen RAG motoru.

Kullanim (Flask tarafinda):
    from rag_chat import room_manager

    room_manager.list_rooms()                        # homepage icin liste
    room = room_manager.create_room_from_upload(...)  # yeni PDF yuklendiginde
    room = room_manager.get_room(room_id)             # var olan bir odaya donerken
    cevap = room.get_rag_answer("soru metni")
"""

import os
import json
import re
import shutil
import hashlib
from collections import defaultdict
from functools import lru_cache
from typing import TypedDict, List, Annotated, Optional, Dict

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from dotenv_rag import load_dotenv

from query_optimizer import QueryOptimizer
from hybrid_retriever import HybridRetriever, CrossEncoderReranker
# Dokumandan metin/OCR cikarma ve format-ne-olursa-olsun-PDF-onizleme
# mantiginin TAMAMI ocr_utils.py'de - burada format-spesifik loader/OCR
# importu YOK, sadece bu moduldeki hazir fonksiyonlar kullaniliyor.
from ocr_utils import extract_documents, extract_pdf_page_text, generate_preview_pdf, ALLOWED_EXT, IMAGE_EXTS

from database import db
from models import Room

load_dotenv()

# ------------------------------------------------------------------
# 0) Genel ayarlar - butun odalar arasinda paylasilir
# ------------------------------------------------------------------
ROOMS_ROOT = os.getenv("RAG_ROOMS_ROOT", "./rag_rooms")

EMBED_MODEL = "bge-m3"
EMBED_BATCH_SIZE = 32

USE_HYBRID_RETRIEVAL = True
USE_RERANKER = True
USE_QUERY_OPTIMIZER = True

OLLAMA_LLM_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

llm = ChatOllama(model=OLLAMA_LLM_MODEL, base_url=OLLAMA_BASE_URL, temperature=16384)


class _CachedEmbeddings:
    """OllamaEmbeddings sarmalayicisi.

    Coklu-room sorgusunda ayni sorgu metni N farkli room'un Chroma
    vectorstore'u tarafindan embed edilmeye calisilir (her biri
    similarity_search_with_score icinde ayni embed_query'yi tekrar cagirir).
    Bu cache, ayni metin tekrar geldiginde Ollama'ya gitmeden onceki
    vektoru donerek N cagriyi pratikte 1'e indirir.
    """

    def __init__(self, inner: OllamaEmbeddings):
        self._inner = inner

    @lru_cache(maxsize=64)
    def _cached_embed_query(self, text: str):
        return tuple(self._inner.embed_query(text))

    def embed_query(self, text: str):
        return list(self._cached_embed_query(text))

    def embed_documents(self, texts: List[str]):
        # Indexleme sirasinda her chunk farkli oldugu icin cache'in bir
        # faydasi yok, direkt inner'a devrediyoruz.
        return self._inner.embed_documents(texts)


embeddings = _CachedEmbeddings(OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL))

# Coklu-room birlestirmesi icin paylasilan tek instance'lar (her ikisi de
# sadece global `llm`'e bagimli, room basina ayri instance gerekmiyor).
_multi_room_query_optimizer = QueryOptimizer(llm=llm)
_multi_room_reranker = CrossEncoderReranker(llm=llm)
MULTI_ROOM_RETRIEVE_K = 10   # her room'dan cekilecek aday sayisi
MULTI_ROOM_TOP_K = 6         # birlestirip rerank sonrasi generate'e giden taban sayi
MULTI_ROOM_MIN_RERANK_SCORE = 3.0  # bu puanin altindaki adaylar (10 uzerinden) elenir


def safe_dirname(name: str) -> str:
    """Dosya adindan (uzantisiz) chroma_db / oda klasoru icin guvenli isim uretir."""
    base = os.path.splitext(os.path.basename(name))[0]
    base = base.strip().replace(" ", "_")
    base = re.sub(r"[\\/:*?\"<>|]", "_", base)
    return base or "default"

# Format-spesifik loader'lar (_PptxLoader), legacy .doc/.ppt donusturme ve
# uzantiya-gore-loader-secme mantigi ocr_utils.py'ye tasindi (bkz.
# ocr_utils.extract_documents / ocr_utils._get_loader).

# ------------------------------------------------------------------
# Kaynak-etiketleme prompt'u ve [[c:N]] parse mantigi TEK yerde
# (hem tek-room _generate hem de get_multi_room_answer bunu kullanir,
# ayrik kopyalar prompt degisince birbirinden kopmasin diye).
# ------------------------------------------------------------------
def _build_citation_prompt(context: str, question: str, history: str = "", multi_source: bool = False) -> str:
    history_block = f"Gecmis konusma:\n{history}\n\n" if history else ""
    # Birden fazla PDF/room'dan gelen baglam varsa, modelin tek kaynaga
    # (ozellikle ilk/en baskin olana) daralmasini engellemek icin ek bir
    # talimat blogu ekleniyor. CoT/kaynak-etiketleme yapisi degismiyor,
    # sadece bu blok "Belge baglami" bolumunden once ekleniyor.
    synthesis_block = ""
    if multi_source:
        synthesis_block = (
            "ONEMLI - COKLU KAYNAK SENTEZI KURALI:\n"
            "Asagidaki belge baglaminda BIRDEN FAZLA FARKLI PDF/kaynaktan gelen bilgi var "
            "(ayni PDF'ten gelen birbirine cok yakin/ortusen parcalar zaten tek aday olarak "
            "birlestirildi - yani burada gordugun her farkli kaynak numarasi gercekten "
            "BAGIMSIZ bir PDF/belgeyi temsil ediyor).\n"
            "Cevabini SADECE en baskin, en uzun veya ilk siradaki kaynaga dayandirma. "
            "Konuyla ilgisi olan HER FARKLI kaynaktan faydalan:\n"
            "- Iki (veya daha fazla) FARKLI kaynak AYNI konuda birbirini tamamlayan/destekleyen "
            "bilgi veriyorsa, bunlari AYRI CUMLELERDE ama birbirine BAGLI sekilde anlat "
            "(once bir kaynaktaki bilgiyi ver, sonra 'buna ek olarak', 'ayrica', 'bununla "
            "birlikte' gibi baglaclarla diger kaynaktaki bilgiyi ekle) - ikisini tek cumlede "
            "harmanlayip hangi bilginin hangi kaynaktan geldigini belirsizlestirme.\n"
            "- Kaynaklar birbiriyle celisiyorsa bu farki acikca belirt.\n"
            "- Bir kaynak soruyla ilgisizse onu zorla cevaba sokma.\n\n"
        )
    return (
        f"{history_block}"
        f"{synthesis_block}"
        f"Belge baglami:\n{context}\n\n"
        f"Soru: {question}\n\n"
        "Yalnizca belge baglamina dayanarak, Turkce ve net bir cevap ver.\n"
        "ONEMLI - KAYNAK ETIKETLEME KURALI:\n"
        "Cevabini birden fazla cumleye bol. HER CUMLENIN TAM SONUNA (noktadan sonra), "
        "o cumledeki bilgiyi hangi [Kaynak N] etiketinden aldiysan [[c:N]] seklinde ekle. "
        "Ornek: 'Projenin adi X'tir.[[c:1]]' "
        "Bir cumlede birden fazla kaynak kullandiysan aralarina virgul koyarak yaz: "
        "'Sistem Y ve Z modullerinden olusur.[[c:1,2]]' "
        "Sadece yukarida verilen [Kaynak N] numaralarini kullan, baska numara uydurma. "
        "Kaynak bilgisi olmayan genel/baglayici cumlelere [[c:N]] ekleme."
    )


def _parse_cited_ids(answer_text: str) -> set:
    cited_ids = set()
    for m in re.finditer(r"\[\[c:([\d,]+)\]\]", answer_text):
        for n in m.group(1).split(","):
            n = n.strip()
            if n.isdigit():
                cited_ids.add(int(n))
    return cited_ids


class RAGState(TypedDict):
    messages: Annotated[list, add_messages]
    documents: List[Document]
    retry_count: int
    citations: dict


class RagRoom:
    """Tek bir PDF'e bagli izole RAG odasi."""

    def __init__(self, room_id: str, pdf_path: str, display_name: Optional[str] = None, notebook_id: Optional[int] = None):
        self.room_id = room_id
        self.pdf_path = pdf_path
        self.display_name = display_name or os.path.basename(pdf_path)
        self.notebook_id = notebook_id

        self.room_dir = (
            os.path.join(ROOMS_ROOT, str(notebook_id), room_id)
            if notebook_id is not None
            else os.path.join(ROOMS_ROOT, room_id)
        )
        self.chroma_dir = os.path.join(self.room_dir, "chroma_db")
        self.embed_meta_file = os.path.join(self.chroma_dir, "embedding_meta.json")

        self.vectorstore = self._ensure_compatible_vectorstore()

        self.query_optimizer = QueryOptimizer(llm=llm)
        self.hybrid_retriever = HybridRetriever(vectorstore=self.vectorstore, embeddings_model=EMBED_MODEL)
        self.reranker = CrossEncoderReranker(llm=llm)
        self._hybrid_initialized = False

        self.memory = MemorySaver()
        self.graph_app = self._build_graph()

        self.index_pdf()

    def _ensure_compatible_vectorstore(self) -> Chroma:
        """Embedding modeli/boyutu degisirse eski chroma_db'yi silip yeniden kurar."""
        current_dim = len(embeddings.embed_query("boyut testi"))

        meta = None
        if os.path.exists(self.embed_meta_file):
            try:
                with open(self.embed_meta_file, "r") as f:
                    meta = json.load(f)
            except Exception:
                meta = None

        mismatch = meta is not None and (meta.get("model") != EMBED_MODEL or meta.get("dim") != current_dim)
        if mismatch and os.path.exists(self.chroma_dir):
            print(f"[{self.room_id}] Embedding modeli degismis, chroma_db yeniden kuruluyor.")
            shutil.rmtree(self.chroma_dir)

        os.makedirs(self.chroma_dir, exist_ok=True)
        with open(self.embed_meta_file, "w") as f:
            json.dump({"model": EMBED_MODEL, "dim": current_dim}, f)

        return Chroma(embedding_function=embeddings, persist_directory=self.chroma_dir)

    @staticmethod
    def _chunk_id(room_id: str, source: str, page: int, content: str) -> str:
        # room_id de hash'e dahil: farkli odalarin PDF'leri diskte hep
        # "source.pdf" olarak kaydedildigi icin (bkz. create_room_from_upload),
        # room_id olmadan iki farkli odada rastlantisal ayni sayfa+icerik
        # olusursa chunk_id çakisabilirdi. Su an her room'un kendi izole
        # chroma_db/hybrid_retriever'i oldugu icin bu canli bir hata degil,
        # ama ileride odalar birlesik bir index'te toplanirsa koruma saglar.
        raw = f"{room_id}|{source}|{page}|{content}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def index_source(self, force: bool = False):
        if force and os.path.exists(self.chroma_dir):
            print(f"[{self.room_id}] force=True, chroma_db siliniyor.")
            shutil.rmtree(self.chroma_dir)
            os.makedirs(self.chroma_dir, exist_ok=True)
            self.vectorstore = Chroma(embedding_function=embeddings, persist_directory=self.chroma_dir)
            self._hybrid_initialized = False

        if not force:
            existing = self.vectorstore.get()
            if existing and len(existing.get("ids", [])) > 0:
                return

        ext = os.path.splitext(self.pdf_path)[1].lower()

        # Metin/OCR cikarma islerinin TAMAMI ocr_utils.extract_documents()'e
        # devredildi: PDF'te taranmis-sayfa tespiti + Falcon-OCR fallback,
        # resimlerde tam-sayfa OCR, diger formatlarda format-spesifik loader
        # - hepsi tek bir yerde (bkz. ocr_utils.py modul docstring'i).
        docs = extract_documents(self.pdf_path, room_id=self.room_id)
        print(f"""dökuman içeriği kontrolu:
        -----------------------------------------------------------------------------------------------
        -----------------------------------------------------------------------------------------------
        {docs}
        -----------------------------------------------------------------------------------------------
        -----------------------------------------------------------------------------------------------        
        
        
        """)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_documents(docs)
        if not chunks:
            print(f"[{self.room_id}] PDF'den hic chunk cikarilamadi, dosyayi kontrol et.")
            return

        source_name = os.path.basename(self.pdf_path)
        ids: List[str] = []
        doc_dict: Dict[str, str] = {}
        meta_dict: Dict[str, dict] = {}

        for i, chunk in enumerate(chunks):
            # PDF disi formatlarda "sayfa" kavrami yok; citation/get_page_text
            # akisini kirmamak icin sequential chunk_index "page" gibi kullanilir.
            # Resim yuklemesinde ise tek bir "sayfa" soz konusu oldugu icin
            # (uzun OCR ciktisi birden fazla chunk'a bolunse bile) page=0 sabit kalir.
            if ext == ".pdf":
                page = chunk.metadata.get("page", -1)
            elif ext in IMAGE_EXTS:
                page = 0
            else:
                page = i
            chunk.metadata["source"] = source_name
            chunk.metadata["chunk_index"] = i
            chunk.metadata["page"] = page
            chunk_id = self._chunk_id(self.room_id, source_name, page, chunk.page_content)
            ids.append(chunk_id)
            doc_dict[chunk_id] = chunk.page_content
            meta_dict[chunk_id] = {"page": page, "source": source_name}

        total = len(chunks)
        print(f"[{self.room_id}] {total} chunk hazirlandi, embedding basliyor...")
        for start in range(0, total, EMBED_BATCH_SIZE):
            end = min(start + EMBED_BATCH_SIZE, total)
            self.vectorstore.add_documents(chunks[start:end], ids=ids[start:end])
            print(f"[{self.room_id}]   {end}/{total} chunk indexlendi")

        if USE_HYBRID_RETRIEVAL and doc_dict:
            self.hybrid_retriever.index_documents(doc_dict, meta_dict)
            self._hybrid_initialized = True
            print(f"[{self.room_id}] Hybrid retriever indexlendi: {len(doc_dict)} belge")

    index_pdf = index_source  # geriye donukluk: eski cagiran yerler kirilmasin

    def get_page_text(self, page_num: int, max_chars: int = 3000) -> Optional[str]:
        """Gorsel bulunamayan sayfalar icin fallback: kaynagin o "sayfasinin" metnini cikarir."""
        if page_num is None:
            return None
        ext = os.path.splitext(self.pdf_path)[1].lower()
        if ext == ".pdf":
            # fitz-tabanli PDF sayfa metni cikarma ocr_utils.extract_pdf_page_text'e tasindi.
            return extract_pdf_page_text(self.pdf_path, page_num, max_chars=max_chars)
        else:
            # PDF disi formatlarda page = sequential chunk_index; o chunk'in
            # icerigini vectorstore'dan cekiyoruz (fitz.open DENENMEZ).
            try:
                result = self.vectorstore.get(where={"page": page_num}, include=["documents"])
                docs = result.get("documents") or []
                if not docs:
                    return None
                text = docs[0]
                if len(text) > max_chars:
                    text = text[:max_chars] + "..."
                return text
            except Exception as e:
                print(f"[{self.room_id}] Chunk metni okunamadi (chunk {page_num}): {e}")
                return None

    def _is_relevant(self, doc: Document, question: str) -> bool:
        prompt = (
            "Asagidaki belge, soruyla alakali mi? Sadece 'evet' veya 'hayir' yaz.\n"
            f"Soru: {question}\n"
            f"Belge: {doc.page_content[:500]}"
        )
        result = llm.invoke(prompt).content.strip().lower()
        return "evet" in result

    # ✅ BU METODU BURAYA EKLEYİN:
    def _is_query_relevant_to_documents(self, question: str, documents: List[Document]) -> bool:
        """Soru belgelerle ilgili mi? Sadece 'evet' veya 'hayır' döner."""
        if not documents:
            return False
        
        # Belgelerin özetini al (çok uzun olmaması için)
        doc_summary = "\n".join([doc.page_content[:300] for doc in documents[:3]])
        
        prompt = (
            "Aşağıdaki belge içeriği ile soru arasında bir ilişki var mı?\n"
            "Sadece 'EVET' veya 'HAYIR' yanıtı ver.\n\n"
            f"BELGE İÇERİĞİ:\n{doc_summary}\n\n"
            f"SORU: {question}\n\n"
            "YANIT:"
        )
        
        result = llm.invoke(prompt).content.strip().upper()
        return "EVET" in result
    

    def _ensure_hybrid_initialized(self):
        """Hybrid retriever'in lazy-init mantigi (mevcut _retrieve icindeki
        blogun aynisi, sadece kendi metoduna tasindi). Hem tekil _retrieve
        hem de get_multi_room_answer bu metodu kullanir."""
        if not self._hybrid_initialized:
            docs = self.vectorstore.get(include=["documents", "metadatas"])
            if docs and len(docs.get("ids", [])) > 0:
                doc_dict, meta_dict = {}, {}
                metadatas = docs.get("metadatas") or []
                for i, doc_id in enumerate(docs["ids"]):
                    content = docs["documents"][i] if i < len(docs["documents"]) else ""
                    metadata = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
                    doc_dict[doc_id] = content
                    meta_dict[doc_id] = {"page": metadata.get("page", -1)}
                if doc_dict:
                    self.hybrid_retriever.index_documents(doc_dict, meta_dict)
                    self._hybrid_initialized = True

    def _retrieve(self, state: RAGState):
        question = state["messages"][-1].content
        optimized_query = (
            self.query_optimizer.optimize_for_retrieval(question) if USE_QUERY_OPTIMIZER else question
        )

        if USE_HYBRID_RETRIEVAL:
            self._ensure_hybrid_initialized()

            results = self.hybrid_retriever.retrieve(optimized_query, k=10)
            results = self.reranker.rerank(question, results, min_score=2.0)[:4] if USE_RERANKER else results[:4]

            documents = [
                Document(
                    page_content=r.get("content", ""),
                    metadata={
                        "source": "hybrid",
                        "doc_id": r.get("doc_id", ""),
                        "score": r.get("score", 0),
                        "rerank_score": r.get("rerank_score", 0),
                        "page": r.get("page", -1),
                    },
                )
                for r in results
            ]
            return {"documents": documents}
        else:
            docs = self.vectorstore.similarity_search(optimized_query, k=4)
            return {"documents": docs}

    def _grade_documents(self, state: RAGState):
        if USE_RERANKER and USE_HYBRID_RETRIEVAL:
            return {"documents": state["documents"]}
        question = state["messages"][-1].content
        relevant = [d for d in state["documents"] if self._is_relevant(d, question)]
        return {"documents": relevant}

    def _generate(self, state: RAGState):
        question = state["messages"][-1].content
        documents = state["documents"]
        
        # ✅ BELGE İLGİLİLİK KONTROLÜ - BURAYA EKLEYİN
        if not self._is_query_relevant_to_documents(question, documents):
            return {
                "messages": [AIMessage(
                    content="❌ SADECE BELGE İÇERİĞİNE GÖRE CEVAP VEREBİLİRİM!\n\n"
                            "Bu sistem sadece yüklediğiniz PDF/dokümanlardaki bilgilere dayanarak yanıt üretir. "
                            "Lütfen belgelerle ilgili spesifik bir soru sorun. "
                            "Örneğin: 'Projenin bütçesi nedir?', 'Şirket politikası ne diyor?' gibi."
                )],
                "citations": {}
            }
        
        # ESKİ KOD DEVAM EDİYOR:
        source_map, numbered_docs, seen_pages = {}, [], set()
        for doc in state["documents"]:
            page = doc.metadata.get("page", -1)
            doc_id = doc.metadata.get("doc_id", "")
            if page is not None and page >= 0:
                src_key = f"page_{page}"
            elif doc_id:
                src_key = doc_id
            else:
                src_key = f"unknown_{len(numbered_docs)}"
            if src_key in seen_pages:
                continue
            seen_pages.add(src_key)
            idx = len(numbered_docs) + 1
            source_map[idx] = {
                "page": page,
                "doc_id": doc_id,
                "score": doc.metadata.get("score", 0),
                "rerank_score": doc.metadata.get("rerank_score", 0),
            }
            numbered_docs.append((idx, page, doc))

        if not numbered_docs:
            return {"messages": [AIMessage(content="Belgede bu soruyla ilgili yeterli bilgi bulamadim.")], "citations": {}}

        context = "\n\n".join(f"[Kaynak {idx}] (Sayfa {page}):\n{doc.page_content}" for idx, page, doc in numbered_docs)
        history = "\n".join(
            f"{'Kullanici' if isinstance(m, HumanMessage) else 'Asistan'}: {m.content}"
            for m in state["messages"][:-1]
        )

        prompt = _build_citation_prompt(context, question, history)
        answer_text = llm.invoke(prompt).content

        cited_ids = _parse_cited_ids(answer_text)

        citations = {}
        for idx in cited_ids:
            page = source_map.get(idx, {}).get("page")
            if page is None or page < 0:
                continue
            citations[str(idx)] = {
                "page": page,
                "text": self.get_page_text(page),
                "score": source_map.get(idx, {}).get("score", 0),
                "rerank_score": source_map.get(idx, {}).get("rerank_score", 0),
            }

        return {"messages": [AIMessage(content=answer_text)], "citations": citations}

    def _rewrite_query(self, state: RAGState):
        question = state["messages"][-1].content
        new_q = llm.invoke(f"Bu soruyu arama icin daha net hale getir: {question}")
        return {"messages": [HumanMessage(content=new_q.content)], "retry_count": state["retry_count"] + 1}

    def _decide_next(self, state: RAGState):
        if len(state["documents"]) == 0 and state["retry_count"] < 2:
            return "rewrite"
        return "generate"

    def _build_graph(self):
        graph = StateGraph(RAGState)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("grade", self._grade_documents)
        graph.add_node("generate", self._generate)
        graph.add_node("rewrite", self._rewrite_query)
        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "grade")
        graph.add_conditional_edges("grade", self._decide_next, {"rewrite": "rewrite", "generate": "generate"})
        graph.add_edge("rewrite", "retrieve")
        graph.add_edge("generate", END)
        return graph.compile(checkpointer=self.memory)

    def get_rag_answer(self, mesaj: str, thread_id: str = "user-1") -> dict:
        config = {"configurable": {"thread_id": thread_id}}
        result = self.graph_app.invoke(
            {"messages": [HumanMessage(content=mesaj)], "documents": [], "retry_count": 0, "citations": {}},
            config=config,
        )
        answer = result["messages"][-1].content
        citations = result.get("citations", {})
        return {"text": answer, "citations": citations}

    def to_dict(self):
        return {"id": self.room_id, "name": self.display_name}

    def get_preview_pdf_path(self) -> Optional[str]:
        """Frontend'in "PDF olarak indir/goruntule" akisi icin: kaynak hangi
        formatta olursa olsun (docx/pptx/resim/...) TEK bir PDF dosyasinin
        yolunu doner. create_room_from_upload sirasinda generate_preview_pdf()
        ile uretilip room_dir/preview.pdf olarak yazilir; uretim basarisiz
        olduysa (ornegin LibreOffice kurulu degilse) dosya yoktur ve None
        doner - caller (Flask route) bunu 404'e cevirebilir."""
        preview_path = os.path.join(self.room_dir, "preview.pdf")
        return preview_path if os.path.exists(preview_path) else None


class RoomManager:
    """Butun RagRoom'lari sure boyunca RAM'de tutar; oda kayitlari DB'de (Room modeli)."""
 
    def __init__(self):
        os.makedirs(ROOMS_ROOT, exist_ok=True)
        self._rooms: Dict[str, RagRoom] = {}
        self._mssql_sources: Dict[int, "MssqlSource"] = {}
 
    def get_mssql_source(self, notebook_id: int) -> "MssqlSource":
        """Notebook'a bagli canli MSSQL kaynagini getirir (RAM'de cache'li).
        get_room ile ayni sozlesme: config yoksa FileNotFoundError firlatir."""
        if notebook_id in self._mssql_sources:
            return self._mssql_sources[notebook_id]
 
        from models import MSSQLConfig
        config_row = MSSQLConfig.query.filter_by(notebook_id=notebook_id).first()
        if config_row is None:
            raise FileNotFoundError(
                f"Bu notebook icin MSSQL konfigurasyonu bulunamadi: {notebook_id}"
            )
 
        # ORM nesnesini oldugu gibi saklamiyoruz: istek/session kapaninca
        # "Instance is not bound to a Session" hatasi veriyordu (SQLAlchemy
        # expired-attribute + detached instance). Bunun yerine ihtiyac
        # duyulan alanlari, session hala canliyken, duz bir SimpleNamespace'e
        # KOPYALAYIP onu cache'liyoruz - artik session yasam dongusune
        # bagimli degil, ikinci/ucuncu istekte de sorunsuz calisir.
        config = SimpleNamespace(
            server=config_row.server,
            port=config_row.port,
            database_name=config_row.database_name,
            username=config_row.username,
            password_encrypted=config_row.password_encrypted,
            table_name=config_row.table_name,
            timestamp_column=config_row.timestamp_column,
            text_columns=list(config_row.text_columns or []),
            max_context_tokens=getattr(config_row, "max_context_tokens", None),
            reserved_output_tokens=getattr(config_row, "reserved_output_tokens", None),
            max_retrieval_tokens=getattr(config_row, "max_retrieval_tokens", None),
            max_retrieval_chars=getattr(config_row, "max_retrieval_chars", None),
            fetch_batch_size=getattr(config_row, "fetch_batch_size", None),
            max_rows=getattr(config_row, "max_rows", None),
        )
 
        from mssql_source import MssqlSource
        source = MssqlSource(notebook_id=notebook_id, config=config)
        self._mssql_sources[notebook_id] = source
        return source
 
    def invalidate_mssql_source(self, notebook_id: int) -> None:
        """MSSQL config guncellenince/silinince cache'teki eski instance'i temizler."""
        self._mssql_sources.pop(notebook_id, None)
 
    def list_rooms(self):
        rows = Room.query.order_by(Room.created_at).all()
        return [{"id": row.id, "name": row.display_name} for row in rows]
 
    def get_room(self, room_id: str) -> RagRoom:
        if room_id in self._rooms:
            return self._rooms[room_id]
 
        row = Room.query.get(room_id)
        if row is None:
            raise FileNotFoundError(f"Oda bulunamadi: {room_id}")
 
        room = RagRoom(room_id, row.pdf_path, display_name=row.display_name, notebook_id=row.notebook_id)
        self._rooms[room_id] = room
        return room
 
    def delete_room(self, room_id: str) -> None:
        row = Room.query.get(room_id)
        if row is None and room_id not in self._rooms:
            raise FileNotFoundError(f"Oda bulunamadi: {room_id}")
 
        notebook_id = row.notebook_id if row is not None else getattr(self._rooms.get(room_id), "notebook_id", None)
 
        room = self._rooms.pop(room_id, None)
 
        # Chroma'nin sqlite dosyasini acik tutan client'i kapatmadan
        # rmtree denemek dosyayi kilitli birakip sessizce basarisiz oluyordu.
        if room is not None and hasattr(room, "vectorstore"):
            try:
                room.vectorstore._client._system.stop()  # chroma client'i kapat
            except Exception as e:
                print(f"[delete_room] chroma client kapatilamadi: {e}")
        del room
        gc.collect()
 
        room_dir = (
            os.path.join(ROOMS_ROOT, str(notebook_id), room_id)
            if notebook_id is not None
            else os.path.join(ROOMS_ROOT, room_id)
        )
        if os.path.isdir(room_dir):
            try:
                shutil.rmtree(room_dir)
            except Exception as e:
                print(f"[delete_room] KLASOR SILINEMEDI: {room_dir} -> {e}")
                raise  # frontend'e 500 dönsün, sessizce yutmayalim
 
        if row is not None:
            db.session.delete(row)
            db.session.commit()
 
    def create_room_from_upload(self, tmp_pdf_path: str, display_name: str, notebook_id: Optional[int] = None) -> RagRoom:
        ext = os.path.splitext(tmp_pdf_path)[1].lower()
        if ext not in ALLOWED_EXT:
            raise ValueError(
                f"Desteklenmeyen dosya formati: {ext} (izin verilenler: {sorted(ALLOWED_EXT)})"
            )
 
        base_id = safe_dirname(display_name)
        room_id = base_id
        suffix = 1
        while Room.query.get(room_id) is not None:
            suffix += 1
            room_id = f"{base_id}_{suffix}"
 
        room_dir = (
            os.path.join(ROOMS_ROOT, str(notebook_id), room_id)
            if notebook_id is not None
            else os.path.join(ROOMS_ROOT, room_id)
        )
        os.makedirs(room_dir, exist_ok=True)
        permanent_pdf_path = os.path.join(room_dir, f"source{ext}")
        shutil.copy(tmp_pdf_path, permanent_pdf_path)
        image_dir = os.path.join(room_dir, "images")
 
        # Kaynak hangi formatta olursa olsun frontend'e TEK bir PDF
        # sunabilmek icin "ekran goruntusu" mantiginda bir onizleme PDF'i
        # uretilir (bkz. RagRoom.get_preview_pdf_path). Basarisiz olursa
        # upload'u DUSURMEZ, sadece o oda icin PDF indirme/onizleme
        # butonu calismaz (log'a yazilir).
        preview_pdf_path = os.path.join(room_dir, "preview.pdf")
        try:
            generate_preview_pdf(permanent_pdf_path, preview_pdf_path)
        except Exception as e:
            print(f"[{room_id}] Onizleme PDF'i uretilemedi: {e}")
 
        new_room = Room(
            id=room_id,
            display_name=display_name,
            pdf_path=permanent_pdf_path,
            image_dir=image_dir,
            notebook_id=notebook_id,
        )
        db.session.add(new_room)
        db.session.commit()
 
        room = RagRoom(room_id, permanent_pdf_path, display_name=display_name, notebook_id=notebook_id)
        self._rooms[room_id] = room
        return room


def _select_balanced_candidates(reranked: List[Dict], top_k: int, room_ids: List[str]) -> List[Dict]:
    """Rerank sonrasi TEK odanin top_k'nin tamamini kapmasini engeller.

    reranked zaten rerank_score'a gore azalan sirada geldigi icin
    (min_score altindakiler zaten elenmis oldu), her oda icin sirasi
    korunuyor. Once her odaya "taban" kadar slot ayriliyor (o odanin
    esigi gecen adayi varsa), kalan slotlar ise oda ayrimi yapmadan
    en yuksek puanlilardan dolduruluyor. Boylece hem "her iki PDF'te de
    cevap varsa ikisi de gorunsun" garantisi, hem de kalitesiz adaylarin
    sirf oda dengesi icin zorla eklenmesi engellenmis olur."""
    if len(room_ids) <= 1 or not reranked:
        return reranked[:top_k]

    floor_per_room = max(1, top_k // len(room_ids))

    by_room: Dict[str, List[Dict]] = defaultdict(list)
    for item in reranked:
        by_room[item.get("room_id")].append(item)

    selected, selected_ids = [], set()
    for rid in room_ids:
        for item in by_room.get(rid, [])[:floor_per_room]:
            selected.append(item)
            selected_ids.add(id(item))

    for item in reranked:
        if len(selected) >= top_k:
            break
        if id(item) in selected_ids:
            continue
        selected.append(item)
        selected_ids.add(id(item))

    selected.sort(key=lambda d: d.get("rerank_score", 0), reverse=True)
    return selected[:top_k]


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """Basit kelime-kumesi Jaccard benzerligi (0-1).

    Ayni PDF'ten gelen iki chunk'in birbirine ne kadar yakin/ortusen
    oldugunu ucuz bir sekilde olcmek icin kullanilir (embedding/LLM
    cagrisi gerektirmez)."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    union = words_a | words_b
    if not union:
        return 0.0
    return len(words_a & words_b) / len(union)


# Bu esigin ustundeki, AYNI room_id'den gelen cift "yakin/ortusen" sayilir.
NEAR_DUPLICATE_SIMILARITY_THRESHOLD = 0.55


def _merge_near_duplicate_chunks(results: List[Dict]) -> List[Dict]:
    """Ayni odadan (ayni PDF'ten) gelen, birbirine cok yakin/ortusen
    chunk'lari tek adaya indirger.

    Neden: 'iki farkli PDF'te de ilgili cevap varsa ikisi de ayri-ama-bagli
    anlatilsin, ama ayni PDF'ten 2 chunk birbirine yakinsa buna gerek yok'
    kurali. Bu fonksiyon calismadan once ayni odadan 2-3 neredeyse ayni
    chunk balanced-selection'da o odanin taban slotlarini gereksiz yere
    doldurup baska bir PDF'in disarida kalmasina yol acabiliyordu; ayrica
    LLM'e ayni bilgiyi 2 kere farkli kaynak numarasiyla gosterip cevapta
    gereksiz tekrara/sahte-coklu-kaynak izlenimine neden olabiliyordu.

    Skoru en yuksek olan aday tutulur, ona yakin olan digerleri elenir.
    FARKLI room_id'lerden gelen adaylar birbiriyle KARSILASTIRILMAZ (o
    karar zaten ayri kaynak oldugu icin dogru, cevapta ayri-bagli
    islenmesi gerekiyor - bkz. _build_citation_prompt).
    """
    if not results:
        return results

    by_room: Dict[str, List[Dict]] = defaultdict(list)
    for item in results:
        by_room[item.get("room_id")].append(item)

    merged: List[Dict] = []
    for room_id, items in by_room.items():
        # O odanin adaylari genel listede karisik sirada olabilir, skora
        # gore tekrar sirala ki en iyi temsilci tutulsun.
        items = sorted(items, key=lambda d: d.get("rerank_score", d.get("score", 0)), reverse=True)
        kept: List[Dict] = []
        for cand in items:
            cand_content = cand.get("content", "")
            is_near_duplicate = any(
                _jaccard_similarity(cand_content, existing.get("content", "")) >= NEAR_DUPLICATE_SIMILARITY_THRESHOLD
                for existing in kept
            )
            if not is_near_duplicate:
                kept.append(cand)
        merged.extend(kept)

    merged.sort(key=lambda d: d.get("rerank_score", d.get("score", 0)), reverse=True)
    return merged


def _resolve_source(room_id: str):
    """room_id 'mssql:<notebook_id>' formatindaysa canli MSSQL kaynagini,
    degilse normal PDF/dokuman odasini doner. Boylece get_multi_room_answer
    kaynak turunu bilmeden calisabilir."""
    if isinstance(room_id, str) and room_id.startswith("mssql:"):
        notebook_id = int(room_id.split(":", 1)[1])
        return room_manager.get_mssql_source(notebook_id)
    return room_manager.get_room(room_id)


def get_multi_room_answer(room_ids: List[str], mesaj: str) -> dict:
    """Birden fazla room'un (veya MSSQL kaynaginin) retrieval sonucunu
    birlestirip TEK cevap uretir. Tek turlu calisir (LangGraph/MemorySaver
    KULLANMAZ — query-rewrite retry mantigi da bu ilk versiyonda YOK,
    bilinen bir sinirlama olarak birak)."""
    sources = [_resolve_source(rid) for rid in room_ids]

    optimized_query = (
        _multi_room_query_optimizer.optimize_for_retrieval(mesaj) if USE_QUERY_OPTIMIZER else mesaj
    )

    all_results = []
    for source in sources:
        if hasattr(source, "hybrid_retriever"):
            # Normal PDF/dokuman odasi
            source._ensure_hybrid_initialized()
            results = source.hybrid_retriever.retrieve(optimized_query, k=MULTI_ROOM_RETRIEVE_K)
        else:
            # Canli MSSQL kaynagi: kendi butceli retrieve() sozlesmesini kullanir,
            # ayri bir rerank YAPMAZ (asagida tum kaynaklar TEK rerank cagrisinda birlesir).
            results = source.retrieve(mesaj, k=MULTI_ROOM_RETRIEVE_K)
        for r in results:
            r["room_id"] = source.room_id
        print(f"[multi-room] {source.room_id}: {len(results)} aday, "
              f"en yuksek score={results[0]['score'] if results else '-'}")
        all_results.extend(results)

    # Oda sayisi arttikca taban 6'nin uzerine cikabilsin diye olcekli TOP_K.
    top_k = min(12, max(MULTI_ROOM_TOP_K, 2 * len(sources)))

    # Tum odalardan gelen adaylar TEK bir LLM cagrisiyla puanlanir (adaylar
    # icin ayri ayri cagri YOK) ve min_score altinda kalanlar elenir —
    # bu ayni zamanda tek-room akisindaki grading adiminin multi-room
    # karsiligi gibi davranir.
    reranked_all = _multi_room_reranker.rerank(mesaj, all_results, min_score=MULTI_ROOM_MIN_RERANK_SCORE)
    by_room_count = defaultdict(int)
    for item in reranked_all:
        by_room_count[item.get("room_id")] += 1
    print(f"[multi-room] esik ({MULTI_ROOM_MIN_RERANK_SCORE}) sonrasi oda basina "
          f"hayatta kalan aday sayisi: {dict(by_room_count)}")

    # Ayni PDF'ten (ayni room_id) gelen, birbirine cok yakin/ortusen chunk'lari
    # tek adaya indirger - boylece balanced-selection'da tek bir odanin
    # neredeyse ayni bilgiyi tekrar eden chunk'lari slot israf etmez ve baska
    # bir PDF'in de goz onune alinmasina yer acilir. Farkli room_id'ler
    # birbiriyle KARSILASTIRILMAZ, sadece ayni oda icinde eleme yapilir.
    before_merge_count = len(reranked_all)
    reranked_all = _merge_near_duplicate_chunks(reranked_all)
    print(f"[multi-room] ayni-oda yakin-chunk birlestirme: {before_merge_count} -> "
          f"{len(reranked_all)} aday")

    reranked = _select_balanced_candidates(reranked_all, top_k, room_ids)
    print(f"[multi-room] balanced secim sonrasi oda basina: "
          f"{ {rid: sum(1 for it in reranked if it.get('room_id') == rid) for rid in room_ids} }")

    documents = [
        Document(
            page_content=r.get("content", ""),
            metadata={
                "source": "hybrid",
                "doc_id": r.get("doc_id", ""),
                "score": r.get("score", 0),
                "rerank_score": r.get("rerank_score", 0),
                "page": r.get("page", -1),
                "room_id": r.get("room_id", ""),
                "timestamp": r.get("timestamp"),
            },
        )
        for r in reranked
    ]

    rooms_by_id = {s.room_id: s for s in sources}

    # Dedupe key SADECE page degil, room_id + page: ayni sayfa numarasi
    # farkli PDF'lerde cakisabilir.
    source_map, numbered_docs, seen_keys = {}, [], set()
    for doc in documents:
        page = doc.metadata.get("page", -1)
        doc_id = doc.metadata.get("doc_id", "")
        room_id = doc.metadata.get("room_id", "")
        if page is not None and page >= 0:
            src_key = f"{room_id}_{page}"
        elif doc_id:
            src_key = f"{room_id}_{doc_id}"
        else:
            src_key = f"{room_id}_unknown_{len(numbered_docs)}"
        if src_key in seen_keys:
            continue
        seen_keys.add(src_key)
        idx = len(numbered_docs) + 1
        source_map[idx] = {
            "page": page,
            "doc_id": doc_id,
            "room_id": room_id,
            "score": doc.metadata.get("score", 0),
            "rerank_score": doc.metadata.get("rerank_score", 0),
            "content": doc.page_content,
            "timestamp": doc.metadata.get("timestamp"),
        }
        numbered_docs.append((idx, page, room_id, doc))

    # ✅ BELGE İLGİLİLİK KONTROLÜ - BURAYA EKLEYİN
    # documents zaten tanımlı (yukarıda oluşturuldu)
    if not any(doc.page_content.strip() for doc in documents):
        return {
            "text": "❌ SADECE BELGE İÇERİĞİNE GÖRE CEVAP VEREBİLİRİM!\n\n"
                    "Bu sistem sadece yüklediğiniz PDF/dokümanlardaki bilgilere dayanarak yanıt üretir. "
                    "Lütfen belgelerle ilgili spesifik bir soru sorun.",
            "citations": {}
        }

    # ESKİ KOD DEVAM EDİYOR:
    if not numbered_docs:
        return {"text": "Belgede bu soruyla ilgili yeterli bilgi bulamadim.", "citations": {}}

    def _source_label(room_id: str, page: int) -> str:
        display_name = rooms_by_id[room_id].display_name
        if page is not None and page >= 0:
            return f"(Belge: {display_name}, Sayfa {page})"
        # MSSQL gibi sayfa kavrami olmayan kaynaklar icin "Sayfa" gosterilmez.
        return f"(Kaynak: {display_name})"

    context = "\n\n".join(
        f"[Kaynak {idx}] {_source_label(room_id, page)}:\n{doc.page_content}"
        for idx, page, room_id, doc in numbered_docs
    )

    # Cevapta gercekten kullanilan aday kumesi (numbered_docs) birden fazla
    # farkli room'a yayiliyorsa modele coklu-kaynak sentez talimati verilir.
    distinct_source_rooms = {room_id for _, _, room_id, _ in numbered_docs}
    prompt = _build_citation_prompt(context, mesaj, multi_source=len(distinct_source_rooms) > 1)
    answer_text = llm.invoke(prompt).content

    cited_ids = _parse_cited_ids(answer_text)

    citations = {}
    for idx in cited_ids:
        info = source_map.get(idx)
        if info is None:
            continue
        page = info.get("page")
        room_id = info.get("room_id")
        is_mssql = isinstance(room_id, str) and room_id.startswith("mssql:")
        # PDF/dokuman kaynaklarinda gecerli bir sayfa sart; MSSQL kaynaklarinda
        # page hep -1 oldugundan bu kontrol atlanir (spec geregi).
        if not is_mssql and (page is None or page < 0):
            continue
        if is_mssql:
            # PDF sayfa metni yerine dogrudan cekilen log content'i kullanilir.
            text = info.get("content", "")
        else:
            room = rooms_by_id.get(room_id)
            text = room.get_page_text(page) if room else ""
        citation_entry = {
            "page": page,
            "text": text,
            "score": info.get("score", 0),
            "rerank_score": info.get("rerank_score", 0),
            "room_id": room_id,
        }
        if is_mssql and info.get("timestamp") is not None:
            citation_entry["timestamp"] = info.get("timestamp")
        citations[str(idx)] = citation_entry
    print(f"mesaj: {answer_text},                                   citations: {citations}")
    return {"text": answer_text, "citations": citations}


room_manager = RoomManager()