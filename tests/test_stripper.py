from ku_gateway.stripper import Stripper
from ku_gateway.models import ContextChunk, DecayResult

def test_filter_chunks():
    stripper = Stripper()
    chunks = [ContextChunk(id="1", content="a"), ContextChunk(id="2", content="b")]
    results = [
        DecayResult(chunk_id="1", decay_score=0.3, knowledge_velocity="slow", conflict_detected=False, confidence=0.8),
        DecayResult(chunk_id="2", decay_score=0.7, knowledge_velocity="fast", conflict_detected=True, confidence=0.6)
    ]
    fresh, fresh_res, blocked = stripper.filter_chunks(chunks, results)
    assert len(fresh) == 1  # chunk 1 kept
    assert len(blocked) == 1