from typing import List, Any


def recommend_from_series(series: List[float], k: int = 3) -> List[dict]:
    """Placeholder recommendation: returns top-k largest future suggestions."""
    if not series:
        return []
    vals = sorted(series, reverse=True)[:k]
    return [{"score": float(v)} for v in vals]
