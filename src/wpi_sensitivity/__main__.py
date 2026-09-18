from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import ConfigurationError, load_config
from .consistency import calculate_consistency
from .excel.ranges import parse_a1
from .matrix import saaty_bounds


def self_test() -> None:
    assert parse_a1("C5:G9").cell_count == 25
    assert saaty_bounds(1.0) == (0.5, 2.0)
    result = calculate_consistency(((1.0, 2.0), (0.5, 1.0)))
    assert result.consistency_ratio == 0.0
    print("WPI Sensitivity Analyzer self-test passed.")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="WPI Sensitivity Analyzer")
    result.add_argument(
        "--self-test", action="store_true", help="run a dependency-light diagnostic"
    )
    result.add_argument("--config", type=Path, help="preset JSON to load")
    result.add_argument("--validate-config", action="store_true", help="validate --config and exit")
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.self_test:
        self_test()
        return 0
    if arguments.validate_config:
        if arguments.config is None:
            parser().error("--validate-config requires --config")
        try:
            load_config(arguments.config)
        except ConfigurationError as exc:
            print(f"Configuration error: {exc}", file=sys.stderr)
            return 2
        print(f"Configuration is valid: {arguments.config}")
        return 0
    try:
        from .app import run

        return run(arguments.config)
    except ImportError as exc:
        print(f"GUI dependency unavailable: {exc}. Run setup first.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
