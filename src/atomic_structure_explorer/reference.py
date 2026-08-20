from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any


@dataclass(frozen=True)
class ReferenceDataset:
    dataset_id: str
    title: str
    version: str
    source: str
    licence: str
    redistribution_verified: bool
    records: tuple[dict[str, Any], ...]


class ReferenceRepository:
    """Read-only registry which refuses unverified bundled datasets."""

    def __init__(self):
        manifest_path = files("atomic_structure_explorer.data").joinpath("reference_manifest.json")
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def datasets(self) -> tuple[ReferenceDataset, ...]:
        result = []
        for raw in self.manifest.get("datasets", []):
            if not raw.get("redistribution_verified", False):
                continue
            result.append(
                ReferenceDataset(
                    dataset_id=raw["id"],
                    title=raw["title"],
                    version=raw["version"],
                    source=raw["source"],
                    licence=raw["licence"],
                    redistribution_verified=True,
                    records=tuple(raw.get("records", [])),
                )
            )
        return tuple(result)
