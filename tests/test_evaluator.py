import pytest
from unittest.mock import AsyncMock, patch
from ku_gateway.evaluator import Evaluator
from ku_gateway.models import ContextChunk, DecayResult

@pytest.mark.asyncio
async def test_evaluate_chunk_mocked():
    evaluator = Evaluator()
    evaluator.client = AsyncMock()
    evaluator.client.post.return_value.json.return_value = {
        "results": [{"decay_score": 0.2, "knowledge_velocity": "slow", "conflict_detected": False, "publication_date": "2025-01-01", "source_platform": "arxiv"}],
        "coverage_intelligence": {"confidence": 0.9}
    }
    chunk = ContextChunk(id="c1", content="test", source="arxiv")
    result = await evaluator.evaluate_chunk(chunk)
    assert result.decay_score == 0.2