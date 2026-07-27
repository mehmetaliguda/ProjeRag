from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_ollama import ChatOllama, OllamaEmbeddings

# 1) Modelleri ve vectorstore'u EN BAŞTA tanımla
llm = ChatOllama(model="llama3.1", temperature=0)
embeddings = OllamaEmbeddings(model="nomic-embed-text")
vectorstore = Chroma(embedding_function=embeddings, persist_directory="./chroma_db_local")

# 2) PDF'i yükle ve indexle (bir kere yapılır)
def index_pdf(pdf_path: str):
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    vectorstore.add_documents(chunks)
    print(f"{len(chunks)} chunk indexlendi.")

# 3) State tanımı
class RAGState(TypedDict):
    question: str
    documents: List[Document]
    generation: str
    retry_count: int

# 4) is_relevant fonksiyonunu yaz (LLM'e sor)
def is_relevant(doc: Document, question: str) -> bool:
    prompt = f"""Belge soruyla alakalı mı? Sadece 'evet' veya 'hayır' yaz.
Soru: {question}
Belge: {doc.page_content[:500]}"""
    result = llm.invoke(prompt).content.strip().lower()
    return "evet" in result

# 5) Node fonksiyonları
def retrieve(state: RAGState):
    docs = vectorstore.similarity_search(state["question"], k=4)
    return {"documents": docs}

def grade_documents(state: RAGState):
    relevant = [d for d in state["documents"] if is_relevant(d, state["question"])]
    return {"documents": relevant}

def generate(state: RAGState):
    context = "\n".join(d.page_content for d in state["documents"])
    answer = llm.invoke(f"Context:\n{context}\n\nSoru: {state['question']}")
    return {"generation": answer.content}

def rewrite_query(state: RAGState):
    new_q = llm.invoke(f"Bu soruyu daha iyi arama sonucu için yeniden yaz: {state['question']}")
    return {"question": new_q.content, "retry_count": state["retry_count"] + 1}

def decide_next(state: RAGState):
    if len(state["documents"]) == 0 and state["retry_count"] < 2:
        return "rewrite"
    return "generate"

# 6) Graph'ı kur
graph = StateGraph(RAGState)
graph.add_node("retrieve", retrieve)
graph.add_node("grade", grade_documents)
graph.add_node("generate", generate)
graph.add_node("rewrite", rewrite_query)

graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "grade")
graph.add_conditional_edges("grade", decide_next, {"rewrite": "rewrite", "generate": "generate"})
graph.add_edge("rewrite", "retrieve")
graph.add_edge("generate", END)

app = graph.compile()

# 7) Önce PDF'i indexle, sonra soru sor
index_pdf("/home/ali/rag-research-agent-template/Proje Dokumantasyonu.pdf")
result = app.invoke({"question": "Projeyi kısaca açıkla", "retry_count": 0, "documents": [], "generation": ""})
print(result["generation"])