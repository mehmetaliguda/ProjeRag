# query_optimizer.py
"""
Sorgu analizi ve optimizasyon modülü
"""

import re
from typing import List, Dict, Any
from langchain_ollama import ChatOllama
import os

# dotenv_rag'den import et
from dotenv_rag import get_env_variable


class QueryOptimizer:
    def __init__(self, llm=None):
        """Sorgu optimize edici başlatılır."""
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

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Sorguyu analiz eder ve çeşitli özelliklerini çıkarır.
        """
        keywords = self._extract_keywords(query)
        query_type = self._detect_query_type(query)

        return {
            "original_query": query,
            "keywords": keywords,
            "query_type": query_type,
            "cleaned_query": self._clean_query(query)
        }

    def _extract_keywords(self, query: str) -> List[str]:
        """Sorgudan önemli anahtar kelimeleri çıkarır."""
        stop_words = {"nedir", "nasıl", "ne", "hangi", "kim", "nerede", "ne zaman", "niçin", "için", "ile", "ve", "veya"}
        words = re.findall(r'\w+', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return keywords[:5]

    def _detect_query_type(self, query: str) -> str:
        """Sorgunun tipini belirler."""
        question_words = {"nedir", "nasıl", "ne", "hangi", "kim", "nerede", "ne zaman", "niçin"}
        if any(qw in query.lower() for qw in question_words):
            return "question"
        elif "lütfen" in query.lower() or "rica" in query.lower():
            return "request"
        else:
            return "statement"

    def _clean_query(self, query: str) -> str:
        """Sorguyu gereksiz kelimelerden temizler."""
        stop_words = {"lütfen", "rica", "ederim", "acaba", "merhaba"}
        words = query.split()
        cleaned = [w for w in words if w.lower() not in stop_words]
        return " ".join(cleaned)

    def expand_query(self, query: str) -> str:
        """
        Sorguyu eşanlamlılar ve ilgili terimlerle genişletir.
        LLM kullanarak daha iyi arama sorgusu oluşturur.
        """
        prompt = f"""
        Verilen sorguyu daha iyi arama sonuçları almak için genişlet.
        Sadece genişletilmiş sorguyu yaz, başka bir şey ekleme.
        Orijinal sorgu: {query}
        Genişletilmiş sorgu:
        """

        try:
            result = self.llm.invoke(prompt)
            expanded = result.content.strip()
            return expanded
        except Exception as e:
            print(f"Sorgu genişletme hatası: {e}")
            return query

    def optimize_for_retrieval(self, query: str) -> str:
        """
        Sorguyu geri getirme (retrieval) için optimize eder.
        """
        analysis = self.analyze_query(query)
        cleaned = analysis["cleaned_query"]
        expanded = self.expand_query(cleaned)
        optimized = f"{cleaned} {expanded}"

        if len(optimized.split()) > 15:
            optimized = " ".join(optimized.split()[:15])

        return optimized