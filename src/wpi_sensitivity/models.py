from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class Comparison:
    row: int
    column: int
    name: str
    input_cell: str
    reciprocal_cell: str
    baseline: float
    low: float
    high: float
    enabled: bool = True


@dataclass(frozen=True)
class OutputDefinition:
    name: str
    cell: str


@dataclass(frozen=True)
class RunPlan:
    comparisons: tuple[Comparison, ...]
    outputs: tuple[OutputDefinition, ...]
    baseline_matrix: tuple[tuple[float, ...], ...]
    labels: tuple[str, ...]

    @property
    def evaluation_count(self) -> int:
        return 1 + 2 * sum(item.enabled for item in self.comparisons)


@dataclass(frozen=True)
class OutputValue:
    kind: str
    value: Any

    @classmethod
    def classify(cls, value: Any) -> OutputValue:
        if value is None:
            return cls("blank", None)
        if isinstance(value, bool):
            return cls("text", str(value))
        if isinstance(value, int | float):
            return cls("number", float(value))
        text = str(value)
        if text.startswith("#"):
            return cls("formula_error", text)
        return cls("text", text)


@dataclass(frozen=True)
class EvaluationResult:
    scenario: str
    comparison_name: str
    input_cell: str
    reciprocal_cell: str
    baseline_input: float
    test_input: float
    reciprocal_input: float
    outputs: tuple[OutputValue, ...]
    consistency_index: float
    consistency_ratio: float
    calculation_seconds: float
    winner: str | None = None
    status: str = "completed"
    error_message: str = ""
    timestamp_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    status: str
    completed_evaluations: int
    expected_evaluations: int
    restoration_verified: bool
    run_directory: str
    error_message: str = ""
