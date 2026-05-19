import os
import shutil
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime

import git
from git import Repo, InvalidGitRepositoryError, GitCommandError


def clone_repo(url: str) -> tuple[Optional[Repo], Optional[str], Optional[str]]:
    """
    Clone a GitHub repo to a temp directory.
    Returns (repo, temp_dir, error_message).
    """
    temp_dir = tempfile.mkdtemp(prefix="repo_health_")
    try:
        repo = Repo.clone_from(url, temp_dir, depth=500, no_single_branch=True)
        return repo, temp_dir, None
    except GitCommandError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        msg = str(e)
        if "not found" in msg.lower() or "repository not found" in msg.lower():
            return None, None, "Repository not found or is private."
        if "could not read" in msg.lower():
            return None, None, "Could not read repository. It may be private or the URL is invalid."
        return None, None, f"Git error: {msg[:200]}"
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, None, f"Unexpected error during clone: {str(e)[:200]}"


def get_commits(repo: Repo) -> List[Any]:
    """Return list of commits from default branch, oldest first."""
    try:
        commits = list(repo.iter_commits(repo.head.commit, reverse=True))
        return commits
    except Exception as e:
        return []


def sample_commits(commits: List[Any]) -> List[Any]:
    """
    Smart scalable sampling.

    Small repos:
        analyze all commits

    Medium repos:
        every 2nd commit

    Large repos:
        every 4th commit

    Very large repos:
        every 8th commit
    """

    total = len(commits)

    if total <= 100:
        sampled = commits

    elif total <= 300:
        sampled = commits[::2]

    elif total <= 1000:
        sampled = commits[::4]

    else:
        sampled = commits[::8]

    # Keep latest commit
    if commits[-1] not in sampled:
        sampled.append(commits[-1])

    # Prevent huge analysis loads
    MAX_ANALYZED = 150

    if len(sampled) > MAX_ANALYZED:
        step = max(1, len(sampled) // MAX_ANALYZED)
        sampled = sampled[::step]

    return sampled


def checkout_commit(repo: Repo, commit: Any) -> bool:
    """Checkout a specific commit. Returns True on success."""
    try:
        repo.git.checkout(commit.hexsha, force=True)
        return True
    except GitCommandError as e:
        return False


def get_python_files(repo_dir: str) -> List[str]:
    """Return all .py files in the repo directory."""
    py_files = []
    for root, dirs, files in os.walk(repo_dir):
        # Skip hidden dirs and common non-source dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'node_modules', '.git', 'venv', 'env', '.venv')]
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.join(root, f))
    return py_files


def get_commit_diff_stats(repo: Repo, commit: Any) -> Dict[str, int]:
    """
    Return {additions, deletions, files_changed} for a commit.
    For the first commit, compare against empty tree.
    """
    try:
        if commit.parents:
            parent = commit.parents[0]
            diff = parent.diff(commit)
            additions = 0
            deletions = 0
            files_changed = 0
            for d in diff:
                files_changed += 1
                try:
                    stats = d.diff.decode('utf-8', errors='ignore') if d.diff else ""
                    for line in stats.splitlines():
                        if line.startswith('+') and not line.startswith('+++'):
                            additions += 1
                        elif line.startswith('-') and not line.startswith('---'):
                            deletions += 1
                except Exception:
                    pass
            return {"additions": additions, "deletions": deletions, "files_changed": files_changed}
        else:
            # First commit - count all lines as additions
            total_lines = 0
            total_files = 0
            for item in commit.tree.traverse():
                if hasattr(item, 'data_stream'):
                    total_files += 1
                    try:
                        content = item.data_stream.read().decode('utf-8', errors='ignore')
                        total_lines += len(content.splitlines())
                    except Exception:
                        pass
            return {"additions": total_lines, "deletions": 0, "files_changed": total_files}
    except Exception:
        return {"additions": 0, "deletions": 0, "files_changed": 0}


def get_contributor_stats(repo: Repo, commit: Any) -> Dict[str, int]:
    """
    Return author commit counts up to and including this commit.
    """
    try:
        author_counts: Dict[str, int] = {}
        for c in repo.iter_commits(commit):
            author = c.author.email or c.author.name or "unknown"
            author_counts[author] = author_counts.get(author, 0) + 1
        return author_counts
    except Exception:
        return {}


def get_changed_files(repo: Repo, commit: Any) -> List[str]:
    """Return list of file paths changed in this commit."""
    try:
        if commit.parents:
            diff = commit.parents[0].diff(commit)
            return [d.a_path or d.b_path for d in diff]
        return []
    except Exception:
        return []


def cleanup_repo(temp_dir: str):
    """Remove cloned repo directory."""
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)