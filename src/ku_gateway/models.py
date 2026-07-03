"""Pydantic models for KU-Gateway."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ContextChunk(BaseModel):
    """A context chunk extracted from the LLM request."""
    id: str = Field(..., description="Unique identifier for the chunk")
    content: str = Field(..., description="The actual content")
    source: Optional[str] = Field(None, description="Source type (arxiv, github, etc.)")
    url: Optional[str] = Field(None, description="Source URL")
    title: Optional[str] = Field(None, description="Source title")

class DecayResult(BaseModel):
    """Decay evaluation result from KU API."""
    chunk_id: str = Field(..., description="Reference to the chunk")
    decay_score: float = Field(..., ge=0.0, le=1.0, description="0=fresh, 1=decayed")
    knowledge_velocity: str = Field(..., description="frozen/slow/moderate/fast/hypersonic")
    conflict_detected: bool = Field(False, description="Whether conflict was detected")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Coverage confidence")
    suggested_queries: List[str] = Field(default_factory=list)
    publication_date: Optional[datetime] = Field(None)
    source_type: Optional[str] = Field(None)

class GatewayRequest(BaseModel):
    """Incoming request to KU-Gateway."""
    messages: List[Dict[str, Any]]
    model: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    # ... other OpenAI-compatible fields

class GatewayResponse(BaseModel):
    """Processed request with telemetry."""
    original_tokens: int
    clean_tokens: int
    tokens_saved: int
    cost_saved: float
    chunks_evaluated: int
    chunks_blocked: int
    conflicts_detected: int
    avg_decay: float
    freshness_label: str  # fresh/aging/stale/decayed
    request_id: str
    timestamp: datetime
    
class TelemetryReport(BaseModel):
    """Session telemetry."""
    request_id: str
    total_requests: int
    total_tokens: int
    total_tokens_saved: int
    total_cost_saved: float
    total_conflicts: int
    avg_latency_ms: float
    uptime_seconds: float