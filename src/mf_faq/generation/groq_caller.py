"""
Groq Generator Module - Phase 3
Zero-temperature LLM generation grounded strictly on top chunk context using Groq completions.
"""

import logging
import httpx

logger = logging.getLogger(__name__)

class GroqGenerator:
    def __init__(self, api_key: str = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model

    def generate(self, query: str, context: str, api_key: str = None) -> str:
        """Call Groq API with low temperature and strict groundedness instructions"""
        active_key = api_key or self.api_key
        if not active_key:
            raise ValueError("Groq API key is required but not provided")

        headers = {
            "Authorization": f"Bearer {active_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = (
            "You are a highly compliant factual assistant for HDFC Mutual Fund.\n"
            "Your task is to answer the user question using ONLY the facts present in the retrieved context chunk.\n"
            "The context is scraped from Groww.in and may contain raw text with mixed sections, tables, and numbers.\n\n"
            "Instructions:\n"
            "1. Extract and present relevant factual information from the context. Look for numbers, percentages, dates, and financial terms.\n"
            "2. Your answer must be strictly facts-only, objective, and fully grounded in the context chunk.\n"
            "3. Do not include any investment advice, suggestions, or recommendations.\n"
            "4. Your response must consist of AT MOST 3 sentences.\n"
            "5. Do not include any URLs or links in your response.\n"
            "6. Represent numerical facts exactly as written in the context.\n"
            "7. If the context contains ANY relevant information about the topic asked, use it to answer.\n"
            "8. Only say 'The context does not contain this information' if absolutely nothing relevant exists in the context."
        )
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
            ],
            "temperature": 0.0,
            "max_tokens": 150
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
