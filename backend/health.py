from typing import Dict, Any, List


# ──────────────────────────────────────────────
# Final Health Score
# ──────────────────────────────────────────────

def compute_health_score(metrics: Dict[str, Any]) -> float:
    """
    health =
      0.25 * complexity_score +
      0.20 * churn_score +
      0.20 * hotspot_score +
      0.15 * bus_factor_score +
      0.20 * stability_score

    Clamped between 0 and 100.
    """
    health = (
        0.25 * metrics["complexity_score"] +
        0.20 * metrics["churn_score"] +
        0.20 * metrics["hotspot_score"] +
        0.15 * metrics["bus_factor_score"] +
        0.20 * metrics["stability_score"]
    )
    return round(max(0.0, min(100.0, health)), 2)


# ──────────────────────────────────────────────
# Alert Generation
# ──────────────────────────────────────────────

def generate_alerts(
    current: Dict[str, Any],
    previous: Dict[str, Any] | None,
    current_health: float,
    previous_health: float | None,
) -> List[str]:
    """
    Generate alert strings based on alert rules:
    - health drops >15 points between commits
    - churn spikes >200%
    - bus factor falls below 40
    - hotspot score falls below 30
    """
    alerts = []

    # Health drop alert
    if previous_health is not None:
        drop = previous_health - current_health
        if drop > 15:
            alerts.append(
                f"⚠️ Health dropped {drop:.1f} points (from {previous_health:.1f} → {current_health:.1f})"
            )

    # Churn spike alert
    if previous is not None:
        prev_churn = previous.get("churn", 0)
        curr_churn = current.get("churn", 0)
        if prev_churn > 0:
            spike_pct = ((curr_churn - prev_churn) / prev_churn) * 100
            if spike_pct > 200:
                alerts.append(
                    f"⚠️ Churn spiked {spike_pct:.0f}% (from {prev_churn} → {curr_churn} lines)"
                )

    # Bus factor alert
    if current.get("bus_factor_score", 100) < 40:
        alerts.append(
            f"⚠️ Bus factor critical: top contributor owns {current.get('ownership_pct', 0):.0f}% of commits"
        )

    # Hotspot alert
    if current.get("hotspot_score", 100) < 30:
        alerts.append(
            f"⚠️ Hotspot score critically low ({current.get('hotspot_score', 0):.1f}): high complexity + high churn"
        )

    return alerts


# ──────────────────────────────────────────────
# Build commit result record
# ──────────────────────────────────────────────

def build_commit_record(
    commit_sha: str,
    commit_date: str,
    commit_message: str,
    author: str,
    metrics: Dict[str, Any],
    alerts: List[str],
) -> Dict[str, Any]:
    health = compute_health_score(metrics)
    return {
        "commit": commit_sha[:8],
        "full_sha": commit_sha,
        "date": commit_date,
        "message": commit_message[:120],
        "author": author,
        "health": health,
        "complexity_score": metrics["complexity_score"],
        "churn_score": metrics["churn_score"],
        "hotspot_score": metrics["hotspot_score"],
        "bus_factor_score": metrics["bus_factor_score"],
        "stability_score": metrics["stability_score"],
        "avg_complexity": metrics["avg_complexity"],
        "churn": metrics["churn"],
        "additions": metrics["additions"],
        "deletions": metrics["deletions"],
        "files_changed": metrics["files_changed"],
        "py_file_count": metrics["py_file_count"],
        "ownership_pct": metrics["ownership_pct"],
        "hotspots": metrics["hotspots"],
        "alerts": alerts,
    }