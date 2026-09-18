# Workbook requirements

- The matrix must be a square, contiguous range of positive numeric cells.
- Diagonal cells equal 1; mirrored cells multiply to 1 within the configured tolerance.
- Row and column labels are contiguous ranges with identical text in identical order.
- Output labels and output values contain the same number of cells.
- Matrix and output ranges must not overlap.
- Sheets must not use merged cells inside configured ranges and must permit writes to the matrix.
- External links should be available before analysis. The app opens working copies with link updates disabled.

Macro-enabled `.xlsm` files can be analyzed, but the default working copy is closed without saving and the original is never opened for mutation.
