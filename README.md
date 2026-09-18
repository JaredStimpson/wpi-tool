# WPI Sensitivity Analyzer

A Windows-first desktop tool for measuring how Saaty/AHP pairwise comparisons
affect outputs in an existing Excel Weighted Property Index model. Excel remains
the calculation engine; the application changes one independent comparison at a
time, records the outputs, and restores the model after every test.

## Safety model

- Analysis uses a timestamped working copy by default.
- Only upper-triangle comparisons are varied; the mirrored cell is set to the reciprocal.
- Results are flushed to CSV after every evaluation.
- Pair restoration happens in a `finally` block after every scenario.
- The complete matrix is restored in an outer `finally` block and outputs are checked.
- The source workbook is never saved by the default workflow.

No workbook data, paths, or results are uploaded. There is no telemetry.

## Requirements

- Windows 10/11
- Python 3.12 (64 bit)
- Microsoft Excel desktop

The calculation and plotting tests can run without Excel on other operating systems.

## Install and launch (Windows)

```powershell
.\setup.ps1
.\launch.ps1
```

If local scripts are blocked, use a process-only policy without changing the system policy:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

Development setup on macOS/Linux:

```bash
./setup.sh
./launch.sh
```

Excel-driven runs still require Windows and desktop Excel.

## First run

1. Choose a workbook and worksheet.
2. Enter matrix, row-label, column-label, output-value, and output-label ranges.
3. Validate the setup. The comparison preview is generated from the workbook.
4. Review enabled low/high scenarios.
5. Choose a results directory and run the analysis.
6. Inspect the CSV log, metadata, and tornado chart in the run folder.

Presets are human-readable JSON. See `examples/example_config.json`.

## Command line

```powershell
.\.venv\Scripts\python.exe -m wpi_sensitivity --self-test
.\.venv\Scripts\python.exe -m wpi_sensitivity --config .\example.json --validate-config
```

## Current scope

Version 0.1 provides the tested matrix/range/configuration core, crash-resilient run
logging, Excel working-copy execution, consistency calculations, tornado/radar export,
and a four-stage desktop workflow with background execution and safe cancellation.
Advanced run comparison and Excel report export are
planned. See `vault.md` for the implementation map and extension notes.
