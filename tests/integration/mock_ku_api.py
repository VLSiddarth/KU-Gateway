from fastapi import FastAPI
from pydantic import BaseModel
import random

app = FastAPI()

class DiscoverRequest(BaseModel):
    topic: str
    formats: list = []
    max_results: int = 1

@app.post("/v1/discover")
async def discover(req: DiscoverRequest):
    return {
        "results": [
            {
                "decay_score": round(random.uniform(0.1, 0.9), 2),
                "knowledge_velocity": "moderate",
                "conflict_detected": False,
                "publication_date": "2024-01-01",
                "source_platform": req.formats[0] if req.formats else "web"
            }
        ],
        "coverage_intelligence": {"confidence": 0.85}
    }