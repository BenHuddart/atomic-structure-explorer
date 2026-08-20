from __future__ import annotations

import gzip
import os
import pickle
from pathlib import Path

from .models import CalculationResult


CACHE_FORMAT_VERSION = 3


class ResultCache:
    """Versioned cache for results produced by this application itself."""

    def __init__(self, directory: Path):
        self.directory = directory

    def _path(self, atomic_number: int, backend_key: str = "central-field") -> Path:
        safe_key = "".join(c for c in backend_key.lower() if c.isalnum() or c in "-_")
        return self.directory / f"v{CACHE_FORMAT_VERSION}-{safe_key}-z{atomic_number:03d}.pickle.gz"

    def get(self, atomic_number: int, backend_key: str = "central-field") -> CalculationResult | None:
        path = self._path(atomic_number, backend_key)
        if not path.exists():
            return None
        try:
            with gzip.open(path, "rb") as stream:
                version, result = pickle.load(stream)
            if version != CACHE_FORMAT_VERSION or not isinstance(result, CalculationResult):
                return None
            return result
        except (OSError, EOFError, pickle.PickleError, AttributeError, ValueError):
            return None

    def put(self, result: CalculationResult, backend_key: str | None = None) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        key = backend_key or str(result.diagnostics.get("backend_id", "central-field"))
        target = self._path(result.element.atomic_number, key)
        temporary = target.with_suffix(target.suffix + ".tmp")
        with gzip.open(temporary, "wb", compresslevel=5) as stream:
            pickle.dump((CACHE_FORMAT_VERSION, result), stream, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(temporary, target)
