from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from math import pi
from pathlib import Path

from .logging_service import read_log


def tornado_data(
    log_path: str | Path, output_name: str, include_inconsistent: bool = True
) -> list[dict[str, float | str]]:
    grouped: dict[str, dict[str, float | str]] = defaultdict(dict)
    for row in read_log(log_path):
        if (
            row["output_name"] != output_name
            or row["scenario"] == "baseline"
            or row["status"] != "completed"
        ):
            continue
        if not include_inconsistent and row["consistency_status"] == "warning":
            continue
        grouped[row["comparison_name"]][row["scenario"]] = float(row["test_output"])
        grouped[row["comparison_name"]]["baseline"] = float(row["baseline_output"])
    result = [
        {
            "comparison": name,
            "low": values["low"],
            "high": values["high"],
            "baseline": values["baseline"],
            "range": abs(float(values["high"]) - float(values["low"])),
        }
        for name, values in grouped.items()
        if {"low", "high", "baseline"} <= values.keys()
    ]
    return sorted(result, key=lambda item: float(item["range"]), reverse=True)


def save_tornado(log_path: str | Path, output_name: str, destination: str | Path) -> Path:
    import matplotlib.pyplot as plt

    data = tornado_data(log_path, output_name)
    if not data:
        raise ValueError(f"No numeric low/high results found for output {output_name!r}.")
    names = [str(item["comparison"]) for item in reversed(data)]
    baseline = float(data[0]["baseline"])
    lows = [float(item["low"]) - baseline for item in reversed(data)]
    highs = [float(item["high"]) - baseline for item in reversed(data)]
    positions = range(len(names))
    figure, axis = plt.subplots(figsize=(10, max(4, len(names) * 0.45)))
    axis.barh(positions, lows, color="#4C78A8", label="Low scenario")
    axis.barh(positions, highs, color="#F58518", label="High scenario")
    axis.axvline(0, color="#222222", linewidth=1)
    axis.set_yticks(list(positions), labels=names)
    axis.set_xlabel(f"Change from baseline ({baseline:g})")
    axis.set_title(f"Sensitivity of {output_name}")
    axis.legend()
    figure.tight_layout()
    target = Path(destination)
    figure.savefig(target, dpi=160)
    plt.close(figure)
    return target


def save_radar(
    labels: Sequence[str], series: dict[str, Sequence[float]], destination: str | Path
) -> Path:
    import matplotlib.pyplot as plt

    if len(labels) < 3 or any(len(values) != len(labels) for values in series.values()):
        raise ValueError("Radar plots need at least three axes and equally sized series.")
    angles = [2 * pi * index / len(labels) for index in range(len(labels))]
    angles += angles[:1]
    figure, axis = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
    all_values = [float(value) for values in series.values() for value in values]
    lower, upper = min(0.0, min(all_values)), max(all_values)
    for name, values in series.items():
        closed = [float(value) for value in values] + [float(values[0])]
        axis.plot(angles, closed, label=name)
        axis.fill(angles, closed, alpha=0.08)
    axis.set_xticks(angles[:-1], labels=labels)
    axis.set_ylim(lower, upper if upper > lower else lower + 1)
    axis.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
    figure.tight_layout()
    target = Path(destination)
    figure.savefig(target, dpi=160)
    plt.close(figure)
    return target
