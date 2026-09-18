from __future__ import annotations

from pathlib import Path
from typing import Any

from wpi_sensitivity.config import (
    AnalysisConfig,
    MatrixConfig,
    OutputsConfig,
    VariationConfig,
)
from wpi_sensitivity.logging_service import RunLogger, read_log
from wpi_sensitivity.sensitivity import SensitivityRunner, build_run_plan


class FakeWorkbook:
    def __init__(self, fail_on_calculation: int | None = None) -> None:
        self.cells: dict[str, Any] = {
            "A2": "Cost",
            "A3": "Strength",
            "B1": "Cost",
            "C1": "Strength",
            "B2": 1.0,
            "C2": 2.0,
            "B3": 0.5,
            "C3": 1.0,
            "E2": "Score",
            "F2": 20.0,
            "F4": "Steel",
        }
        self.formulas = {"B3": "=1/C2", "F2": "=C2*10"}
        self.calculations = 0
        self.fail_on_calculation = fail_on_calculation

    def read_range(self, sheet: str, reference: str) -> Any:
        ranges = {
            "B2:C3": [[self.cells["B2"], self.cells["C2"]], [self.cells["B3"], self.cells["C3"]]],
            "A2:A3": [[self.cells["A2"]], [self.cells["A3"]]],
            "B1:C1": [[self.cells["B1"], self.cells["C1"]]],
            "E2:E2": self.cells["E2"],
            "F2:F2": self.cells["F2"],
        }
        return ranges[reference]

    def read_cell(self, sheet: str, address: str) -> Any:
        return self.cells[address]

    def read_formula(self, sheet: str, address: str) -> Any:
        return self.formulas.get(address, self.cells[address])

    def write_cell(self, sheet: str, address: str, value: Any) -> None:
        if isinstance(value, str) and value.startswith("="):
            self.formulas[address] = value
            if address == "B3":
                self.cells[address] = 1 / self.cells["C2"]
        else:
            self.cells[address] = value

    def calculate(self, full_rebuild: bool = True) -> None:
        self.calculations += 1
        if self.fail_on_calculation == self.calculations:
            raise RuntimeError("simulated Excel failure")
        self.cells["B3"] = 1 / self.cells["C2"]
        self.cells["F2"] = self.cells["C2"] * 10

    def close(self) -> None:
        pass


def config() -> AnalysisConfig:
    return AnalysisConfig(
        workbook="model.xlsx",
        worksheet="Model",
        matrix=MatrixConfig("B2:C3", "A2:A3", "B1:C1"),
        outputs=OutputsConfig("F2:F2", "E2:E2", winner="F4"),
        variation=VariationConfig(steps=1),
    )


def test_builds_and_executes_plan_with_restoration(tmp_path: Path) -> None:
    workbook = FakeWorkbook()
    plan = build_run_plan(workbook, config())
    assert plan.evaluation_count == 3
    with RunLogger(tmp_path, config(), "test") as logger:
        summary = SensitivityRunner(workbook, config(), plan, logger).execute()
    assert summary.status == "completed"
    assert summary.restoration_verified
    assert workbook.cells["C2"] == 2.0
    assert workbook.cells["B3"] == 0.5
    rows = read_log(Path(summary.run_directory) / "results.csv")
    assert [row["scenario"] for row in rows] == ["baseline", "low", "high"]


def test_restores_matrix_after_failure(tmp_path: Path) -> None:
    workbook = FakeWorkbook(fail_on_calculation=3)
    plan = build_run_plan(workbook, config())
    with RunLogger(tmp_path, config(), "test") as logger:
        summary = SensitivityRunner(workbook, config(), plan, logger).execute()
    assert summary.status == "failed"
    assert summary.restoration_verified
    assert workbook.cells["C2"] == 2.0
    assert workbook.cells["B3"] == 0.5
