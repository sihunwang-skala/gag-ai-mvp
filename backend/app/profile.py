"""Humor Profile 계산. 응답 -> 유형별 비율 벡터."""
from __future__ import annotations

from collections import Counter

from .content import HUMOR_TYPES

SCHEMA_VERSION = 1


def build_profile(picks: list[str]) -> dict:
    """picks: 사용자가 가장 웃기다고 고른 유머 유형 목록 (시나리오당 1개)."""
    n = len(picks)
    counts = Counter(p for p in picks if p in HUMOR_TYPES)
    vector = {t: (counts[t] / n if n else 0.0) for t in HUMOR_TYPES}
    ranked = sorted(HUMOR_TYPES, key=lambda t: (-vector[t], t))
    top = [t for t in ranked if vector[t] > 0][:2]
    if n == 0:
        confidence = "none"
    elif n < 5:
        confidence = "low"
    else:
        confidence = "medium"
    return {
        "schema_version": SCHEMA_VERSION,
        "answered": n,
        "vector": {t: round(v, 3) for t, v in vector.items()},
        "top_types": top,
        "confidence": confidence,
        "note": "적은 응답에서 계산한 잠정 취향이에요. 코치·컴패니언을 쓰면서 바뀔 수 있어요.",
    }
