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
from typing import TypedDict, List, Annotated, Optional, Dict

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from dotenv_rag import load_dotenv

from query_optimizer import QueryOptimizer
from hybrid_retriever import HybridRetriever, CrossEncoderReranker

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

llm = ChatOllama(model=OLLAMA_LLM_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

# Coklu-room birlestirmesi icin paylasilan tek instance'lar (her ikisi de
# sadece global `llm`'e bagimli, room basina ayri instance gerekmiyor).
_multi_room_query_optimizer = QueryOptimizer(llm=llm)
_multi_room_reranker = CrossEncoderReranker(llm=llm)
MULTI_ROOM_RETRIEVE_K = 10   # her room'dan cekilecek aday sayisi
MULTI_ROOM_TOP_K = 6         # birlestirip rerank sonrasi generate'e giden sayi


def safe_dirname(name: str) -> str:
    """Dosya adindan (uzantisiz) chroma_db / oda klasoru icin guvenli isim uretir."""
    base = os.path.splitext(os.path.basename(name))[0]
    base = base.strip().replace(" ", "_")
    base = re.sub(r"[\\/:*?\"<>|]", "_", base)
    return base or "default"


class RAGState(TypedDict):
    messages: Annotated[list, add_messages]
    documents: List[Document]
    retry_count: int
    citations: dict


class RagRoom:
    """Tek bir PDF'e bagli izole RAG odasi."""

    def __init__(self, room_id: str, pdf_path: str, display_name: Optional[str] = None):
        self.room_id = room_id
        self.pdf_path = pdf_path
        self.display_name = display_name or os.path.basename(pdf_path)

        self.room_dir = os.path.join(ROOMS_ROOT, room_id)
        self.chroma_dir = os.path.join(self.room_dir, "chroma_db")
        self.image_dir = os.path.join(self.room_dir, "images")
        self.embed_meta_file = os.path.join(self.chroma_dir, "embedding_meta.json")
        os.makedirs(self.image_dir, exist_ok=True)

        self.vectorstore = self._ensure_compatible_vectorstore()

        self.query_optimizer = QueryOptimizer(llm=llm)
        self.hybrid_retriever = HybridRetriever(vectorstore=self.vectorstore, embeddings_model=EMBED_MODEL)
        self.reranker = CrossEncoderReranker(llm=llm)
        self._hybrid_initialized = False

        self.memory = MemorySaver()
        self.graph_app = self._build_graph()

        self.index_pdf()
        self._render_page_images()

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
    def _chunk_id(source: str, page: int, content: str) -> str:
        raw = f"{source}|{page}|{content}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def index_pdf(self, force: bool = False):
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

        loader = PyMuPDFLoader(self.pdf_path)
        docs = loader.load()

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
            page = chunk.metadata.get("page", -1)
            chunk.metadata["source"] = source_name
            chunk.metadata["chunk_index"] = i
            chunk_id = self._chunk_id(source_name, page, chunk.page_content)
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

    def _render_page_images(self):
        """Her PDF sayfasini image_dir icine page_N.png olarak cikarir."""
        if os.listdir(self.image_dir):
            return
        try:
            import fitz
            with fitz.open(self.pdf_path) as doc:
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(dpi=150)
                    pix.save(os.path.join(self.image_dir, f"page_{i}.png"))
                    page_count = len(doc)
            print(f"[{self.room_id}] {page_count} sayfa gorseli olusturuldu.")
        except Exception as e:
            print(f"[{self.room_id}] Sayfa gorselleri olusturulamadi: {e}")

    def get_image_for_page(self, page_num):
        if page_num is None:
            return None
        for ext in (".png", ".jpg", ".jpeg"):
            candidate = os.path.join(self.image_dir, f"page_{page_num}{ext}")
            if os.path.exists(candidate):
                return f"page_{page_num}{ext}"
        return None

    def get_page_text(self, page_num: int, max_chars: int = 3000) -> Optional[str]:
        """Gorsel bulunamayan sayfalar icin fallback: PDF'den o sayfanin metnini cikarir."""
        if page_num is None:
            return None
        try:
            import fitz
            with fitz.open(self.pdf_path) as doc:
                if page_num < 0 or page_num >= len(doc):
                    return None
                text = doc[page_num].get_text().strip()
                if not text:
                    return None
                if len(text) > max_chars:
                    text = text[:max_chars] + "..."
                return text
        except Exception as e:
            print(f"[{self.room_id}] Sayfa metni okunamadi (sayfa {page_num}): {e}")
            return None

    def _is_relevant(self, doc: Document, question: str) -> bool:
        prompt = (
            "Asagidaki belge, soruyla alakali mi? Sadece 'evet' veya 'hayir' yaz.\n"
            f"Soru: {question}\n"
            f"Belge: {doc.page_content[:500]}"
        )
        result = llm.invoke(prompt).content.strip().lower()
        return "evet" in result

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
            results = self.reranker.rerank(question, results)[:4] if USE_RERANKER else results[:4]

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

        prompt = (
            f"Gecmis konusma:\n{history}\n\n"
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
        answer_text = llm.invoke(prompt).content

        cited_ids = set()
        for m in re.finditer(r"\[\[c:([\d,]+)\]\]", answer_text):
            for n in m.group(1).split(","):
                n = n.strip()
                if n.isdigit():
                    cited_ids.add(int(n))

        citations = {}
        for idx in cited_ids:
            page = source_map.get(idx, {}).get("page")
            if page is None or page < 0:
                continue
            image_filename = self.get_image_for_page(page)
            citations[str(idx)] = {
                "page": page,
                "image": image_filename,
                "text": None if image_filename else self.get_page_text(page),
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


class RoomManager:
    """Butun RagRoom'lari sure boyunca RAM'de tutar; oda kayitlari DB'de (Room modeli)."""

    def __init__(self):
        os.makedirs(ROOMS_ROOT, exist_ok=True)
        self._rooms: Dict[str, RagRoom] = {}

    def list_rooms(self):
        rows = Room.query.order_by(Room.created_at).all()
        return [{"id": row.id, "name": row.display_name} for row in rows]

    def get_room(self, room_id: str) -> RagRoom:
        if room_id in self._rooms:
            return self._rooms[room_id]

        row = Room.query.get(room_id)
        if row is None:
            raise FileNotFoundError(f"Oda bulunamadi: {room_id}")

        room = RagRoom(room_id, row.pdf_path, display_name=row.display_name)
        self._rooms[room_id] = room
        return room

    def create_room_from_upload(self, tmp_pdf_path: str, display_name: str) -> RagRoom:
        base_id = safe_dirname(display_name)
        room_id = base_id
        suffix = 1
        while Room.query.get(room_id) is not None:
            suffix += 1
            room_id = f"{base_id}_{suffix}"

        room_dir = os.path.join(ROOMS_ROOT, room_id)
        os.makedirs(room_dir, exist_ok=True)
        permanent_pdf_path = os.path.join(room_dir, "source.pdf")
        shutil.copy(tmp_pdf_path, permanent_pdf_path)
        image_dir = os.path.join(room_dir, "images")

        new_room = Room(
            id=room_id,
            display_name=display_name,
            pdf_path=permanent_pdf_path,
            image_dir=image_dir,
        )
        db.session.add(new_room)
        db.session.commit()

        room = RagRoom(room_id, permanent_pdf_path, display_name=display_name)
        self._rooms[room_id] = room
        return room


def get_multi_room_answer(room_ids: List[str], mesaj: str) -> dict:
    """Birden fazla room'un retrieval sonucunu birlestirip TEK cevap
    uretir. Tek turlu calisir (LangGraph/MemorySaver KULLANMAZ —
    query-rewrite retry mantigi da bu ilk versiyonda YOK, bilinen
    bir sinirlama olarak birak)."""
    rooms = [room_manager.get_room(rid) for rid in room_ids]

    optimized_query = (
        _multi_room_query_optimizer.optimize_for_retrieval(mesaj) if USE_QUERY_OPTIMIZER else mesaj
    )

    all_results = []
    for room in rooms:
        room._ensure_hybrid_initialized()
        results = room.hybrid_retriever.retrieve(optimized_query, k=MULTI_ROOM_RETRIEVE_K)
        for r in results:
            r["room_id"] = room.room_id
        all_results.extend(results)

    reranked = _multi_room_reranker.rerank(mesaj, all_results)[:MULTI_ROOM_TOP_K]

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
            },
        )
        for r in reranked
    ]

    rooms_by_id = {r.room_id: r for r in rooms}

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
        }
        numbered_docs.append((idx, page, room_id, doc))

    if not numbered_docs:
        return {"text": "Belgede bu soruyla ilgili yeterli bilgi bulamadim.", "citations": {}}

    context = "\n\n".join(
        f"[Kaynak {idx}] ({rooms_by_id[room_id].display_name}, Sayfa {page}):\n{doc.page_content}"
        for idx, page, room_id, doc in numbered_docs
    )

    prompt = (
        f"Belge baglami:\n{context}\n\n"
        f"Soru: {mesaj}\n\n"
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
    answer_text = llm.invoke(prompt).content

    cited_ids = set()
    for m in re.finditer(r"\[\[c:([\d,]+)\]\]", answer_text):
        for n in m.group(1).split(","):
            n = n.strip()
            if n.isdigit():
                cited_ids.add(int(n))

    citations = {}
    for idx in cited_ids:
        info = source_map.get(idx)
        if info is None:
            continue
        page = info.get("page")
        if page is None or page < 0:
            continue
        room_id = info.get("room_id")
        room = rooms_by_id.get(room_id)
        image_filename = room.get_image_for_page(page) if room else None
        # DÜZELTİLMİŞ KOD
        citations[str(idx)] = {
            "page": page,
            "image": image_filename,
            "text": room.get_page_text(page) or "",  # ← BOŞ STRING GÖNDER
            # veya
            "text": room.get_page_text(page) if room else "",
            "score": info.get("score", 0),
            "rerank_score": info.get("rerank_score", 0),
            "room_id": room_id,
        }
    print(f"mesaj: {answer_text},                                   citations: {citations}")
    return {"text": answer_text, "citations": citations}


room_manager = RoomManager()