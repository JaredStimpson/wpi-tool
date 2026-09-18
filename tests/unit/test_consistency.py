import pytest

from wpi_sensitivity.consistency import calculate_consistency


def test_consistent_matrix_has_zero_ratio() -> None:
    matrix = ((1, 2, 4), (0.5, 1, 2), (0.25, 0.5, 1))
    result = calculate_consistency(matrix)
    assert result.lambda_max == pytest.approx(3, abs=1e-10)
    assert result.consistency_ratio == pytest.approx(0, abs=1e-10)


def test_known_inconsistent_matrix() -> None:
    matrix = ((1, 3, 5), (1 / 3, 1, 7), (1 / 5, 1 / 7, 1))
    result = calculate_consistency(matrix)
    assert result.consistency_ratio > 0.1
