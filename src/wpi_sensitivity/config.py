from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


class ConfigurationError(ValueError):
    """A preset is invalid or unsupported."""


@dataclass(frozen=True)
class MatrixConfig:
    values: str
    row_labels: str
    column_labels: str
    reciprocal_tolerance: float = 1e-9


@dataclass(frozen=True)
class OutputsConfig:
    values: str
    labels: str
    winner: str | None = None
    material_ranking: str | None = None
    property_weights: str | None = None


@dataclass(frozen=True)
class VariationConfig:
    method: str = "saaty_steps"
    steps: int = 1
    consistency_ratio_limit: float = 0.1


@dataclass(frozen=True)
class RunConfig:
    use_working_copy: bool = True
    full_calculation_rebuild: bool = True
    restore_after_each_test: bool = True
    stop_on_restoration_failure: bool = True
    log_each_result: bool = True


@dataclass(frozen=True)
class AnalysisConfig:
    workbook: str
    worksheet: str
    matrix: MatrixConfig
    outputs: OutputsConfig
    variation: VariationConfig = field(default_factory=VariationConfig)
    run: RunConfig = field(default_factory=RunConfig)
    schema_version: int = 1

    def resolved_workbook(self, preset_path: str | Path | None = None) -> Path:
        path = Path(self.workbook).expanduser()
        if not path.is_absolute() and preset_path is not None:
            path = Path(preset_path).resolve().parent / path
        return path.resolve()


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigurationError(f"'{name}' must be a JSON object.")
    return value


def config_from_dict(raw: dict[str, Any]) -> AnalysisConfig:
    version = raw.get("schema_version")
    if version != 1:
        raise ConfigurationError(
            f"Unsupported schema_version {version!r}; this release accepts version 1. "
            "Migrate the preset before loading it."
        )
    try:
        matrix_raw = _mapping(raw["matrix"], "matrix")
        outputs_raw = _mapping(raw["outputs"], "outputs")
        variation_raw = _mapping(raw.get("variation", {}), "variation")
        run_raw = _mapping(raw.get("run", {}), "run")
        config = AnalysisConfig(
            schema_version=1,
            workbook=str(raw["workbook"]),
            worksheet=str(raw["worksheet"]),
            matrix=MatrixConfig(**matrix_raw),
            outputs=OutputsConfig(**outputs_raw),
            variation=VariationConfig(**variation_raw),
            run=RunConfig(**run_raw),
        )
    except (KeyError, TypeError) as exc:
        raise ConfigurationError(f"Invalid preset structure: {exc}") from exc
    validate_config(config)
    return config


def validate_config(config: AnalysisConfig) -> None:
    if not config.workbook.strip():
        raise ConfigurationError("Workbook path is required.")
    if not config.worksheet.strip():
        raise ConfigurationError("Worksheet name is required.")
    for name, value in (
        ("matrix.values", config.matrix.values),
        ("matrix.row_labels", config.matrix.row_labels),
        ("matrix.column_labels", config.matrix.column_labels),
        ("outputs.values", config.outputs.values),
        ("outputs.labels", config.outputs.labels),
    ):
        if not value.strip():
            raise ConfigurationError(f"{name} is required.")
    if config.matrix.reciprocal_tolerance <= 0:
        raise ConfigurationError("reciprocal_tolerance must be positive.")
    if config.variation.method not in {"saaty_steps", "percentage", "full_sweep"}:
        raise ConfigurationError(f"Unknown variation method: {config.variation.method}")
    if config.variation.steps < 1:
        raise ConfigurationError("variation.steps must be at least 1.")
    if config.variation.consistency_ratio_limit < 0:
        raise ConfigurationError("consistency_ratio_limit cannot be negative.")


def load_config(path: str | Path) -> AnalysisConfig:
    preset = Path(path)
    try:
        raw = json.loads(preset.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Could not load preset '{preset}': {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError("Preset root must be a JSON object.")
    return config_from_dict(raw)


def save_config(config: AnalysisConfig, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(asdict(config), indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
