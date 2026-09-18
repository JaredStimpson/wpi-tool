from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WorkbookAdapter(Protocol):
    """Minimal workbook boundary used by the runner and portable tests."""

    def read_range(self, sheet: str, reference: str) -> Any: ...
    def read_cell(self, sheet: str, address: str) -> Any: ...
    def read_formula(self, sheet: str, address: str) -> Any: ...
    def write_cell(self, sheet: str, address: str, value: Any) -> None: ...
    def calculate(self, full_rebuild: bool = True) -> None: ...
    def close(self) -> None: ...


class XlwingsWorkbook:
    """Workbook adapter that owns a hidden Excel instance and one workbook."""

    def __init__(self, path: str | Path, visible: bool = False) -> None:
        try:
            import xlwings as xw  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError("xlwings is not installed; run setup before using Excel.") from exc
        self._app = xw.App(visible=visible, add_book=False)
        self._app.display_alerts = False
        self._app.screen_updating = visible
        try:
            self._book = self._app.books.open(
                str(Path(path).resolve()), update_links=False, read_only=False
            )
        except Exception:
            self._app.quit()
            raise
        self._closed = False

    def _range(self, sheet: str, reference: str) -> Any:
        try:
            return self._book.sheets[sheet].range(reference)
        except Exception as exc:
            raise RuntimeError(f"Cannot access '{sheet}'!{reference}: {exc}") from exc

    def read_range(self, sheet: str, reference: str) -> Any:
        return self._range(sheet, reference).value

    def read_cell(self, sheet: str, address: str) -> Any:
        return self._range(sheet, address).value

    def read_formula(self, sheet: str, address: str) -> Any:
        return self._range(sheet, address).formula

    def write_cell(self, sheet: str, address: str, value: Any) -> None:
        cell = self._range(sheet, address)
        if isinstance(value, str) and value.startswith("="):
            cell.formula = value
        else:
            cell.value = value

    def calculate(self, full_rebuild: bool = True) -> None:
        if full_rebuild:
            self._app.api.CalculateFullRebuild()
        else:
            self._app.calculate()
        # xlwings calculation is synchronous for COM calls; reading CalculationState
        # provides an explicit guard for workbooks with asynchronous dependencies.
        import time

        deadline = time.monotonic() + 300
        while int(self._app.api.CalculationState) != 0:
            if time.monotonic() >= deadline:
                raise TimeoutError("Excel calculation did not finish within 300 seconds.")
            time.sleep(0.05)

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._book.close()
        finally:
            self._app.quit()
            self._closed = True

    def __enter__(self) -> XlwingsWorkbook:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def flatten_range(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        flattened: list[Any] = []
        for item in value:
            if isinstance(item, Sequence) and not isinstance(item, str | bytes):
                flattened.extend(item)
            else:
                flattened.append(item)
        return flattened
    return [value]
