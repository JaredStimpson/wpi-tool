from __future__ import annotations

import csv
import json
import os
import platform
import sys
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import AnalysisConfig
from .models import EvaluationResult, OutputDefinition, OutputValue

LOG_FIELDS = (
    "run_id",
    "timestamp_utc",
    "workbook_name",
    "worksheet_name",
    "comparison_name",
    "input_cell",
    "reciprocal_cell",
    "scenario",
    "baseline_input",
    "test_input",
    "reciprocal_input",
    "output_name",
    "output_cell",
    "output_kind",
    "baseline_output",
    "test_output",
    "absolute_change",
    "percent_change",
    "consistency_index",
    "consistency_ratio",
    "consistency_status",
    "baseline_winner",
    "test_winner",
    "winner_changed",
    "calculation_seconds",
    "status",
    "error_message",
)


class RunLogger:
    def __init__(self, root: str | Path, config: AnalysisConfig, app_version: str) -> None:
        self.run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
        self.directory = Path(root) / self.run_id
        self.directory.mkdir(parents=True, exist_ok=False)
        self.csv_path = self.directory / "results.csv"
        self.metadata_path = self.directory / "metadata.json"
        self._config = config
        self._handle = self.csv_path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._handle, fieldnames=LOG_FIELDS)
        self._writer.writeheader()
        self._flush()
        self.write_metadata(
            {
                "run_id": self.run_id,
                "status": "running",
                "application_version": app_version,
                "python_version": sys.version,
                "operating_system": platform.platform(),
                "start_time_utc": datetime.now(UTC).isoformat(),
                "configuration": asdict(config),
                "restoration_verified": False,
            }
        )

    def _flush(self) -> None:
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def append(
        self,
        result: EvaluationResult,
        outputs: tuple[OutputDefinition, ...],
        baseline_outputs: tuple[OutputValue, ...],
        workbook_name: str,
        worksheet: str,
        baseline_winner: str | None,
        cr_limit: float,
    ) -> None:
        for definition, baseline, tested in zip(
            outputs, baseline_outputs, result.outputs, strict=True
        ):
            baseline_number = baseline.value if baseline.kind == "number" else ""
            tested_number = tested.value if tested.kind == "number" else ""
            absolute = (
                tested.value - baseline.value if baseline.kind == tested.kind == "number" else ""
            )
            percent = (
                absolute / abs(baseline.value) * 100
                if isinstance(absolute, float) and baseline.value != 0
                else ""
            )
            self._writer.writerow(
                {
                    "run_id": self.run_id,
                    "timestamp_utc": result.timestamp_utc,
                    "workbook_name": workbook_name,
                    "worksheet_name": worksheet,
                    "comparison_name": result.comparison_name,
                    "input_cell": result.input_cell,
                    "reciprocal_cell": result.reciprocal_cell,
                    "scenario": result.scenario,
                    "baseline_input": result.baseline_input,
                    "test_input": result.test_input,
                    "reciprocal_input": result.reciprocal_input,
                    "output_name": definition.name,
                    "output_cell": definition.cell,
                    "output_kind": tested.kind,
                    "baseline_output": baseline_number,
                    "test_output": tested_number,
                    "absolute_change": absolute,
                    "percent_change": percent,
                    "consistency_index": result.consistency_index,
                    "consistency_ratio": result.consistency_ratio,
                    "consistency_status": "warning"
                    if result.consistency_ratio > cr_limit
                    else "ok",
                    "baseline_winner": baseline_winner or "",
                    "test_winner": result.winner or "",
                    "winner_changed": bool(baseline_winner and result.winner != baseline_winner),
                    "calculation_seconds": result.calculation_seconds,
                    "status": result.status,
                    "error_message": result.error_message,
                }
            )
        self._flush()

    def write_metadata(self, values: dict[str, Any]) -> None:
        current: dict[str, Any] = {}
        if self.metadata_path.exists():
            current = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        current.update(values)
        temporary = self.metadata_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(current, indent=2, default=str) + "\n", encoding="utf-8")
        temporary.replace(self.metadata_path)

    def close(self, status: str, restoration_verified: bool, **extra: Any) -> None:
        if self._handle.closed:
            return
        self._flush()
        self._handle.close()
        self.write_metadata(
            {
                "status": status,
                "restoration_verified": restoration_verified,
                "end_time_utc": datetime.now(UTC).isoformat(),
                **extra,
            }
        )

    def __enter__(self) -> RunLogger:
        return self

    def __exit__(self, *_: object) -> None:
        if not self._handle.closed:
            self.close("failed", False, error_message="Run logger closed before completion.")


def read_log(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
