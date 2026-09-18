import json

import pytest

from wpi_sensitivity.config import ConfigurationError, config_from_dict, load_config, save_config


def minimal_config() -> dict[str, object]:
    return {
        "schema_version": 1,
        "workbook": "model.xlsx",
        "worksheet": "Model",
        "matrix": {"values": "B2:C3", "row_labels": "A2:A3", "column_labels": "B1:C1"},
        "outputs": {"values": "F2:F3", "labels": "E2:E3"},
    }


def test_rejects_unknown_schema_version() -> None:
    raw = minimal_config()
    raw["schema_version"] = 99
    with pytest.raises(ConfigurationError, match="Migrate"):
        config_from_dict(raw)


def test_round_trip(tmp_path) -> None:
    config = config_from_dict(minimal_config())
    path = tmp_path / "preset.json"
    save_config(config, path)
    loaded = load_config(path)
    assert loaded == config
    assert json.loads(path.read_text())["schema_version"] == 1
