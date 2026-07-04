"""Context evaluation with KU API (real + mock compatible)."""

import httpx
from typing import List, Dict, Any, Optional
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
        self.difficulty = settings.ku_difficulty
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
            },
        )

    async def evaluate_chunk(self, chunk: ContextChunk) -> DecayResult:
        """Evaluate a single context chunk."""
        # Check cache first
        if cache:
            cached = await cache.get(chunk.id)
            if cached:
                return DecayResult(**cached)

        try:
            # Build payload for real API (also works with mock)
            topic = chunk.title or chunk.content[:200]
            payload: Dict[str, Any] = {
                "topic": topic,
                "difficulty": self.difficulty,
            }
            # Pass source as format hint if available
            if chunk.source:
                payload["formats"] = [chunk.source]

            response = await self.client.post(
                f"{self.api_url}/v1/discover", json=payload
            )
            response.raise_for_status()
            data = response.json()

            # --- Parse response (handles both real and mock formats) ---

            # 1. decay score and velocity
            decay_score = 0.5
            knowledge_velocity = "unknown"
            confidence = 0.0

            # Real API: max_decay_detected + knowledge_velocity.velocity_label
            if "max_decay_detected" in data:
                decay_score = data["max_decay_detected"]
                knowledge_velocity = data.get("knowledge_velocity", {}).get(
                    "velocity_label", "unknown"
                )
                confidence = data.get("coverage_intelligence", {}).get("confidence", 0.0)
            # Mock API: first result contains decay_score, knowledge_velocity, confidence
            elif "results" in data:
                results = data["results"]
                if results:
                    first = results[0]
                    decay_score = first.get("decay_score", 0.5)
                    knowledge_velocity = first.get("knowledge_velocity", "unknown")
                    confidence = data.get("coverage_intelligence", {}).get("confidence", 0.0)

            # 2. conflict detection
            conflict_detected = False
            # Real API
            if "conflict_detection" in data:
                conflict_detected = data["conflict_detection"]["conflicts_found"] > 0
            # Mock API (each result may have conflict_detected)
            elif "results" in data and data["results"]:
                conflict_detected = data["results"][0].get("conflict_detected", False)

            # 3. suggested queries (optional)
            suggested_queries = []
            if "coverage_intelligence" in data:
                suggested_queries = data["coverage_intelligence"].get(
                    "suggested_queries", []
                )

            result = DecayResult(
                chunk_id=chunk.id,
                decay_score=decay_score,
                knowledge_velocity=knowledge_velocity,
                conflict_detected=conflict_detected,
                confidence=confidence,
                suggested_queries=suggested_queries,
            )

            # Cache result
            if cache:
                await cache.set(chunk.id, result.model_dump(), ttl=settings.redis_ttl)

            return result

        except httpx.HTTPError as e:
            logger.error(f"KU API error: {e}")
            # Return neutral result on failure
            return DecayResult(
                chunk_id=chunk.id,
                decay_score=0.5,
                knowledge_velocity="unknown",
                conflict_detected=False,
                confidence=0.0,
            )

    async def evaluate_chunks(self, chunks: List[ContextChunk]) -> List[DecayResult]:
        """Evaluate multiple chunks in parallel."""
        tasks = [self.evaluate_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            r for r in results
            if isinstance(r, DecayResult) and not isinstance(r, Exception)
        ]

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()