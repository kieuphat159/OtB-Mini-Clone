from typing import Any, Optional


def normalize_article_id(article_id: Any) -> Optional[str]:
    """Normalize article IDs so comparisons are stable across int/string values."""
    if article_id is None:
        return None
    if isinstance(article_id, (int, float)):
        return str(int(article_id))
    return str(article_id).strip()
