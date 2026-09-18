# Contributing

Use Python 3.12 and the repository-local `.venv`. Before committing, run:

```powershell
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pytest
```

Keep Excel integration behind the `WorkbookAdapter` protocol so unit tests remain
portable. Any write to Excel must have a matching restoration path exercised by a test.
Update `vault.md` whenever a feature, invariant, schema, or extension point changes.
