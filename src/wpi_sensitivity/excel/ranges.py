from __future__ import annotations

import re
from dataclasses import dataclass


class RangeReferenceError(ValueError):
    pass


_REFERENCE = re.compile(
    r"^(?:(?:'(?P<quoted>(?:[^']|'')+)'|(?P<plain>[^'!]+))!)?"
    r"\$?(?P<c1>[A-Za-z]{1,3})\$?(?P<r1>[1-9][0-9]*)"
    r"(?::\$?(?P<c2>[A-Za-z]{1,3})\$?(?P<r2>[1-9][0-9]*))?$"
)


def column_number(letters: str) -> int:
    result = 0
    for character in letters.upper():
        result = result * 26 + ord(character) - ord("A") + 1
    return result


def column_letters(number: int) -> str:
    if number < 1:
        raise ValueError("Column number must be positive.")
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


@dataclass(frozen=True)
class A1Range:
    sheet: str | None
    start_row: int
    start_column: int
    end_row: int
    end_column: int

    @property
    def rows(self) -> int:
        return self.end_row - self.start_row + 1

    @property
    def columns(self) -> int:
        return self.end_column - self.start_column + 1

    @property
    def cell_count(self) -> int:
        return self.rows * self.columns

    def address(self, row_offset: int = 0, column_offset: int = 0) -> str:
        if not 0 <= row_offset < self.rows or not 0 <= column_offset < self.columns:
            raise IndexError("Cell offset is outside the range.")
        return f"{column_letters(self.start_column + column_offset)}{self.start_row + row_offset}"

    def cells(self) -> tuple[str, ...]:
        return tuple(
            self.address(row, column) for row in range(self.rows) for column in range(self.columns)
        )

    def overlaps(self, other: A1Range) -> bool:
        if self.sheet and other.sheet and self.sheet.casefold() != other.sheet.casefold():
            return False
        return not (
            self.end_row < other.start_row
            or other.end_row < self.start_row
            or self.end_column < other.start_column
            or other.end_column < self.start_column
        )


def parse_a1(reference: str) -> A1Range:
    match = _REFERENCE.fullmatch(reference.strip())
    if match is None:
        raise RangeReferenceError(f"Invalid Excel A1 reference: {reference!r}")
    sheet = match.group("quoted") or match.group("plain")
    if match.group("quoted"):
        sheet = sheet.replace("''", "'")
    c1 = column_number(match.group("c1"))
    r1 = int(match.group("r1"))
    c2 = column_number(match.group("c2") or match.group("c1"))
    r2 = int(match.group("r2") or match.group("r1"))
    if r2 < r1 or c2 < c1:
        raise RangeReferenceError("Ranges must run from top-left to bottom-right.")
    return A1Range(sheet, r1, c1, r2, c2)
