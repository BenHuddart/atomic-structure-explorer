# Contributing

Thank you for improving Atomic Structure Explorer.

## Development setup

Create a Python 3.11 or newer virtual environment, then install the project in editable mode:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## Expectations

- Keep the application usable offline.
- Do not add private teaching materials, student data, credentials, or datasets without verified redistribution rights.
- Distinguish calculated results from accepted or experimental values.
- Explain approximation limits in the interface when they affect interpretation.
- Add or update tests for numerical and GUI behaviour.
- Regenerate documentation screenshots when a visible interface change makes them stale.

Before opening a pull request, run the complete test suite and review the diff for generated files, caches, local paths, and sensitive information.
