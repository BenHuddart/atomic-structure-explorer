from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import numpy as np


class TheoryStage(IntEnum):
    CENTRAL_FIELD = 0
    CONFIGURATION = 1
    TERMS = 2
    FINE_STRUCTURE = 3


@dataclass(frozen=True, order=True)
class Subshell:
    n: int
    l: int
    occupation: int

    @property
    def capacity(self) -> int:
        return 2 * (2 * self.l + 1)

    @property
    def label(self) -> str:
        return f"{self.n}{'spdfghik'[self.l]}"


@dataclass(frozen=True)
class ElectronConfiguration:
    subshells: tuple[Subshell, ...]
    source: str = "calculated"

    @property
    def electron_count(self) -> int:
        return sum(s.occupation for s in self.subshells)


@dataclass(frozen=True)
class Element:
    atomic_number: int
    symbol: str
    name: str
    period: int
    group: int | None
    display_row: int
    display_column: int


@dataclass(frozen=True)
class TraceEvent:
    stage: TheoryStage
    title: str
    explanation: str
    equation: str | None = None
    values: dict[str, str] = field(default_factory=dict)
    interpretation: str | None = None
    kind: str = "derivation"


@dataclass(frozen=True)
class OrbitalResult:
    n: int
    l: int
    occupation: int
    energy_hartree: float
    radius_bohr: np.ndarray
    radial_u: np.ndarray

    @property
    def label(self) -> str:
        return f"{self.n}{'spdfghik'[self.l]}"


@dataclass(frozen=True)
class EnergyLevel:
    configuration: str
    term: str
    j: str
    energy_hartree: float
    stage: TheoryStage
    provenance: str = "calculated"


@dataclass(frozen=True)
class QuantumDefectPoint:
    n: int
    l: int
    binding_hartree: float
    defect: float
    provenance: str = "calculated"


@dataclass(frozen=True)
class CalculationRequest:
    atomic_number: int
    stage: TheoryStage = TheoryStage.FINE_STRUCTURE
    n_max: int = 6
    grid_points: int = 1400
    max_iterations: int = 120
    tolerance: float = 1.0e-7


@dataclass
class CalculationResult:
    request: CalculationRequest
    element: Element
    calculated_configuration: ElectronConfiguration
    accepted_configuration: ElectronConfiguration
    method_name: str
    converged: bool
    iterations: int
    total_orbital_energy_hartree: float
    orbitals: list[OrbitalResult] = field(default_factory=list)
    levels: list[EnergyLevel] = field(default_factory=list)
    quantum_defects: list[QuantumDefectPoint] = field(default_factory=list)
    trace: list[TraceEvent] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
