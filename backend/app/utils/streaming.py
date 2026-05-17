"""
SSE streaming utilities — format Server-Sent Events for FastAPI responses.
"""

import json
from typing import AsyncGenerator


def sse_event(event_type: str, data: dict | str) -> str:
    """Format a single SSE event."""
    if isinstance(data, dict):
        payload = json.dumps(data)
    else:
        payload = data
    return f"event: {event_type}\ndata: {payload}\n\n"


async def token_stream(agent: str, token: str) -> str:
    return sse_event("token", {"agent": agent, "token": token})


async def status_stream(step: str, status: str, extra: dict = {}) -> str:
    return sse_event("agent_status", {"step": step, "status": status, **extra})


async def verdict_stream(verdict_dict: dict) -> str:
    return sse_event("verdict", verdict_dict)


async def error_stream(message: str) -> str:
    return sse_event("error", {"message": message})


async def done_stream() -> str:
    return sse_event("done", {})
