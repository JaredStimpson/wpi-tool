import pytest

from wpi_sensitivity.excel.ranges import parse_a1
from wpi_sensitivity.matrix import (
    MatrixValidationError,
    display_saaty,
    enumerate_comparisons,
    parse_saaty_value,
    saaty_bounds,
    validate_matrix,
)


def test_fraction_parsing_and_display() -> None:
    assert parse_saaty_value("1/3") == pytest.approx(1 / 3)
    assert display_saaty(0.25) == "1/4"
    assert display_saaty(3.0) == "3"


def test_adjacent_scale_bounds() -> None:
    assert saaty_bounds(3) == (2, 4)
    assert saaty_bounds(1) == (0.5, 2)
    assert saaty_bounds(1 / 3) == (0.25, 0.5)
    assert saaty_bounds(9) == (8, 9)


def test_matrix_validation_and_comparison_addresses() -> None:
    matrix = [[1, 2, 4], [0.5, 1, 2], [0.25, 0.5, 1]]
    reference = parse_a1("C5:E7")
    validated = validate_matrix(matrix, ["Cost", "Strength", "Mass"], reference)
    comparisons = enumerate_comparisons(validated, ["Cost", "Strength", "Mass"], reference)
    assert len(comparisons) == 3
    assert comparisons[0].name == "Cost vs. Strength"
    assert comparisons[0].input_cell == "D5"
    assert comparisons[0].reciprocal_cell == "C6"


def test_reports_specific_nonreciprocal_cells() -> None:
    with pytest.raises(MatrixValidationError, match="B1 and A2"):
        validate_matrix([[1, 3], [0.5, 1]], ["A", "B"], parse_a1("A1:B2"))
