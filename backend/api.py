import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.git_analyzer import (
    clone_repo, get_commits, sample_commits,
    checkout_commit, get_python_files, get_commit_diff_stats,
    get_contributor_stats, get_changed_files, cleanup_repo,
)
from backend.metrics import compute_all_metrics
from backend.health import compute_health_score, generate_alerts, build_commit_record
from backend.utils import validate_github_url, normalize_url, format_date

# ── AI imports (optional) ──────────────────────────────────────
try:
    from ai.gemini_client import get_commit_summary, get_repo_summary
    AI_AVAILABLE = True
except Exception:
    AI_AVAILABLE = False

    async def get_commit_summary(*args, **kwargs):
        return None

    async def get_repo_summary(*args, **kwargs):
        return None


router = APIRouter()


class AnalyzeRequest(BaseModel):
    url: str


# ─────────────────────────────────────────────────────────────────
# POST /analyze
# ─────────────────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze_repo(request: AnalyzeRequest):
    url = request.url.strip()

    # Validate URL
    valid, error = validate_github_url(url)
    if not valid:
        return JSONResponse(
            status_code=400,
            content={"error": error, "commits": [], "summary": None}
        )

    # Clone repository
    repo, temp_dir, clone_error = clone_repo(url)
    if clone_error:
        return JSONResponse(
            status_code=422,
            content={"error": clone_error, "commits": [], "summary": None}
        )

    results: List[Dict[str, Any]] = []

    try:
        # Get and sample commits
        commits = get_commits(repo)
        if not commits:
            return JSONResponse(
                status_code=422,
                content={
                    "error": "No commits found in repository.",
                    "commits": [],
                    "summary": None,
                }
            )

        sampled = sample_commits(commits)
        total_commits = len(commits)
        analyzed_count = len(sampled)

        prev_metrics = None
        prev_health = None

        for commit in sampled:
            # Checkout this commit
            ok = checkout_commit(repo, commit)
            if not ok:
                continue

            # Get Python files at this commit
            py_files = get_python_files(temp_dir)

            # Diff stats
            diff_stats = get_commit_diff_stats(repo, commit)

            # Contributor stats (cumulative up to this commit)
            author_counts = get_contributor_stats(repo, commit)

            # Changed files
            changed_files = get_changed_files(repo, commit)
            files_changed = len(changed_files)

            # Compute all metrics
            metrics = compute_all_metrics(
                py_files=py_files,
                additions=diff_stats["additions"],
                deletions=diff_stats["deletions"],
                files_changed=files_changed,
                author_counts=author_counts,
            )

            current_health = compute_health_score(metrics)

            # Alerts
            alerts = generate_alerts(metrics, prev_metrics, current_health, prev_health)

            # Author name
            author = commit.author.name or commit.author.email or "Unknown"

            # Date
            try:
                date_str = format_date(
                    datetime.fromtimestamp(commit.committed_date, tz=timezone.utc)
                )
            except Exception:
                date_str = str(commit.committed_date)

            record = build_commit_record(
                commit_sha=commit.hexsha,
                commit_date=date_str,
                commit_message=commit.message.strip(),
                author=author,
                metrics=metrics,
                alerts=alerts,
            )

            # AI commit summary (non-blocking, best-effort)
            if AI_AVAILABLE and prev_metrics is not None:
                try:
                    complexity_delta = metrics["avg_complexity"] - prev_metrics["avg_complexity"]
                    churn_delta = metrics["churn"] - prev_metrics.get("churn", 0)
                    summary = await get_commit_summary(
                        complexity_delta=complexity_delta,
                        churn_delta=churn_delta,
                        hotspots=metrics["hotspots"],
                    )
                    record["ai_summary"] = summary
                except Exception:
                    record["ai_summary"] = None
            else:
                record["ai_summary"] = None

            results.append(record)
            prev_metrics = metrics
            prev_health = current_health

        if not results:
            return JSONResponse(
                status_code=422,
                content={
                    "error": "Could not analyze any commits. Repository may have no Python files or checkout failed.",
                    "commits": [],
                    "summary": None,
                }
            )

        # Final AI repo summary
        repo_summary = None
        if AI_AVAILABLE and results:
            try:
                repo_summary = await get_repo_summary(results)
            except Exception:
                repo_summary = None

        if not repo_summary:
            repo_summary = _build_fallback_summary(results, total_commits, analyzed_count)

        return {
            "url": normalize_url(url),
            "total_commits": total_commits,
            "analyzed_commits": analyzed_count,
            "commits": results,
            "summary": repo_summary,
            "ai_available": AI_AVAILABLE,
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Analysis failed: {str(e)[:300]}",
                "commits": [],
                "summary": None,
            }
        )
    finally:
        cleanup_repo(temp_dir)


# ─────────────────────────────────────────────────────────────────
# GET /health  (ping endpoint)
# ─────────────────────────────────────────────────────────────────

@router.get("/health")
async def ping():
    return {"status": "ok", "ai_available": AI_AVAILABLE}


# ─────────────────────────────────────────────────────────────────
# Fallback summary (no AI)
# ─────────────────────────────────────────────────────────────────

def _build_fallback_summary(
    results: List[Dict[str, Any]],
    total_commits: int,
    analyzed_count: int,
) -> str:
    if not results:
        return "No data to summarize."

    first_health = results[0]["health"]
    last_health = results[-1]["health"]
    avg_health = sum(r["health"] for r in results) / len(results)

    trend = "stable"
    delta = last_health - first_health
    if delta < -10:
        trend = "declining"
    elif delta > 10:
        trend = "improving"

    all_alerts = [a for r in results for a in r.get("alerts", [])]
    alert_summary = f" {len(all_alerts)} alerts were generated." if all_alerts else ""

    hotspot_files = list({h for r in results for h in r.get("hotspots", [])})
    hotspot_str = ""
    if hotspot_files:
        hotspot_str = f" Key hotspot files: {', '.join(hotspot_files[:3])}."

    return (
        f"Analyzed {analyzed_count} of {total_commits} total commits. "
        f"Health trend is {trend} (started at {first_health:.0f}, "
        f"ended at {last_health:.0f}, avg {avg_health:.0f}/100)."
        f"{alert_summary}{hotspot_str}"
    )