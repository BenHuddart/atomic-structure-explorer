from __future__ import annotations

from math import sqrt
from typing import Callable

import numpy as np
from scipy.integrate import cumulative_trapezoid

from .models import (
    ElectronConfiguration,
    Element,
    EnergyLevel,
    QuantumDefectPoint,
    TheoryStage,
    TraceEvent,
)


ALPHA = 7.2973525643e-3
L_LETTERS = "SPDFGHIK"


def _radial_exchange(a: np.ndarray, b: np.ndarray, r: np.ndarray, k: int) -> float:
    product = a * b
    lower = cumulative_trapezoid(product * r**k, r, initial=0.0)
    upper_integrand = product / r ** (k + 1)
    upper_cumulative = cumulative_trapezoid(upper_integrand, r, initial=0.0)
    upper = upper_cumulative[-1] - upper_cumulative
    kernel_action = lower / r ** (k + 1) + r**k * upper
    return float(np.trapezoid(product * kernel_action, r))


def _spin_orbit_zeta(u: np.ndarray, r: np.ndarray, potential: np.ndarray) -> float:
    derivative = np.gradient(potential, r, edge_order=2)
    integrand = u * u * derivative / r
    return float(0.5 * ALPHA**2 * np.trapezoid(integrand, r))


def _series_states(solve_states, l: int, n_max: int):
    count = max(1, n_max - l)
    energies, radial = solve_states(l, count)
    return [(l + 1 + index, float(energy), radial[:, index]) for index, energy in enumerate(energies)]


def build_spectroscopic_levels(
    *,
    element: Element,
    configuration: ElectronConfiguration,
    r: np.ndarray,
    potential: np.ndarray,
    solve_states: Callable[[int, int], tuple[np.ndarray, np.ndarray]],
    n_max: int,
):
    levels: list[EnergyLevel] = []
    defects: list[QuantumDefectPoint] = []
    trace: list[TraceEvent] = []
    warnings: list[str] = []
    diagnostics: dict[str, object] = {}

    if element.group == 1 or element.atomic_number == 1:
        for l in range(0, min(3, n_max - 1) + 1):
            for n, energy, u in _series_states(solve_states, l, n_max):
                if energy >= 0.0:
                    continue
                # Ignore orbitals occupied wholly in the closed core; start at
                # the first orbital at or above the neutral valence n.
                valence_n = max(s.n for s in configuration.subshells)
                if n < valence_n:
                    continue
                term = f"²{L_LETTERS[l]}"
                if l == 0:
                    levels.append(EnergyLevel(f"{n}s", term, "1/2", energy, TheoryStage.FINE_STRUCTURE))
                else:
                    zeta = _spin_orbit_zeta(u, r, potential)
                    for j, angular in ((l - 0.5, -(l + 1) / 2.0), (l + 0.5, l / 2.0)):
                        j_text = f"{int(2*j)}/2"
                        levels.append(
                            EnergyLevel(f"{n}{'spdf'[l]}", term, j_text, energy + zeta * angular, TheoryStage.FINE_STRUCTURE)
                        )
                binding = -energy
                defect = n - sqrt(0.5 / binding)
                defects.append(QuantumDefectPoint(n, l, binding, defect))
        trace.extend(
            [
                TraceEvent(
                    TheoryStage.TERMS,
                    "Identify one-electron terms",
                    "A single valence electron has L=l and S=1/2, giving one doublet term for each nl configuration.",
                    "nl → ²L",
                ),
                TraceEvent(
                    TheoryStage.FINE_STRUCTURE,
                    "Resolve the spin-orbit doublet",
                    "For l>0, couple l and s to obtain j=l±1/2 and evaluate the radial spin-orbit integral.",
                    "ΔE_j = ζ_nl [j(j+1)-l(l+1)-s(s+1)] / 2",
                    interpretation="The degeneracy-weighted centre of gravity is unchanged.",
                ),
                TraceEvent(
                    TheoryStage.CENTRAL_FIELD,
                    "Calculate the quantum defect",
                    "Compare each calculated binding energy with the hydrogenic Rydberg formula.",
                    "δ_l(n) = n - √(R∞/T_nl)",
                    interpretation="A meaningful series should be nearly independent of n and decrease with increasing l.",
                ),
            ]
        )
        diagnostics["ls_coupling"] = "single valence electron"
        return levels, defects, trace, warnings, diagnostics

    if element.group == 2 and element.atomic_number != 2:
        outer_n = max(s.n for s in configuration.subshells)
        s_energies, s_radial = solve_states(0, outer_n + 1)
        p_energies, p_radial = solve_states(1, outer_n)
        spectator = s_radial[:, outer_n - 1]
        excited_p = p_radial[:, outer_n - 2]
        gross = float(s_energies[outer_n - 1] + p_energies[outer_n - 2])
        exchange = _radial_exchange(spectator, excited_p, r, 1) / 3.0
        zeta = _spin_orbit_zeta(excited_p, r, potential)
        singlet_shift = 1.5 * exchange
        triplet_centre = -0.5 * exchange
        levels.append(EnergyLevel(f"{outer_n}s{outer_n}p", "¹P", "1", gross + singlet_shift, TheoryStage.TERMS))
        a_constant = 0.5 * zeta
        for j, factor in ((0, -2.0), (1, -1.0), (2, 1.0)):
            levels.append(
                EnergyLevel(
                    f"{outer_n}s{outer_n}p",
                    "³P",
                    str(j),
                    gross + triplet_centre + a_constant * factor,
                    TheoryStage.FINE_STRUCTURE,
                )
            )
        separation = max(2.0 * exchange, 1e-15)
        eta = abs(2.0 * a_constant) / separation
        diagnostics.update({"exchange_K_hartree": exchange, "spin_orbit_zeta_hartree": zeta, "ls_eta": eta})
        if eta <= 0.1:
            ls_status = "supported"
        elif eta <= 0.3:
            ls_status = "borderline"
            warnings.append("LS coupling is borderline because fine structure is no longer very small compared with term separation.")
        else:
            ls_status = "unsupported"
            warnings.append("LS coupling is unsupported by the interaction-scale diagnostic; fine structure is illustrative only.")
        diagnostics["ls_coupling"] = ls_status
        trace.extend(
            [
                TraceEvent(
                    TheoryStage.TERMS,
                    "Evaluate residual electrostatic interaction",
                    "Direct interaction shifts the configuration average; exchange separates the singlet and triplet terms.",
                    "E(¹P)-E(³P) = 2K",
                    {"K": f"{exchange:.6e} Ha", "separation": f"{2*exchange:.6e} Ha"},
                    "The degeneracy-weighted term centre remains at the configuration-average energy.",
                ),
                TraceEvent(
                    TheoryStage.FINE_STRUCTURE,
                    "Test LS coupling before resolving J",
                    "Compare the spin-orbit scale with the residual-electrostatic term separation.",
                    "η = max fine-structure interval / term separation",
                    {"η": f"{eta:.4f}", "classification": ls_status},
                    "LS coupling is an approximation with a scale-dependent domain of validity.",
                ),
            ]
        )
        return levels, defects, trace, warnings, diagnostics

    warnings.append(
        "Detailed term and fine-structure calculations are currently limited to the implemented one- and two-valence model families."
    )
    diagnostics["ls_coupling"] = "not evaluated"
    trace.append(
        TraceEvent(
            TheoryStage.TERMS,
            "Stop at the supported theory boundary",
            "The central-field orbitals and configuration remain available, but this valence space requires broader angular algebra and configuration interaction.",
            interpretation="No term labels are preferable to unjustified term labels.",
            kind="warning",
        )
    )
    return levels, defects, trace, warnings, diagnostics
