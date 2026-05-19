import re
from typing import Optional


def validate_github_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate that a URL looks like a GitHub repository URL.
    Returns (is_valid, error_message).
    """
    url = url.strip()
    if not url:
        return False, "URL cannot be empty."

    # Accept https://github.com/owner/repo or git@github.com:owner/repo
    patterns = [
        r'^https://github\.com/[\w\-\.]+/[\w\-\.]+(?:\.git)?/?$',
        r'^git@github\.com:[\w\-\.]+/[\w\-\.]+(?:\.git)?$',
        r'^https://gitlab\.com/[\w\-\.]+/[\w\-\.]+(?:\.git)?/?$',
        r'^https://bitbucket\.org/[\w\-\.]+/[\w\-\.]+(?:\.git)?/?$',
    ]

    for pattern in patterns:
        if re.match(pattern, url):
            return True, None

    return False, (
        "Invalid repository URL. "
        "Expected format: https://github.com/owner/repo"
    )


def normalize_url(url: str) -> str:
    """Strip trailing slashes and .git suffix for display."""
    url = url.strip().rstrip('/')
    if url.endswith('.git'):
        url = url[:-4]
    return url


def format_date(dt) -> str:
    """Format a datetime object to ISO string."""
    try:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(dt)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division avoiding ZeroDivisionError."""
    if denominator == 0:
        return default
    return numerator / denominator