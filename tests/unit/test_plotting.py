import csv

from wpi_sensitivity.logging_service import LOG_FIELDS
from wpi_sensitivity.plotting import tornado_data


def test_tornado_sorts_by_output_range(tmp_path) -> None:
    path = tmp_path / "results.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_FIELDS)
        writer.writeheader()
        for name, low, high in (("Small", 9, 11), ("Large", 5, 14)):
            for scenario, value in (("low", low), ("high", high)):
                row = dict.fromkeys(LOG_FIELDS, "")
                row.update(
                    {
                        "comparison_name": name,
                        "scenario": scenario,
                        "output_name": "Score",
                        "status": "completed",
                        "consistency_status": "ok",
                        "test_output": value,
                        "baseline_output": 10,
                    }
                )
                writer.writerow(row)
    data = tornado_data(path, "Score")
    assert [item["comparison"] for item in data] == ["Large", "Small"]
