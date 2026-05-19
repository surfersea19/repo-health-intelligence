import math
import os
from typing import List, Dict, Any, Optional

try:
    from radon.complexity import cc_visit, average_complexity
    from radon.metrics import mi_visit
    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False


# ──────────────────────────────────────────────
# 1. Complexity Score
# ──────────────────────────────────────────────

def compute_complexity(py_files: List[str]) -> tuple[float, List[str]]:
    """
    Compute average cyclomatic complexity across all Python files.
    Returns (avg_complexity, list_of_hotspot_files).
    Uses Radon if available; falls back to line-count heuristic.
    """
    if not py_files:
        return 0.0, []

    if not RADON_AVAILABLE:
        return _fallback_complexity(py_files)

    all_complexities: List[float] = []
    file_complexities: Dict[str, float] = {}

    for filepath in py_files:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                source = f.read()
            if not source.strip():
                continue
            blocks = cc_visit(source)
            if blocks:
                avg = sum(b.complexity for b in blocks) / len(blocks)
                file_complexities[filepath] = avg
                all_complexities.extend(b.complexity for b in blocks)
        except SyntaxError:
            pass
        except Exception:
            pass

    if not all_complexities:
        return 0.0, []

    avg_cc = sum(all_complexities) / len(all_complexities)

    # Hotspots: files with complexity above average * 1.5
    threshold = avg_cc * 1.5
    hotspots = [
        os.path.basename(fp)
        for fp, c in file_complexities.items()
        if c >= threshold
    ]

    return avg_cc, hotspots


def _fallback_complexity(py_files: List[str]) -> tuple[float, List[str]]:
    """Heuristic complexity when Radon is unavailable: avg lines per function."""
    total_lines = 0
    total_files = 0
    for fp in py_files:
        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            total_lines += len(lines)
            total_files += 1
        except Exception:
            pass
    if total_files == 0:
        return 0.0, []
    avg_lines = total_lines / total_files
    # Rough heuristic: 1 unit per 10 lines
    return avg_lines / 10.0, []


def complexity_score(avg_complexity: float) -> float:
    """complexity_score = max(0, 100 - (avg_complexity * 5))"""
    return max(0.0, 100.0 - (avg_complexity * 5.0))


# ──────────────────────────────────────────────
# 2. Churn Score
# ──────────────────────────────────────────────

def compute_churn(additions: int, deletions: int) -> int:
    return additions + deletions


def churn_score(churn: int) -> float:
    """churn_score = max(0, 100 - (churn / 50))"""
    return max(0.0, 100.0 - (churn / 50.0))


# ──────────────────────────────────────────────
# 3. Hotspot Score
# ──────────────────────────────────────────────

def hotspot_score(avg_complexity: float, churn: int) -> float:
    """
    hotspot = complexity * churn
    hotspot_score = max(0, 100 - log(hotspot + 1) * 10)
    """
    hotspot = avg_complexity * churn
    return max(0.0, 100.0 - math.log(hotspot + 1) * 10.0)


# ──────────────────────────────────────────────
# 4. Bus Factor Score
# ──────────────────────────────────────────────

def compute_bus_factor(author_counts: Dict[str, int]) -> tuple[float, float]:
    """
    Returns (bus_factor_score, top_contributor_ownership_pct).
    ownership = top contributor commits / total commits.
    """
    if not author_counts:
        return 90.0, 0.0

    total = sum(author_counts.values())
    if total == 0:
        return 90.0, 0.0

    top_count = max(author_counts.values())
    ownership_pct = (top_count / total) * 100.0

    if ownership_pct > 80:
        score = 30.0
    elif ownership_pct > 60:
        score = 60.0
    else:
        score = 90.0

    return score, ownership_pct


# ──────────────────────────────────────────────
# 5. Stability Score
# ──────────────────────────────────────────────

def compute_stability(files_changed: int, py_file_count: int) -> float:
    """
    file_change_frequency = files_changed / max(py_file_count, 1)
    stability_score = max(0, 100 - (file_change_frequency * 10))
    """
    if py_file_count == 0:
        return 100.0
    frequency = files_changed / py_file_count
    return max(0.0, 100.0 - (frequency * 10.0))


# ──────────────────────────────────────────────
# All metrics bundled
# ──────────────────────────────────────────────

def compute_all_metrics(
    py_files: List[str],
    additions: int,
    deletions: int,
    files_changed: int,
    author_counts: Dict[str, int],
) -> Dict[str, Any]:
    """Compute all metrics and return a structured dict."""
    avg_cc, hotspots = compute_complexity(py_files)

    churn = compute_churn(additions, deletions)
    c_score = complexity_score(avg_cc)
    ch_score = churn_score(churn)
    hs_score = hotspot_score(avg_cc, churn)
    bf_score, ownership_pct = compute_bus_factor(author_counts)
    stab_score = compute_stability(files_changed, len(py_files))

    return {
        "avg_complexity": round(avg_cc, 3),
        "churn": churn,
        "additions": additions,
        "deletions": deletions,
        "files_changed": files_changed,
        "py_file_count": len(py_files),
        "ownership_pct": round(ownership_pct, 1),
        "hotspots": hotspots[:5],  # top 5 hotspot files
        "complexity_score": round(c_score, 2),
        "churn_score": round(ch_score, 2),
        "hotspot_score": round(hs_score, 2),
        "bus_factor_score": round(bf_score, 2),
        "stability_score": round(stab_score, 2),
    }