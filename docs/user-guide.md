# User guide

The application follows four stages: configure the workbook, review independent
comparisons, confirm safety/output settings, and inspect results. Validation opens the
selected workbook in an application-owned hidden Excel instance and closes it without
saving. Analysis runs should use the working-copy service described in the README.

Every run directory contains `results.csv`, `metadata.json`, and (when enabled) its
temporary workbook copy. A run is trustworthy only when metadata reports both
`status: completed` and `restoration_verified: true`.
