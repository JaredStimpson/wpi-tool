import pytest

from wpi_sensitivity.excel.ranges import RangeReferenceError, column_letters, parse_a1


def test_parses_quoted_sheet_and_absolute_range() -> None:
    result = parse_a1("'WPI Model'!$C$5:$G$9")
    assert result.sheet == "WPI Model"
    assert (result.rows, result.columns, result.cell_count) == (5, 5, 25)
    assert result.address(4, 4) == "G9"


def test_generates_excel_column_letters() -> None:
    assert column_letters(1) == "A"
    assert column_letters(27) == "AA"
    assert column_letters(703) == "AAA"


def test_rejects_reversed_range() -> None:
    with pytest.raises(RangeReferenceError):
        parse_a1("G9:C5")


def test_overlap_respects_sheet_names() -> None:
    assert parse_a1("A1:C3").overlaps(parse_a1("C3:D4"))
    assert not parse_a1("One!A1:C3").overlaps(parse_a1("Two!A1:C3"))
