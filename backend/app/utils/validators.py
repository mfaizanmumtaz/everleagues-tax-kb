"""Data validation helper functions."""

from typing import Optional
from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """Validate if a string is a valid URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_authority_level(level: Optional[int]) -> bool:
    """Validate authority level is between 1 and 6."""
    if level is None:
        return True
    return 1 <= level <= 6


def validate_governance_state(state: str) -> bool:
    """Validate governance state is a valid value."""
    valid_states = {"Draft", "Under Review", "Published", "Deprecated", "Archived"}
    return state in valid_states


def sanitize_solr_query(query: str) -> str:
    """Sanitize a query string for Solr to prevent injection."""
    # Escape special Solr characters
    special_chars = [
        "+",
        "-",
        "&&",
        "||",
        "!",
        "(",
        ")",
        "{",
        "}",
        "[",
        "]",
        "^",
        '"',
        "~",
        "*",
        "?",
        ":",
        "\\",
        "/",
    ]
    escaped = query
    for char in special_chars:
        escaped = escaped.replace(char, f"\\{char}")
    return escaped


def extract_domain_from_url(url: str) -> Optional[str]:
    """Extract domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove 'www.' prefix if present
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return None
