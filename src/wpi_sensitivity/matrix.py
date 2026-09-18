from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction
from math import isclose, isfinite

from .excel.ranges import A1Range
from .models import Comparison

SAATY_SCALE: tuple[float, ...] = (
    1 / 9,
    1 / 8,
    1 / 7,
    1 / 6,
    1 / 5,
    1 / 4,
    1 / 3,
    1 / 2,
    1.0,
    2.0,
    3.0,
    4.0,
    5.0,
    6.0,
    7.0,
    8.0,
    9.0,
)


class MatrixValidationError(ValueError):
    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("\n".join(self.errors))


def parse_saaty_value(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid comparisons.")
    if isinstance(value, int | float):
        result = float(value)
    elif isinstance(value, str):
        text = value.strip()
        try:
            result = float(Fraction(text)) if "/" in text else float(text)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"Invalid comparison value: {value!r}") from exc
    else:
        raise ValueError(f"Invalid comparison value: {value!r}")
    if not isfinite(result) or result <= 0:
        raise ValueError("Comparison values must be positive finite numbers.")
    return result


def display_saaty(value: float, tolerance: float = 1e-9) -> str:
    for scale_value in SAATY_SCALE:
        if isclose(value, scale_value, rel_tol=tolerance, abs_tol=tolerance):
            if scale_value < 1:
                return f"1/{round(1 / scale_value)}"
            return str(round(scale_value))
    return f"{value:.6g}"


def saaty_bounds(value: float, steps: int = 1) -> tuple[float, float]:
    if steps < 1:
        raise ValueError("Saaty steps must be at least one.")
    matches = [i for i, item in enumerate(SAATY_SCALE) if isclose(value, item, rel_tol=1e-9)]
    if not matches:
        raise ValueError(f"{value:g} is not on the configured Saaty scale.")
    index = matches[0]
    return SAATY_SCALE[max(0, index - steps)], SAATY_SCALE[min(len(SAATY_SCALE) - 1, index + steps)]


def validate_matrix(
    matrix: Sequence[Sequence[object]],
    labels: Sequence[object],
    matrix_range: A1Range,
    tolerance: float = 1e-9,
) -> tuple[tuple[float, ...], ...]:
    errors: list[str] = []
    size = len(matrix)
    if size == 0 or any(len(row) != size for row in matrix):
        errors.append("Pairwise matrix must be non-empty and square.")
    if matrix_range.rows != size or matrix_range.columns != size:
        errors.append(
            f"Range dimensions {matrix_range.rows}x{matrix_range.columns} do not match matrix data."
        )
    if len(labels) != size:
        errors.append(f"Expected {size} property labels, received {len(labels)}.")
    numeric: list[list[float]] = []
    for row_index, row_values in enumerate(matrix):
        converted: list[float] = []
        for column_index, value in enumerate(row_values):
            address = (
                matrix_range.address(row_index, column_index)
                if row_index < matrix_range.rows and column_index < matrix_range.columns
                else f"[{row_index},{column_index}]"
            )
            try:
                converted.append(parse_saaty_value(value))
            except ValueError as exc:
                errors.append(f"{address}: {exc}")
                converted.append(float("nan"))
        numeric.append(converted)
    if len(numeric) == size and all(len(row) == size for row in numeric):
        for index in range(size):
            if not isclose(numeric[index][index], 1.0, rel_tol=tolerance, abs_tol=tolerance):
                errors.append(f"{matrix_range.address(index, index)}: diagonal value must equal 1.")
        for row in range(size):
            for column in range(row + 1, size):
                product = numeric[row][column] * numeric[column][row]
                if not isfinite(product) or not isclose(
                    product, 1.0, rel_tol=tolerance, abs_tol=tolerance
                ):
                    upper = matrix_range.address(row, column)
                    lower = matrix_range.address(column, row)
                    errors.append(f"{upper} and {lower} are not reciprocal.")
    if errors:
        raise MatrixValidationError(errors)
    return tuple(tuple(row) for row in numeric)


def enumerate_comparisons(
    matrix: Sequence[Sequence[float]], labels: Sequence[str], matrix_range: A1Range, steps: int = 1
) -> tuple[Comparison, ...]:
    comparisons: list[Comparison] = []
    for row in range(len(matrix)):
        for column in range(row + 1, len(matrix)):
            baseline = float(matrix[row][column])
            low, high = saaty_bounds(baseline, steps)
            comparisons.append(
                Comparison(
                    row=row,
                    column=column,
                    name=f"{labels[row]} vs. {labels[column]}",
                    input_cell=matrix_range.address(row, column),
                    reciprocal_cell=matrix_range.address(column, row),
                    baseline=baseline,
                    low=low,
                    high=high,
                )
            )
    return tuple(comparisons)
