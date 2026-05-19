"""
Gemini API client for AI-powered summaries.
Replace GEMINI_API_KEY with your actual key.
AI is only used for commit explanation and final repo summary.
Raw code is never sent to the API.
"""

import os
import json
import httpx
from typing import List, Dict, Any, Optional

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

TIMEOUT = 10.0  # seconds


async def _call_gemini(prompt: str) -> Optional[str]:
    """
    Send a prompt to Gemini and return the text response.
    Returns None on error.
    """
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        return None  # No key configured

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 256,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(GEMINI_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
    except Exception:
        pass

    return None


async def get_commit_summary(
    complexity_delta: float,
    churn_delta: int,
    hotspots: List[str],
) -> Optional[str]:
    """
    Ask Gemini to explain what happened in a commit based on metric deltas.
    No code is sent — only computed metric values.
    """
    from ai.prompts import build_commit_prompt
    prompt = build_commit_prompt(complexity_delta, churn_delta, hotspots)
    return await _call_gemini(prompt)


async def get_repo_summary(results: List[Dict[str, Any]]) -> Optional[str]:
    """
    Ask Gemini to summarize the overall repo health trend.
    Only aggregated metric data is sent — no code.
    """
    from ai.prompts import build_repo_prompt
    prompt = build_repo_prompt(results)
    return await _call_gemini(prompt)