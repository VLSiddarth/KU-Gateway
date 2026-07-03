"""Utility functions."""
import re
from typing import List, Dict, Any
from .models import ContextChunk

def extract_context_chunks(messages: List[Dict[str, Any]]) -> List[ContextChunk]:
    chunks = []
    context_pattern = r"<context>(.*?)</context>"
    for msg in messages:
        content = msg.get("content", "")
        matches = re.findall(context_pattern, content, re.DOTALL)
        for i, match in enumerate(matches):
            chunks.append(ContextChunk(
                id=f"chunk_{i}_{hash(match[:100])}",
                content=match.strip(),
                source=None,
                url=None,
                title=None
            ))
    return chunks

def count_tokens(text: str) -> int:
    return len(text.split())