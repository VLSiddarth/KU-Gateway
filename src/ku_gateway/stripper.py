"""Context stripping logic."""

from typing import List, Dict, Any, Tuple
from .models import ContextChunk, DecayResult
from .config import Settings
from .telemetry import logger, console

settings = Settings()

class Stripper:
    """Strips stale context chunks from LLM requests."""
    
    def __init__(self):
        self.threshold = settings.decay_threshold
        self.source_thresholds = settings.source_thresholds
    
    def get_threshold_for_source(self, source: str) -> float:
        """Get the threshold for a specific source."""
        return self.source_thresholds.get(source, self.threshold)
    
    def filter_chunks(
        self,
        chunks: List[ContextChunk],
        results: List[DecayResult]
    ) -> Tuple[List[ContextChunk], List[DecayResult], List[Tuple[ContextChunk, DecayResult]]]:
        """Filter chunks based on decay scores."""
        fresh_chunks = []
        fresh_results = []
        blocked_chunks = []
        
        result_map = {r.chunk_id: r for r in results}
        
        for chunk in chunks:
            result = result_map.get(chunk.id)
            if result is None:
                # No evaluation result, keep the chunk (fail open)
                fresh_chunks.append(chunk)
                continue
            
            threshold = self.get_threshold_for_source(chunk.source)
            
            if result.decay_score < threshold:
                fresh_chunks.append(chunk)
                fresh_results.append(result)
            else:
                blocked_chunks.append((chunk, result))
                logger.info(f"Blocked chunk: {chunk.id} (decay={result.decay_score:.2f})")
        
        return fresh_chunks, fresh_results, blocked_chunks
    
    def reconstruct_messages(
        self,
        messages: List[Dict[str, Any]],
        fresh_chunks: List[ContextChunk],
        original_chunks: List[ContextChunk]
    ) -> List[Dict[str, Any]]:
        """
        Reconstruct messages with only fresh context.
        This is a simplified version — real implementation depends on how
        context is embedded in messages.
        """
        # Create a mapping of original content to fresh content
        fresh_map = {c.id: c.content for c in fresh_chunks}
        
        # Deep copy messages
        new_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if "<context>" in content:
                # This is a simplified replacement logic
                # Real implementation would need to parse the context tags
                import re
                context_pattern = r"<context>(.*?)</context>"
                
                def replace_context(match):
                    chunk_id = match.group(1).strip()
                    return f"<context>{fresh_map.get(chunk_id, '')}</context>"
                
                new_content = re.sub(context_pattern, replace_context, content, flags=re.DOTALL)
                new_messages.append({**msg, "content": new_content})
            else:
                new_messages.append(msg)
        
        return new_messages
    
    def calculate_stats(
        self,
        original_chunks: List[ContextChunk],
        fresh_chunks: List[ContextChunk],
        blocked_chunks: List[Tuple[ContextChunk, DecayResult]],
        original_tokens: int,
        clean_tokens: int
    ) -> Dict[str, Any]:
        """Calculate statistics for telemetry."""
        total = len(original_chunks)
        fresh = len(fresh_chunks)
        blocked = len(blocked_chunks)
        
        avg_decay = 0.0
        conflicts = 0
        
        for chunk, result in blocked_chunks:
            avg_decay += result.decay_score
            if result.conflict_detected:
                conflicts += 1
        
        if blocked > 0:
            avg_decay /= blocked
        
        return {
            "total_chunks": total,
            "fresh_chunks": fresh,
            "blocked_chunks": blocked,
            "blocked_percentage": (blocked / total * 100) if total > 0 else 0,
            "avg_decay": avg_decay,
            "conflicts_detected": conflicts,
            "tokens_saved": original_tokens - clean_tokens,
            "savings_percentage": ((original_tokens - clean_tokens) / original_tokens * 100) if original_tokens > 0 else 0
        }