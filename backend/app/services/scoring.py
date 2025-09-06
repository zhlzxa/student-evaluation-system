from __future__ import annotations

from typing import Optional


WEIGHTS = {
    "english": 0.10,
    "degree": 0.50,
    "academic": 0.15,
    "experience": 0.15,
    "ps_rl": 0.10,
}


def weighted_total(
    english: Optional[float],
    degree: Optional[float],
    academic: Optional[float],
    experience: Optional[float],
    ps_rl: Optional[float],
) -> float:
    total = 0.0
    for key, val in {
        "english": english,
        "degree": degree,
        "academic": academic,
        "experience": experience,
        "ps_rl": ps_rl,
    }.items():
        if val is None:
            continue
        total += WEIGHTS[key] * max(0.0, min(10.0, float(val)))
    return round(total, 4)


def is_close(a: float, b: float, eps: float = 0.3) -> bool:
    return abs(a - b) <= eps

