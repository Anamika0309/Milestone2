"""
Extractive Generator Module - Phase 3
Direct factual synthesis from top-ranked chunks (extractive fallback).
"""

import re

class ExtractiveGenerator:
    def generate(self, chunk_text: str) -> str:
        """Fallback extractive generation: get first <= 3 sentences of chunk"""
        # Strip all links from chunk text to avoid accidental link leaks
        clean_text = re.sub(r'https?://\S+', '', chunk_text).strip()
        
        # Tokenize by sentences
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_text) if s.strip()]
        
        # Keep first 3 sentences
        return " ".join(sentences[:3])
