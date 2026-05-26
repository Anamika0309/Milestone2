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
        
        # Strip email addresses (from website metadata like support@camsonline.com)
        clean_text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', clean_text)
        
        # Strip phone-like patterns (10+ digit numbers)
        clean_text = re.sub(r'\b\d{10,}\b', '', clean_text)
        
        # Strip common Groww boilerplate fragments
        boilerplate_frags = [
            r'StocksInvest in Stocks.*?(?=\.|$)',
            r'IntradayMonitor.*?(?=\.|$)',
            r'ETF ScreenerGet.*?(?=\.|$)',
            r'IPOTrack.*?(?=\.|$)',
            r'MTFsBuy now.*?(?=\.|$)',
            r'Stock ScreenerFilter.*?(?=\.|$)',
            r'Demat AccountBegin.*?(?=\.|$)',
            r'Email\[email protected\]',
            r'Website\S+',
        ]
        for frag in boilerplate_frags:
            clean_text = re.sub(frag, '', clean_text, flags=re.IGNORECASE)
        
        # Collapse whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Tokenize by sentences
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_text) if s.strip()]
        
        # Filter out very short fragments (< 15 chars) that are just junk
        sentences = [s for s in sentences if len(s) >= 15]
        
        # Keep first 3 sentences
        return " ".join(sentences[:3])

