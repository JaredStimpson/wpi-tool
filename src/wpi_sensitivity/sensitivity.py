from __future__ import annotations

import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import __version__
from .config import AnalysisConfig
from .consistency import calculate_consistency
from .excel.connection import WorkbookAdapter, XlwingsWorkbook, flatten_range
from .excel.ranges import parse_a1
from .excel.restoration import outputs_match
from .logging_service import RunLogger
from .matrix import enumerate_comparisons, validate_matrix
from .models import EvaluationResult, OutputDefinition, OutputValue, RunPlan, RunSummary


class CancellationRequested(RuntimeError):
    pass


class RestorationError(RuntimeError):
    pass


def _as_2d(value: Any) -> list[list[Any]]:
    if not isinstance(value, list):
        return [[value]]
    if value and not isinstance(value[0], list):
        return [value]
    return value


def build_run_plan(workbook: WorkbookAdapter, config: AnalysisConfig) -> RunPlan:
    matrix_range = parse_a1(config.matrix.values)
    parse_a1(config.matrix.row_labels)
    parse_a1(config.matrix.column_labels)
    output_range = parse_a1(config.outputs.values)
    output_label_range = parse_a1(config.outputs.labels)
    if matrix_range.overlaps(output_range):
        raise ValueError("Matrix and output ranges overlap and could corrupt the model.")
    row_labels = [
        str(item).strip()
        for item in flatten_range(workbook.read_range(config.worksheet, config.matrix.row_labels))
    ]
    column_labels = [
        str(item).strip()
        for item in flatten_range(
            workbook.read_range(config.worksheet, config.matrix.column_labels)
        )
    ]
    if row_labels != column_labels:
        raise ValueError(
            "Row and column labels must identify the same properties in the same order."
        )
    matrix = validate_matrix(
        _as_2d(workbook.read_range(config.worksheet, config.matrix.values)),
        row_labels,
        matrix_range,
        config.matrix.reciprocal_tolerance,
    )
    output_labels = [
        str(item).strip()
        for item in flatten_range(workbook.read_range(config.worksheet, config.outputs.labels))
    ]
    if (
        output_range.cell_count != output_label_range.cell_count
        or len(output_labels) != output_range.cell_count
    ):
        raise ValueError(
            "Output-value and output-label ranges must contain the same number of cells."
        )
    outputs = tuple(
        OutputDefinition(name, cell)
        for name, cell in zip(output_labels, output_range.cells(), strict=True)
    )
    comparisons = enumerate_comparisons(matrix, row_labels, matrix_range, config.variation.steps)
    return RunPlan(comparisons, outputs, matrix, tuple(row_labels))


def _read_outputs(
    workbook: WorkbookAdapter, sheet: str, outputs: tuple[OutputDefinition, ...]
) -> tuple[OutputValue, ...]:
    return tuple(OutputValue.classify(workbook.read_cell(sheet, item.cell)) for item in outputs)


def _raw_outputs(values: tuple[OutputValue, ...]) -> tuple[Any, ...]:
    return tuple(item.value for item in values)


class SensitivityRunner:
    def __init__(
        self, workbook: WorkbookAdapter, config: AnalysisConfig, plan: RunPlan, logger: RunLogger
    ) -> None:
        self.workbook = workbook
        self.config = config
        self.plan = plan
        self.logger = logger

    def execute(
        self,
        progress: Callable[[int, int, str], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> RunSummary:
        sheet = self.config.worksheet
        matrix_range = parse_a1(self.config.matrix.values)
        original: dict[str, Any] = {}
        for row in range(matrix_range.rows):
            for column in range(matrix_range.columns):
                address = matrix_range.address(row, column)
                formula = self.workbook.read_formula(sheet, address)
                original[address] = (
                    formula
                    if isinstance(formula, str) and formula.startswith("=")
                    else self.workbook.read_cell(sheet, address)
                )
        completed = 0
        restoration_verified = False
        status = "failed"
        error_message = ""
        baseline_values: tuple[OutputValue, ...] = ()
        baseline_winner: str | None = None
        try:
            self.workbook.calculate(self.config.run.full_calculation_rebuild)
            baseline_values = _read_outputs(self.workbook, sheet, self.plan.outputs)
            if self.config.outputs.winner:
                winner_value = self.workbook.read_cell(sheet, self.config.outputs.winner)
                baseline_winner = None if winner_value is None else str(winner_value)
            baseline_consistency = calculate_consistency(self.plan.baseline_matrix)
            baseline_result = EvaluationResult(
                scenario="baseline",
                comparison_name="Baseline",
                input_cell="",
                reciprocal_cell="",
                baseline_input=1.0,
                test_input=1.0,
                reciprocal_input=1.0,
                outputs=baseline_values,
                consistency_index=baseline_consistency.consistency_index,
                consistency_ratio=baseline_consistency.consistency_ratio,
                calculation_seconds=0.0,
                winner=baseline_winner,
            )
            self.logger.append(
                baseline_result,
                self.plan.outputs,
                baseline_values,
                Path(self.config.workbook).name,
                sheet,
                baseline_winner,
                self.config.variation.consistency_ratio_limit,
            )
            completed = 1
            if progress:
                progress(completed, self.plan.evaluation_count, "Baseline")
            for comparison in self.plan.comparisons:
                if not comparison.enabled:
                    continue
                for scenario, test_value in (("low", comparison.low), ("high", comparison.high)):
                    if cancelled and cancelled():
                        raise CancellationRequested("Cancellation requested by user.")
                    result = self._evaluate(comparison, scenario, test_value)
                    self.logger.append(
                        result,
                        self.plan.outputs,
                        baseline_values,
                        Path(self.config.workbook).name,
                        sheet,
                        baseline_winner,
                        self.config.variation.consistency_ratio_limit,
                    )
                    completed += 1
                    if progress:
                        progress(
                            completed, self.plan.evaluation_count, f"{comparison.name} ({scenario})"
                        )
            status = "completed"
        except CancellationRequested as exc:
            status, error_message = "cancelled", str(exc)
        except Exception as exc:
            status, error_message = "failed", str(exc)
        finally:
            restore_errors: list[str] = []
            for address, value in original.items():
                try:
                    self.workbook.write_cell(sheet, address, value)
                except Exception as exc:
                    restore_errors.append(f"{address}: {exc}")
            try:
                self.workbook.calculate(self.config.run.full_calculation_rebuild)
                actual = _read_outputs(self.workbook, sheet, self.plan.outputs)
                restoration_verified = bool(baseline_values) and outputs_match(
                    _raw_outputs(baseline_values),
                    _raw_outputs(actual),
                    self.config.matrix.reciprocal_tolerance,
                )
            except Exception as exc:
                restore_errors.append(f"recalculation: {exc}")
            if restore_errors or not restoration_verified:
                status = "restoration-failed"
                details = "; ".join(restore_errors) or "Restored outputs differ from baseline."
                error_message = f"{error_message}; {details}".strip("; ")
            self.logger.close(
                status,
                restoration_verified,
                completed_evaluations=completed,
                expected_evaluations=self.plan.evaluation_count,
                error_message=error_message,
            )
        return RunSummary(
            self.logger.run_id,
            status,
            completed,
            self.plan.evaluation_count,
            restoration_verified,
            str(self.logger.directory),
            error_message,
        )

    def _evaluate(self, comparison: Any, scenario: str, test_value: float) -> EvaluationResult:
        sheet = self.config.worksheet
        started = time.perf_counter()
        try:
            self.workbook.write_cell(sheet, comparison.input_cell, test_value)
            self.workbook.write_cell(sheet, comparison.reciprocal_cell, 1.0 / test_value)
            self.workbook.calculate(self.config.run.full_calculation_rebuild)
            outputs = _read_outputs(self.workbook, sheet, self.plan.outputs)
            matrix = [list(row) for row in self.plan.baseline_matrix]
            matrix[comparison.row][comparison.column] = test_value
            matrix[comparison.column][comparison.row] = 1.0 / test_value
            consistency = calculate_consistency(matrix)
            winner = None
            if self.config.outputs.winner:
                raw_winner = self.workbook.read_cell(sheet, self.config.outputs.winner)
                winner = None if raw_winner is None else str(raw_winner)
            return EvaluationResult(
                scenario=scenario,
                comparison_name=comparison.name,
                input_cell=comparison.input_cell,
                reciprocal_cell=comparison.reciprocal_cell,
                baseline_input=comparison.baseline,
                test_input=test_value,
                reciprocal_input=1.0 / test_value,
                outputs=outputs,
                consistency_index=consistency.consistency_index,
                consistency_ratio=consistency.consistency_ratio,
                calculation_seconds=time.perf_counter() - started,
                winner=winner,
            )
        finally:
            self.workbook.write_cell(sheet, comparison.input_cell, comparison.baseline)
            self.workbook.write_cell(sheet, comparison.reciprocal_cell, 1.0 / comparison.baseline)
            self.workbook.calculate(self.config.run.full_calculation_rebuild)


def run_excel_analysis(
    config: AnalysisConfig,
    results_root: str | Path,
    visible: bool = False,
    progress: Callable[[int, int, str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> RunSummary:
    source = config.resolved_workbook()
    if not source.is_file():
        raise FileNotFoundError(f"Workbook not found: {source}")
    with RunLogger(results_root, config, __version__) as logger:
        working_path = source
        if config.run.use_working_copy:
            working_path = logger.directory / f"working-{source.name}"
            shutil.copy2(source, working_path)
            logger.write_metadata(
                {
                    "source_fingerprint": {
                        "size": source.stat().st_size,
                        "modified_ns": source.stat().st_mtime_ns,
                    },
                    "working_copy": working_path.name,
                }
            )
        workbook = XlwingsWorkbook(working_path, visible=visible)
        try:
            plan = build_run_plan(workbook, config)
            runner = SensitivityRunner(workbook, config, plan, logger)
            return runner.execute(progress=progress, cancelled=cancelled)
        finally:
            workbook.close()
