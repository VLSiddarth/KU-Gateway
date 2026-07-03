"""Context evaluation with KU API."""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from .config import Settings
from .models import ContextChunk, DecayResult
from .telemetry import logger
from .cache import Cache

settings = Settings()
cache = Cache() if settings.redis_enabled else None

class Evaluator:
    """Evaluates context chunks for freshness using KU API."""
    
    def __init__(self):
        self.api_url = settings.ku_api_url
        self.api_key = settings.ku_api_key
        self.timeout = settings.ku_api_timeout
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
        )
    
    async def evaluate_chunk(self, chunk: ContextChunk) -> DecayResult:
        """Evaluate a single context chunk."""
        # Check cache first
        if cache:
            cached = await cache.get(chunk.id)
            if cached:
                return DecayResult(**cached)
        
        try:
            # Call KU API
            response = await self.client.post(
                f"{self.api_url}/v1/discover",
                json={
                    "topic": chunk.title or chunk.content[:200],
                    "formats": [chunk.source] if chunk.source else [],
                    "max_results": 1
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("results"):
                # No results found
                return DecayResult(
                    chunk_id=chunk.id,
                    decay_score=0.5,
                    knowledge_velocity="unknown",
                    conflict_detected=False,
                    confidence=data.get("coverage_intelligence", {}).get("confidence", 0.0)
                )
            
            result = data["results"][0]
            decay_result = DecayResult(
                chunk_id=chunk.id,
                decay_score=result.get("decay_score", 0.5),
                knowledge_velocity=result.get("knowledge_velocity", "unknown"),
                conflict_detected=result.get("conflict_detected", False),
                confidence=data.get("coverage_intelligence", {}).get("confidence", 0.0),
                publication_date=result.get("publication_date"),
                source_type=result.get("source_platform")
            )
            
            # Cache result
            if cache:
                await cache.set(chunk.id, decay_result.dict(), ttl=settings.redis_ttl)
            
            return decay_result
            
        except httpx.HTTPError as e:
            logger.error(f"KU API error: {e}")
            # Return default with low confidence
            return DecayResult(
                chunk_id=chunk.id,
                decay_score=0.5,
                knowledge_velocity="unknown",
                conflict_detected=False,
                confidence=0.0
            )
    
    async def evaluate_chunks(self, chunks: List[ContextChunk]) -> List[DecayResult]:
        """Evaluate multiple chunks in parallel."""
        tasks = [self.evaluate_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors
        return [
            r for r in results 
            if isinstance(r, DecayResult) and not isinstance(r, Exception)
        ]
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()