"""
Prompt builders for Gemini API.
Only metric data is sent — never raw source code.
"""

import json
from typing import List, Dict, Any


def build_commit_prompt(
    complexity_delta: float,
    churn_delta: int,
    hotspots: List[str],
) -> str:
    """Build a prompt for explaining a single commit's metric changes."""
    delta_str = f"+{complexity_delta:.2f}" if complexity_delta >= 0 else f"{complexity_delta:.2f}"
    churn_str = f"+{churn_delta}" if churn_delta >= 0 else str(churn_delta)

    data = {
        "complexity_delta": delta_str,
        "churn_delta": churn_str,
        "hotspots": hotspots,
    }

    return (
        "You are a code health analyst. Based ONLY on these computed metrics "
        "(no source code is provided), write one concise sentence explaining "
        "what likely happened in this commit and its impact on maintainability.\n\n"
        f"Metrics:\n{json.dumps(data, indent=2)}\n\n"
        "Reply with exactly one sentence. Be specific about the metrics."
    )


def build_repo_prompt(results: List[Dict[str, Any]]) -> str:
    """Build a prompt for summarizing overall repo health trend."""
    if not results:
        return ""

    # Send only aggregated stats — no code
    first = results[0]
    last = results[-1]
    avg_health = sum(r["health"] for r in results) / len(results)

    # Find worst and best commits
    worst = min(results, key=lambda r: r["health"])
    best = max(results, key=lambda r: r["health"])

    # Count alerts
    total_alerts = sum(len(r.get("alerts", [])) for r in results)

    # Collect all hotspots
    all_hotspots = list({h for r in results for h in r.get("hotspots", [])})

    summary_data = {
        "total_commits_analyzed": len(results),
        "first_health_score": first["health"],
        "last_health_score": last["health"],
        "average_health_score": round(avg_health, 1),
        "best_health": {"score": best["health"], "commit": best["commit"]},
        "worst_health": {"score": worst["health"], "commit": worst["commit"]},
        "total_alerts": total_alerts,
        "frequent_hotspot_files": all_hotspots[:5],
        "avg_complexity": round(
            sum(r["avg_complexity"] for r in results) / len(results), 2
        ),
        "avg_churn": round(
            sum(r["churn"] for r in results) / len(results), 0
        ),
    }

    return (
        "You are a senior engineering lead reviewing repository health metrics. "
        "Based ONLY on these computed statistics (no source code), write a "
        "2-3 sentence summary of the repository's health trend, highlighting "
        "key risks and any positive patterns.\n\n"
        f"Repository Health Statistics:\n{json.dumps(summary_data, indent=2)}\n\n"
        "Be specific. Mention actual numbers. Focus on actionable insights."
    )