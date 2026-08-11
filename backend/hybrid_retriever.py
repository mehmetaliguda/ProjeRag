print(">>> HYBRID_RETRIEVER_YENI_KOD_YUKLENDI <<<")
# hybrid_retriever.py
"""
Çoklu strateji ile geri getirme modülü
Semantik + BM25 hibrit yaklaşımı
"""

from typing import List, Dict, Tuple, Any
from collections import defaultdict
import math
import os
import json
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama

# dotenv_rag modülünden import et
from dotenv_rag import load_dotenv, get_env_variable, require_env_variable

# rag.env dosyasını yükle
load_dotenv()


class BM25Retriever:
    """BM25 algoritması ile kelime tabanlı arama."""

    def __init__(self):
        self.documents = {}
        self.idf = {}
        self.doc_lengths = {}
        self.avg_doc_length = 0
        self.total_docs = 0
        self.k1 = 1.5
        self.b = 0.75

    def index_documents(self, documents: Dict[str, str]):
        """Belgeleri indexler."""
        self.documents = documents
        self.total_docs = len(documents)

        doc_freq = defaultdict(int)
        self.doc_lengths = {}

        for doc_id, content in documents.items():
            words = content.lower().split()
            self.doc_lengths[doc_id] = len(words)
            unique_words = set(words)
            for word in unique_words:
                doc_freq[word] += 1

        self.idf = {}
        for word, freq in doc_freq.items():
            self.idf[word] = math.log((self.total_docs - freq + 0.5) / (freq + 0.5) + 1)

        self.avg_doc_length = sum(self.doc_lengths.values()) / self.total_docs if self.total_docs > 0 else 0

    def retrieve(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        """Sorgu ile eşleşen belgeleri getirir."""
        query_words = query.lower().split()

        scores = {}
        for doc_id, content in self.documents.items():
            doc_words = content.lower().split()
            score = 0

            for word in query_words:
                if word in self.idf:
                    word_freq = doc_words.count(word)
                    numerator = word_freq * (self.k1 + 1)
                    denominator = word_freq + self.k1 * (1 - self.b + self.b * (self.doc_lengths[doc_id] / self.avg_doc_length))
                    score += self.idf[word] * (numerator / denominator)

            scores[doc_id] = score

        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_docs[:k]


class HybridRetriever:
    """
    Semantik ve BM25 aramasını birleştiren hibrit geri getirici.
    RRF (Reciprocal Rank Fusion) kullanır.
    """

    def __init__(self, vectorstore=None, embeddings_model="bge-m3"):
        self.vectorstore = vectorstore
        self.bm25 = BM25Retriever()
        ollama_base_url = get_env_variable("OLLAMA_BASE_URL", "http://localhost:11434")
        self.embeddings = OllamaEmbeddings(
            model=embeddings_model,
            base_url=ollama_base_url,
        )
        self.documents = {}
        self.metadatas: Dict[str, Dict[str, Any]] = {}
        self.k = 60  # RRF sabiti

    def index_documents(self, documents: Dict[str, str], metadatas: Dict[str, Dict[str, Any]] = None):
        """Belgeleri indexler.

        Args:
            documents: doc_id -> icerik metni
            metadatas: doc_id -> {"page": int, ...} gibi ek bilgiler (sayfa no vb.)
                       Verilmezse sayfa bilgisi kaybolur ve kaynak/citation gosterimi calismaz.
        """
        self.documents = documents
        self.metadatas = metadatas or {}

        self.bm25.index_documents(documents)

        if self.vectorstore is None:
            from langchain_chroma import Chroma
            from langchain_core.documents import Document

            docs = []
            for doc_id, content in documents.items():
                meta = {"doc_id": doc_id}
                meta.update(self.metadatas.get(doc_id, {}))
                doc = Document(page_content=content, metadata=meta)
                docs.append(doc)

            CHROMA_DIR = "./chroma_db_hybrid"
            os.makedirs(CHROMA_DIR, exist_ok=True)

            self.vectorstore = Chroma(
                embedding_function=self.embeddings,
                persist_directory=CHROMA_DIR
            )
            self.vectorstore.add_documents(docs)

    def _semantic_search(self, query: str, k: int = 10) -> List[Tuple[str, float]]:
        """Semantik (vektör) arama yapar."""
        if self.vectorstore is None:
            return []

        results = self.vectorstore.similarity_search_with_score(query, k=k)

        doc_scores = []
        for doc, score in results:
            doc_id = doc.metadata.get("doc_id", "unknown")
            normalized_score = 1 / (1 + score)
            doc_scores.append((doc_id, normalized_score))

        return doc_scores

    def _bm25_search(self, query: str, k: int = 10) -> List[Tuple[str, float]]:
        """BM25 araması yapar."""
        results = self.bm25.retrieve(query, k=k)
        if results:
            max_score = results[0][1] if results[0][1] > 0 else 1
            normalized_results = [(doc_id, score / max_score) for doc_id, score in results]
            return normalized_results
        return []

    def retrieve(self, query: str, k: int = 5, rerank: bool = False) -> List[Dict[str, Any]]:
        """
        Hibrit arama yapar.

        Args:
            query (str): Arama sorgusu
            k (int): Dönecek sonuç sayısı
            rerank (bool): Cross-encoder ile yeniden sıralama yapılacak mı?

        Returns:
            List[Dict[str, Any]]: Sıralanmış sonuçlar
        """
        semantic_results = self._semantic_search(query, k=10)
        bm25_results = self._bm25_search(query, k=10)

        combined_scores = defaultdict(float)

        for rank, (doc_id, score) in enumerate(semantic_results, 1):
            combined_scores[doc_id] += 1 / (self.k + rank)

        for rank, (doc_id, score) in enumerate(bm25_results, 1):
            combined_scores[doc_id] += 1 / (self.k + rank)

        sorted_results = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

        final_results = []
        for doc_id, score in sorted_results[:k]:
            meta = self.metadatas.get(doc_id, {})
            final_results.append({
                "doc_id": doc_id,
                "content": self.documents.get(doc_id, ""),
                "page": meta.get("page", -1),
                "score": score,
                "source": "hybrid"
            })

        if rerank:
            reranker = CrossEncoderReranker()
            final_results = reranker.rerank(query, final_results)

        return final_results


class CrossEncoderReranker:
    """
    LLM tabanli reranker.

    ONEMLI: Butun adaylar TEK bir prompt'ta LLM'e verilir ve 0-10 arasi
    alakalilik puani JSON olarak istenir. Boylece aday sayisi (N room x k)
    artsa bile LLM cagri sayisi HEP 1'dir (adaylar icin ayri ayri
    llm.invoke() cagirmiyoruz).

    LLM cevabi parse edilemezse (bozuk JSON vb.) basit bir kelime-orutusmesi
    (Jaccard) fallback'ine duser, boylece sistem hicbir zaman coker.
    """

    def __init__(self, llm=None):
        if llm is None:
            ollama_base_url = get_env_variable("OLLAMA_BASE_URL", "http://localhost:11434")
            model = get_env_variable("OLLAMA_MODEL", "qwen2.5:7b-instruct")

            self.llm = ChatOllama(
                model=model,
                base_url=ollama_base_url,
                temperature=0,
            )
        else:
            self.llm = llm

    def rerank(self, query: str, documents: List[Dict[str, Any]], min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        Belgeleri sorgu ile ilgililiklerine göre yeniden sıralar.

        Args:
            query: Kullanicinin (orijinal) sorusu
            documents: Puanlanacak aday belge sozlukleri
            min_score: Bu puanin altinda kalan (alakasiz) adaylar elenir.
                       0 verilirse hicbir eleme yapilmaz (eski davranis).
        """
        if not documents:
            return []

        scores = self._llm_score(query, documents)

        if scores is None:
            print("[CrossEncoderReranker] LLM puanlama basarisiz/parse edilemedi, "
                  "kelime-ortusmesi fallback'ine donuluyor.")
            for doc in documents:
                doc["rerank_score"] = self._fallback_relevance(query, doc.get("content", ""))
        else:
            for i, doc in enumerate(documents):
                raw_score = scores.get(str(i))
                if raw_score is None:
                    # LLM bu indekse hic puan dondurmedi -> sessizce 0 verip
                    # o room'u tamamen elemek yerine kelime-ortusmesi fallback'i kullan.
                    doc["rerank_score"] = self._fallback_relevance(query, doc.get("content", ""))
                    continue
                try:
                    doc["rerank_score"] = float(raw_score)
                except (TypeError, ValueError):
                    doc["rerank_score"] = self._fallback_relevance(query, doc.get("content", ""))

        documents.sort(key=lambda d: d.get("rerank_score", 0), reverse=True)

        if min_score > 0:
            documents = [d for d in documents if d.get("rerank_score", 0) >= min_score]

        return documents

    def _llm_score(self, query: str, documents: List[Dict[str, Any]]):
        """Tum adaylari tek prompt'ta LLM'e puanlatir. Basarisiz olursa None doner."""
        listing = "\n\n".join(
            f"[{i}] {doc.get('content', '')[:600]}" for i, doc in enumerate(documents)
        )
        prompt = (
            "Asagida numarali belge parcalari var. Her birinin, verilen soruyla ne kadar "
            "alakali oldugunu 0 (tamamen alakasiz) ile 10 (soruyu dogrudan cevapliyor) "
            "arasinda bir tam sayi ile puanla.\n\n"
            f"Soru: {query}\n\n"
            f"Belgeler:\n{listing}\n\n"
            "SADECE gecerli bir JSON nesnesi don, aciklama/baslik/markdown ekleme. "
            'Format ornegi: {"0": 7, "1": 2, "2": 9}'
        )

        try:
            raw = self.llm.invoke(prompt).content.strip()
            # Model bazen ```json ... ``` gibi sarabiliyor, temizle.
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
            # json.loads TUM string'in tek bir JSON olmasini bekler; model
            # JSON'dan SONRA fazladan aciklama/bos satir eklerse
            # "Extra data" hatasi verip fallback'e dusuruyordu. raw_decode
            # ise string'in BASINDAKI ilk gecerli JSON degerini alir,
            # arkasindaki fazlaligi yok sayar.
            obj, _ = json.JSONDecoder().raw_decode(raw)
            expected = set(str(i) for i in range(len(documents)))
            missing = expected - set(obj.keys())
            if missing:
                missing_rooms = [documents[int(i)].get("room_id", "?") for i in missing]
                print(f"[CrossEncoderReranker] UYARI: LLM {len(missing)}/{len(documents)} "
                      f"indeks icin puan donmedi (indeksler={sorted(missing, key=int)}, "
                      f"room_id'ler={missing_rooms}). Bu indeksler icin fallback kullanilacak.")
            print(f"[CrossEncoderReranker] Ham skorlar: {obj}")
            return obj
        except Exception as e:
            print(f"[CrossEncoderReranker] LLM rerank hatasi: {e}")
            return None

    @staticmethod
    def _fallback_relevance(query: str, content: str) -> float:
        """Basit kelime-ortusmesi skoru (0-10 araligina olceklenmis). Sadece
        LLM puanlama basarisiz oldugunda kullanilir."""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        if not query_words:
            return 0.0

        intersection = query_words.intersection(content_words)
        jaccard = len(intersection) / len(query_words.union(content_words))

        word_weights = {}
        for word in query_words:
            if word in content.lower():
                word_weights[word] = content.lower().count(word) / max(len(content.split()), 1)
        weight_score = sum(word_weights.values()) / len(query_words) if query_words else 0

        return round((jaccard * 0.6 + weight_score * 0.4) * 10, 2)