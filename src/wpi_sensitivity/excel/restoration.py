from __future__ import annotations

from collections.abc import Sequence
from math import isclose
from typing import Any


def values_match(expected: Any, actual: Any, tolerance: float = 1e-9) -> bool:
    if expected is None or actual is None:
        return expected is actual
    if isinstance(expected, bool) or isinstance(actual, bool):
        return bool(expected == actual)
    if isinstance(expected, int | float) and isinstance(actual, int | float):
        return isclose(float(expected), float(actual), rel_tol=tolerance, abs_tol=tolerance)
    return bool(expected == actual)


def outputs_match(expected: Sequence[Any], actual: Sequence[Any], tolerance: float = 1e-9) -> bool:
    return len(expected) == len(actual) and all(
        values_match(left, right, tolerance) for left, right in zip(expected, actual, strict=True)
    )
