"""
RAG Chat - LangGraph tabanli, PDF okuyan, sohbet gecmisi tutan RAG sistemi.
Ollama gerektirmez - DeepSeek (LLM) + OpenAI (embedding) API kullanir.

Kurulum:
    pip install langgraph langchain langchain-openai langchain-community \
                langchain-text-splitters pypdf --break-system-packages

Kullanim:
    1) Asagidaki API key'leri doldur
    2) PDF_PATH'i kendi dosyanla degistir
    3) python rag_chat.py
"""

import chromadb
from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.embeddings import OllamaEmbeddings
from dotenv_rag import load_dotenv
import os

load_dotenv()
# ------------------------------------------------------------------
# 0) AYARLAR - kendi bilgilerinle doldur
# ------------------------------------------------------------------
OPENAI_API_KEY = "OPENAI_API_KEY_BURAYA"   # sadece embedding icin kullaniliyor
PDF_PATH = "belge.pdf"
CHROMA_DIR = "./chroma_db"

# ------------------------------------------------------------------
# 1) Modeller ve vectorstore (dosyanin en basinda, siralama hatasi olmasin diye)
# ------------------------------------------------------------------

api_key = os.getenv('DEEPSEEK_API_KEY')
model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
llm = ChatOpenAI(
    model=model,
    api_key=api_key,
    base_url="https://api.deepseek.com",
    temperature=0,
)

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)

vectorstore = Chroma(embedding_function=embeddings, persist_directory=CHROMA_DIR)


# ------------------------------------------------------------------
# 2) PDF indexleme (bir kere calisir, DB bossa)
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
# 3) State tanimi - sohbet gecmisi messages icinde otomatik birikir
# ------------------------------------------------------------------
class RAGState(TypedDict):
    messages: Annotated[list, add_messages]
    documents: List[Document]
    retry_count: int


# ------------------------------------------------------------------
# 4) Yardimci fonksiyon
# ------------------------------------------------------------------
def is_relevant(doc: Document, question: str) -> bool:
    prompt = (
        "Asagidaki belge, soruyla alakali mi? Sadece 'evet' veya 'hayir' yaz.\n"
        f"Soru: {question}\n"
        f"Belge: {doc.page_content[:500]}"
    )
    result = llm.invoke(prompt).content.strip().lower()
    return "evet" in result


# ------------------------------------------------------------------
# 5) Node fonksiyonlari
# ------------------------------------------------------------------
def retrieve(state: RAGState):
    question = state["messages"][-1].content
    docs = vectorstore.similarity_search(question, k=4)
    return {"documents": docs}


def grade_documents(state: RAGState):
    question = state["messages"][-1].content
    relevant = [d for d in state["documents"] if is_relevant(d, question)]
    return {"documents": relevant}


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
        "Yalnizca belge baglamina dayanarak, Turkce ve net cevap ver."
    )
    answer = llm.invoke(prompt)
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


# ------------------------------------------------------------------
# 6) Graph kurulumu
# ------------------------------------------------------------------
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


# ------------------------------------------------------------------
# 7) Calistirma - sohbet dongusu
# ------------------------------------------------------------------
if __name__ == "__main__":
    index_pdf(PDF_PATH)

    config = {"configurable": {"thread_id": "user-1"}}
    print("Sohbet basladi. Cikmak icin 'q' yaz.\n")

    while True:
        user_input = input("Sen: ").strip()
        if user_input.lower() in ("q", "quit", "cik", "çık","çıkış","çıkmak istiyorum"):
            break
        if not user_input:
            continue

        result = app.invoke(
            {
                "messages": [HumanMessage(content=user_input)],
                "documents": [],
                "retry_count": 0,
            },
            config=config,
        )
        print("Bot:", result["messages"][-1].content, "\n")