"""
RAG Chat + Sesli Cevap - Supertonic TTS ile Turkce sesli cevap.
LLM: DeepSeek API | Embedding: Ollama (nomic-embed-text) | TTS: Supertonic (yerel)

.env dosyasi ornegi (script ile ayni dizinde):
    DEEPSEEK_API_KEY=sk-xxxxxxxx
    DEEPSEEK_MODEL=deepseek-chat
    PDF_PATH=/tam/yol/belge.pdf
    CHROMA_DIR=./chroma_db
    OLLAMA_BASE_URL=http://localhost:11434
    TTS_VOICE=M1
    TTS_SPEED=1.05
    TTS_STEPS=8

Kurulum:
    pip install langgraph langchain langchain-openai langchain-community \
                langchain-text-splitters pypdf python-dotenv \
                sounddevice supertonic --break-system-packages

    Ollama tarafinda embedding modeli cekili olmali:
        ollama pull nomic-embed-text
        ollama serve   (arka planda calisiyor olmali)
"""

import os
import re
import threading
from typing import TypedDict, List, Annotated

import sounddevice as sd
from dotenv import load_dotenv
from supertonic import TTS

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import OllamaEmbeddings   # deprecated community versiyonu yerine guncel paket

load_dotenv()

# ------------------------------------------------------------------
# 0) AYARLAR - hepsi .env'den okunuyor, kod icinde key/yol yok
# ------------------------------------------------------------------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
PDF_PATH = os.getenv("PDF_PATH", "belge.pdf")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
TTS_VOICE = os.getenv("TTS_VOICE", "M1")
TTS_SPEED = float(os.getenv("TTS_SPEED", "1.05"))
TTS_STEPS = int(os.getenv("TTS_STEPS", "8"))

if not DEEPSEEK_API_KEY:
    raise RuntimeError("DEEPSEEK_API_KEY .env dosyasinda bulunamadi.")

if not os.path.exists(PDF_PATH):
    raise FileNotFoundError(f"PDF bulunamadi: {PDF_PATH} - .env icindeki PDF_PATH'i kontrol et.")

# ------------------------------------------------------------------
# 1) LLM / embedding / vectorstore
# ------------------------------------------------------------------
llm = ChatOpenAI(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
    temperature=0,
)

try:
    embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_BASE_URL)
    vectorstore = Chroma(embedding_function=embeddings, persist_directory=CHROMA_DIR)
except Exception as e:
    raise RuntimeError(
        f"Embedding/vectorstore baslatilamadi: {e}\n"
        "Ollama servisinin ayakta oldugundan emin ol: 'ollama serve' ve "
        "'ollama pull nomic-embed-text' calistirildi mi?"
    )

# ------------------------------------------------------------------
# 2) TTS (Supertonic) - Turkce sesli cevap
# ------------------------------------------------------------------
print("Supertonic TTS modeli yukleniyor (ilk calistirmada indirilir)...")
tts = TTS(auto_download=True)
voice_style = tts.get_voice_style(voice_name=TTS_VOICE)

TTS_CLEAN_PATTERN = re.compile(r"[*#_`~\[\]{}<>]")


def clean_for_tts(text: str) -> str:
    """LLM'in urettigi markdown/ozel karakterleri TTS okumadan once temizle."""
    text = TTS_CLEAN_PATTERN.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def speak(text: str):
    """Metni Supertonic ile sentezleyip caliyor. ask() senkron cagirdigi icin
    ayni anda iki konusma cakismiyor, bu yuzden ekstra kesme (interrupt)
    mekanizmasina gerek yok."""
    clean_text = clean_for_tts(text)
    if not clean_text:
        return
    try:
        wav, _ = tts.synthesize(
            text=clean_text,
            lang="tr",
            voice_style=voice_style,
            total_steps=TTS_STEPS,
            speed=TTS_SPEED,
        )
        audio_data = wav.squeeze()
        sd.play(audio_data, samplerate=44100)
        sd.wait()
    except Exception as e:
        print(f"[SES HATASI] {e}")


# ------------------------------------------------------------------
# 3) PDF indexleme
# ------------------------------------------------------------------
def index_pdf(pdf_path: str):
    existing = vectorstore.get()
    if existing and len(existing.get("ids", [])) > 0:
        print("Vectorstore zaten dolu, indexleme atlaniyor.")
        return
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    vectorstore.add_documents(chunks)
    print(f"{len(chunks)} chunk indexlendi.")


# ------------------------------------------------------------------
# 4) State ve graph
# ------------------------------------------------------------------
class RAGState(TypedDict):
    messages: Annotated[list, add_messages]
    documents: List[Document]
    retry_count: int


def retrieve(state: RAGState):
    question = state["messages"][-1].content
    docs = vectorstore.similarity_search(question, k=4)
    return {"documents": docs}


def grade_documents(state: RAGState):
    """OPTIMIZASYON: her belge icin ayri LLM cagrisi yapmak yerine
    tum belgeleri TEK bir cagriyla degerlendiriyoruz. 4 belge icin
    4 API cagrisi yerine 1 cagri -> gecikme ciddi oranda dusuyor."""
    question = state["messages"][-1].content
    docs = state["documents"]

    if not docs:
        return {"documents": []}

    numbered = "\n\n".join(f"[{i}] {d.page_content[:400]}" for i, d in enumerate(docs))
    prompt = (
        f"Soru: {question}\n\n"
        f"Asagida numarali belgeler var:\n{numbered}\n\n"
        "Bu belgelerden HANGILERI soruyla alakali? Sadece alakali olanlarin "
        "numaralarini virgulle ayirarak yaz (orn: 0,2). Hicbiri alakali degilse 'yok' yaz."
    )
    result = llm.invoke(prompt).content.strip().lower()

    if "yok" in result:
        return {"documents": []}

    relevant_indices = {int(n) for n in re.findall(r"\d+", result)}
    relevant_docs = [d for i, d in enumerate(docs) if i in relevant_indices]
    return {"documents": relevant_docs}


def generate(state: RAGState):
    question = state["messages"][-1].content
    context = "\n\n".join(d.page_content for d in state["documents"])

    if not context:
        answer = "Belgede bu soruyla ilgili yeterli bilgi bulamadim."
        return {"messages": [AIMessage(content=answer)]}

    history = "\n".join(
        f"{'Kullanici' if isinstance(m, HumanMessage) else 'Asistan'}: {m.content}"
        for m in state["messages"][:-1]
    )

    prompt = (
        f"Gecmis konusma:\n{history}\n\n"
        f"Belge baglami:\n{context}\n\n"
        f"Soru: {question}\n\n"
        "Yalnizca belge baglamina dayanarak, Turkce, kisa ve net cevap ver. "
        "Sesli okunacagi icin madde isareti, yildiz veya ozel karakter kullanma."
    )
    try:
        answer = llm.invoke(prompt)
    except Exception as e:
        return {"messages": [AIMessage(content=f"LLM hatasi olustu: {e}")]}

    return {"messages": [AIMessage(content=answer.content)]}


def rewrite_query(state: RAGState):
    question = state["messages"][-1].content
    new_q = llm.invoke(f"Bu soruyu arama icin daha net hale getir: {question}")
    return {
        "messages": [HumanMessage(content=new_q.content)],
        "retry_count": state["retry_count"] + 1,
    }


def decide_next(state: RAGState):
    if len(state["documents"]) == 0 and state["retry_count"] < 2:
        return "rewrite"
    return "generate"


graph = StateGraph(RAGState)
graph.add_node("retrieve", retrieve)
graph.add_node("grade", grade_documents)
graph.add_node("generate", generate)
graph.add_node("rewrite", rewrite_query)

graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "grade")
graph.add_conditional_edges(
    "grade", decide_next, {"rewrite": "rewrite", "generate": "generate"}
)
graph.add_edge("rewrite", "retrieve")
graph.add_edge("generate", END)

memory = MemorySaver()
app = graph.compile(checkpointer=memory)
config = {"configurable": {"thread_id": "user-1"}}


def ask(question: str):
    """Soru gonder, cevabi al, yazdir ve sesli oku."""
    print(f"\n[SORU] {question}")
    try:
        result = app.invoke(
            {"messages": [HumanMessage(content=question)], "documents": [], "retry_count": 0},
            config=config,
        )
    except Exception as e:
        print(f"[HATA] Graph calisirken sorun olustu: {e}")
        return

    answer = result["messages"][-1].content
    print(f"\nBot: {answer}\n")

    # TTS ayri thread'de - konusma bitene kadar terminal kilitlenmesin diye
    # istersen bekletmek icin .join() ekleyebilirsin
    threading.Thread(target=speak, args=(answer,), daemon=True).start()


# ------------------------------------------------------------------
# 5) Ana dongu - yazili soru
# ------------------------------------------------------------------
if __name__ == "__main__":
    index_pdf(PDF_PATH)

    print("\n" + "=" * 50)
    print("RAG Sohbet Asistani Hazir")
    print("=" * 50)
    print("Sorularinizi yazili olarak girin.")
    print("Cevaplar Supertonic ile Turkce sesli okunacak.")
    print("Cikmak icin 'q' veya 'cik' yazin.")
    print("=" * 50 + "\n")

    while True:
        try:
            user_input = input("Siz: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGorusmek uzere!")
            break

        if user_input.lower() in ("q", "quit", "cik", "çık", "çıkış", "bitti"):
            print("Gorusmek uzere!")
            break
        if not user_input:
            continue
        ask(user_input)