# Project vault

This is the durable engineering memory for the repository. Read this file first when
adding or changing a feature; update it in the same commit. It records what exists and
why, while the tests remain the executable source of truth.

## Product state (0.1.0)

Implemented:

- JSON preset schema v1 with explicit rejection of unknown versions.
- Excel A1 range parser with quoted worksheet support and cell iteration.
- Positive square reciprocal-matrix validation with address-specific errors.
- Saaty fraction parsing/display and adjacent or multi-step scenario generation.
- AHP consistency index/ratio calculation using the principal eigenvalue power method.
- Immutable run planning containing baseline/low/high values and Excel addresses.
- Workbook adapter boundary plus an xlwings implementation for desktop Excel.
- Default timestamped working-copy workflow; the source workbook is not opened for edits.
- Immediate append-and-flush CSV logging and atomic metadata JSON replacement.
- Nested restoration guarantees: the changed pair after each evaluation and the whole
  matrix at run shutdown, including cancellation and ordinary exceptions.
- Restoration verification against baseline outputs and a hard failure state if it fails.
- Tornado and radar plotting functions that work without the GUI.
- Four-stage PySide6 application with configuration fields, validation, comparison table,
  workload/safety summary, background execution, safe cancellation, results page,
  preset load/save, and keyboard shortcuts.
- Cross-platform unit tests that use an in-memory workbook adapter rather than Excel.

Not yet implemented:

- Live Excel-selection buttons and attachment to a user-owned Excel instance.
- Pause/resume, automatic reconnect after an Excel crash, and prior-run comparison.
- Excel-formatted report export and packaged/signed Windows distribution.
- Formula/value/number-format snapshot parity for arbitrary cells outside the matrix.

## Architecture map

- `config.py`: schema-v1 dataclasses, path resolution, and JSON load/save.
- `excel/ranges.py`: strict A1 parsing only; no workbook automation.
- `matrix.py`: domain validation, Saaty values, comparisons, and scenario bounds.
- `consistency.py`: RI table and CI/CR. RI values use Saaty's published conventional table.
- `models.py`: frozen run-plan and result records shared across layers.
- `excel/connection.py`: `WorkbookAdapter` protocol and optional `XlwingsWorkbook`.
- `excel/restoration.py`: tolerant scalar/output comparison helpers.
- `sensitivity.py`: run-plan construction and restoration-safe execution service.
- `logging_service.py`: one-row-per-output CSV and atomic run metadata.
- `plotting.py`: post-processing; it never writes to a workbook.
- `gui/main_window.py`: presentation/orchestration only; domain rules stay outside Qt.

Dependency direction: GUI -> services -> domain/protocols. Domain modules must never
import PySide6, xlwings, pandas, or matplotlib.

## Non-negotiable invariants

1. Upper-triangle cells are authoritative and lower-triangle cells are reciprocals.
2. A recalculation never occurs between writing the authoritative and reciprocal values.
3. Scenario restoration is in `finally`; whole-matrix restoration is in an outer `finally`.
4. Default execution operates on a copied workbook and never saves the source.
5. Formula errors, blanks, text, and numeric zero remain distinguishable in logs.
6. Completed log rows are flushed before the next Excel mutation.
7. Unknown config schema versions fail loudly with a migration-oriented message.
8. New Excel behavior is first exercised against a fake `WorkbookAdapter` unit test.

## Extension recipe

When adding a feature: identify its owner above; add/adjust a narrow public API; write a
portable unit test first; keep Excel-specific calls inside `excel/`; update the GUI only
after the service is usable headlessly; then update Product state and any changed invariant
here. Avoid duplicating workbook state in widgets—`AnalysisConfig` and `RunPlan` are the
handoff objects.

## Key decisions

- Dataclasses plus explicit validation were chosen over runtime model frameworks to keep
  configuration usable even before optional dependencies are installed.
- A workbook protocol makes safety logic testable without COM or a licensed Excel install.
- CSV is the canonical append-only recovery log. Richer reports should be derived from it.
- Matrix restoration captures formulas when available; writing a formula back is preferred
  over writing its last calculated value.
- The synchronous runner accepts progress/cancellation callbacks. The Qt worker wraps it,
  keeping event-loop logic out of the runner.

## Change log discipline

For every material change, update the version/date if appropriate, the Product state list,
the Architecture map when ownership moves, and Key decisions when a tradeoff is introduced.
Do not turn this file into a task diary or paste large code excerpts into it.
