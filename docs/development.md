# Development guide

Read `vault.md` first. The core is intentionally independent from Qt and xlwings.
Use a fake implementation of `WorkbookAdapter` for safety and execution tests; reserve
the `excel` pytest marker for real desktop-Excel checks.

The canonical verification sequence is documented in `CONTRIBUTING.md`.
