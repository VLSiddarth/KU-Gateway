"""Core proxy logic for KU-Gateway."""

import httpx
import os
import json
import asyncio
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional

from .config import Settings
from .models import ContextChunk, DecayResult, GatewayRequest, GatewayResponse
from .evaluator import Evaluator
from .stripper import Stripper
from .telemetry import Telemetry, logger
from .vault import Vault

router = APIRouter()
settings = Settings()
telemetry = Telemetry()
evaluator = Evaluator()
stripper = Stripper()
vault = Vault() if settings.vault_enabled else None

# Cached telemetry for dashboard
telemetry_buffer = []


def extract_context_chunks(messages: List[Dict[str, Any]]) -> List[ContextChunk]:
    """Extract context chunks from messages."""
    chunks = []
    import re
    context_pattern = r"<context>(.*?)</context>"

    for msg in messages:
        content = msg.get("content", "")
        matches = re.findall(context_pattern, content, re.DOTALL)

        for i, match in enumerate(matches):
            chunk = ContextChunk(
                id=f"chunk_{i+1}_{hash(match[:100])}",
                content=match.strip(),
                source=None,
                url=None,
                title=None
            )
            chunks.append(chunk)

    return chunks


def count_tokens(text: str) -> int:
    """Simple token counter (approximate)."""
    return len(text.split())


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Handle chat completions requests."""
    try:
        # Parse request
        body = await request.json()
        messages = body.get("messages", [])
        model = body.get("model", "gpt-4")
        stream = body.get("stream", False)

        logger.info(f"Received request: model={model}, stream={stream}")

        # Extract context chunks
        chunks = extract_context_chunks(messages)
        original_tokens = count_tokens(json.dumps(messages))

        if not chunks:
            # No context to evaluate, forward directly
            return await forward_to_llm(body, stream, dict(request.headers))

        # Evaluate chunks
        logger.info(f"Evaluating {len(chunks)} chunks")
        results = await evaluator.evaluate_chunks(chunks)

        # Filter chunks
        fresh_chunks, fresh_results, blocked_chunks = stripper.filter_chunks(
            chunks, results
        )

        # Reconstruct messages
        clean_messages = stripper.reconstruct_messages(
            messages, fresh_chunks, chunks
        )
        clean_tokens = count_tokens(json.dumps(clean_messages))

        # Calculate stats
        stats = stripper.calculate_stats(
            chunks, fresh_chunks, blocked_chunks,
            original_tokens, clean_tokens
        )
        stats['cost_saved'] = (stats['tokens_saved'] / 1000) * 0.002

        # Build telemetry
        telemetry_data = {
            "original_tokens": original_tokens,
            "clean_tokens": clean_tokens,
            "tokens_saved": stats["tokens_saved"],
            "savings_percentage": stats["savings_percentage"],
            "cost_saved": stats["cost_saved"],
            "total_chunks": stats["total_chunks"],
            "fresh_chunks": stats["fresh_chunks"],
            "blocked_chunks": stats["blocked_chunks"],
            "conflicts_detected": stats["conflicts_detected"],
            "avg_decay": stats["avg_decay"],
            "blocked_details": [
                (c.source or "unknown", c.title or "Untitled", r.decay_score)
                for c, r in blocked_chunks[:10]
            ],
            "latency_ms": 0
        }

        telemetry_buffer.append(telemetry_data)
        telemetry.update(telemetry_data)
        telemetry.print_request_summary(telemetry_data)

        # Reconstruct clean payload
        clean_body = body.copy()
        clean_body["messages"] = clean_messages

        # Forward to LLM with original client headers
        return await forward_to_llm(clean_body, stream, dict(request.headers))

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def forward_to_llm(
    body: Dict[str, Any],
    stream: bool,
    original_headers: Dict[str, str]
):
    """Forward request to LLM provider, preserving only safe headers."""
    # Determine target URL
    upstream_url = settings.upstream_llm_base_url
    if upstream_url:
        target_url = f"{upstream_url}/v1/chat/completions"
    else:
        target_url = "https://api.openai.com/v1/chat/completions"

    # List of headers that should NOT be forwarded (hop-by-hop)
    hop_by_hop = {
        "host", "content-length", "content-type",
        "transfer-encoding", "connection", "keep-alive",
        "proxy-authenticate", "proxy-authorization", "te", "trailer",
        "upgrade"
    }

    # Build clean headers for upstream
    forwarded_headers = {}
    for key, value in original_headers.items():
        if key.lower() not in hop_by_hop:
            forwarded_headers[key] = value

    # If no Authorization header from client, try OPENAI_API_KEY env
    if "authorization" not in (k.lower() for k in forwarded_headers):
        api_key = settings.openai_api_key
        if api_key:
            forwarded_headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if stream:
                async def stream_response():
                    async with client.stream(
                        "POST", target_url, json=body, headers=forwarded_headers
                    ) as response:
                        async for chunk in response.aiter_bytes():
                            yield chunk
                return StreamingResponse(
                    stream_response(), media_type="text/event-stream"
                )
            else:
                response = await client.post(
                    target_url, json=body, headers=forwarded_headers
                )
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
    except Exception as e:
        logger.error(f"Error forwarding to LLM: {e}")
        raise HTTPException(status_code=502, detail="LLM provider error")


@router.get("/v1/telemetry")
async def get_telemetry():
    """Get telemetry data for dashboard."""
    return {
        "requests": len(telemetry_buffer),
        "total_tokens_saved": telemetry.total_tokens_saved,
        "total_cost_saved": telemetry.total_cost_saved,
        "total_conflicts": telemetry.total_conflicts,
        "recent": telemetry_buffer[-20:]
    }


@router.on_event("shutdown")
async def shutdown():
    """Clean up resources."""
    await evaluator.close()
    telemetry.print_session_summary()