from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite

# Conventional Saaty random-index values (n=1..15), widely reproduced from
# T. L. Saaty, The Analytic Hierarchy Process, McGraw-Hill, 1980.
RANDOM_INDEX: dict[int, float] = {
    1: 0.0,
    2: 0.0,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
    11: 1.51,
    12: 1.48,
    13: 1.56,
    14: 1.57,
    15: 1.59,
}


@dataclass(frozen=True)
class ConsistencyResult:
    lambda_max: float
    consistency_index: float
    consistency_ratio: float


def calculate_consistency(
    matrix: Sequence[Sequence[float]], max_iterations: int = 10_000, tolerance: float = 1e-12
) -> ConsistencyResult:
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        raise ValueError("Consistency requires a non-empty square matrix.")
    if n not in RANDOM_INDEX:
        raise ValueError("Consistency ratio supports matrix sizes 1 through 15.")
    vector = [1.0 / n] * n
    for _ in range(max_iterations):
        product = [sum(float(matrix[i][j]) * vector[j] for j in range(n)) for i in range(n)]
        total = sum(product)
        if not isfinite(total) or total <= 0:
            raise ValueError("Matrix produced an invalid principal eigenvector.")
        updated = [item / total for item in product]
        if max(abs(updated[i] - vector[i]) for i in range(n)) <= tolerance:
            vector = updated
            break
        vector = updated
    weighted = [sum(float(matrix[i][j]) * vector[j] for j in range(n)) for i in range(n)]
    lambda_max = sum(weighted[i] / vector[i] for i in range(n)) / n
    ci = 0.0 if n < 2 else max(0.0, (lambda_max - n) / (n - 1))
    ri = RANDOM_INDEX[n]
    cr = 0.0 if ri == 0 else ci / ri
    return ConsistencyResult(lambda_max, ci, cr)
