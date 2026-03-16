from __future__ import annotations

from typing import Any


def to_float(value: Any, default: float = 0.0) -> float:
    if value in (None, "", "-"):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def default_index_groups() -> dict[str, list]:
    return {"us": [], "jp": [], "kr": [], "hk": [], "cn": []}


def build_sparkline(values: list[Any], limit: int = 7) -> list[float]:
    points: list[float] = []
    for value in values:
        number = to_float(value, default=float("nan"))
        if number == number:
            points.append(round(number, 4))

    if not points:
        return []
    return points[-limit:]
