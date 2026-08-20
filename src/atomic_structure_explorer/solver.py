from __future__ import annotations

from collections import defaultdict
from math import pi
from typing import Callable

import numpy as np
from scipy.integrate import cumulative_trapezoid
from scipy.linalg import eigh_tridiagonal

from .models import (
    CalculationRequest,
    CalculationResult,
    ElectronConfiguration,
    OrbitalResult,
    Subshell,
    TheoryStage,
    TraceEvent,
)
from .periodic import (
    ELEMENT_BY_Z,
    accepted_configuration,
    aufbau_configuration,
    format_configuration,
)
from .spectroscopy import build_spectroscopic_levels


ProgressCallback = Callable[[int, float, str], None]


class SphericalSCFSolver:
    """Transparent radial central-field solver.

    Hydrogen is solved in its exact Coulomb field. Multi-electron atoms currently
    use a spherical Hartree field, local Dirac/Slater exchange, and a Latter
    asymptotic correction. This is deliberately identified as HFS rather than
    full nonlocal Hartree-Fock.
    """

    method_name = "Spherical SCF (Hartree-Fock-Slater local exchange)"

    def calculate(
        self,
        request: CalculationRequest,
        progress: ProgressCallback | None = None,
    ) -> CalculationResult:
        element = ELEMENT_BY_Z[request.atomic_number]
        predicted = aufbau_configuration(request.atomic_number)
        accepted = accepted_configuration(request.atomic_number)
        trace = self._opening_trace(element.symbol)
        warnings: list[str] = []

        if request.atomic_number >= 37:
            warnings.append(
                "Relativistic corrections are increasingly important; this "
                "nonrelativistic result should be treated as a model trend."
            )

        r = self._log_grid(request.atomic_number, request.grid_points, request.n_max)
        potential = self._initial_potential(request.atomic_number, r)
        occupied_by_l = self._required_states(predicted)
        competition_event: TraceEvent | None = None

        if request.atomic_number == 1:
            orbitals = self._solve_occupied(r, potential, predicted)
            converged, iterations = True, 1
            total_orbital_energy = sum(o.energy_hartree * o.occupation for o in orbitals)
            trace.append(
                TraceEvent(
                    TheoryStage.CENTRAL_FIELD,
                    "Hydrogenic limit",
                    "With one electron there is no electron-electron field, so the Coulomb central field is exact.",
                    "U(r) = -1/r",
                    {"E(1s)": f"{orbitals[0].energy_hartree:.8f} Ha"},
                    "The numerical result should approach -0.5 Ha.",
                )
            )
        else:
            orbitals, potential, iterations, converged, history = self._iterate_scf(
                request, r, potential, predicted, progress
            )
            promoted = self._configuration_competitor(predicted, orbitals)
            if promoted is not None:
                original = predicted
                pre_promotion_energies = {(orbital.n, orbital.l): orbital.energy_hartree for orbital in orbitals}
                original_occupations = {(shell.n, shell.l): shell.occupation for shell in original.subshells}
                changed = [
                    shell for shell in promoted.subshells
                    if shell.occupation != original_occupations.get((shell.n, shell.l), 0)
                ]
                s_shell = next(shell for shell in changed if shell.l == 0)
                d_shell = next(shell for shell in changed if shell.l == 2)
                competition_gap = pre_promotion_energies[(d_shell.n, 2)] - pre_promotion_energies[(s_shell.n, 0)]
                predicted = promoted
                first_iterations = iterations
                orbitals, potential, extra_iterations, converged, extra_history = self._iterate_scf(
                    request, r, potential, predicted, progress
                )
                iterations = first_iterations + extra_iterations
                history.extend(extra_history)
                competition_event = TraceEvent(
                        TheoryStage.CONFIGURATION,
                        "Test competing s and d occupations",
                        "The ns and (n−1)d subshells are close enough that the Madelung order is not decisive. Transfer one ns electron when the calculated d orbital lies lower and the transfer produces a half-filled or filled d subshell.",
                        "ns² (n−1)d^(q) → ns¹ (n−1)d^(q+1),  q+1 = 5 or 10",
                        {
                            "Madelung candidate": format_configuration(original),
                            "selected candidate": format_configuration(predicted),
                            "εd − εs": f"{competition_gap:.6f} Ha",
                        },
                        "This is a transparent shell-stability model, not an experimental configuration lookup.",
                    )
            # The Latter tail is imposed after the occupied-shell fixed point;
            # including its switching boundary in every update causes d-block
            # atoms to oscillate. It is needed for neutral Rydberg series, not
            # for determining compact occupied orbitals.
            potential = self._apply_latter_tail(potential, r)
            total_orbital_energy = sum(o.energy_hartree * o.occupation for o in orbitals)
            trace.extend(self._scf_trace(iterations, converged, history, potential, r))
            if competition_event is not None:
                trace.append(competition_event)
            if not converged:
                warnings.append("The SCF convergence threshold was not reached; inspect the numerical trace.")

        calculated_text = format_configuration(predicted)
        accepted_text = format_configuration(accepted)
        trace.append(
            TraceEvent(
                TheoryStage.CONFIGURATION,
                "Fill the central-field orbitals",
                "Apply the Pauli principle and the least-energy filling rule to the calculated orbital sequence.",
                "configuration = product of occupied nl subshells",
                {"calculated": calculated_text, "accepted": accepted_text},
                "Disagreement is retained as evidence of the model's limitations.",
            )
        )

        levels, defects, level_trace, level_warnings, diagnostics = build_spectroscopic_levels(
            element=element,
            configuration=predicted,
            r=r,
            potential=potential,
            solve_states=lambda l, count: self._solve_l(r, potential, l, count),
            n_max=request.n_max,
        )
        trace.extend(level_trace)
        warnings.extend(level_warnings)
        diagnostics.update(
            {
                "radius_bohr": r,
                "central_potential_hartree": potential,
                "calculated_configuration": calculated_text,
                "accepted_configuration": accepted_text,
                "required_states_by_l": dict(occupied_by_l),
                "configuration_selection": (
                    "s-d half/full-shell competition" if competition_event is not None else "Madelung"
                ),
            }
        )
        if predicted.subshells != accepted.subshells:
            warnings.append(
                f"Calculated configuration {calculated_text} differs from accepted {accepted_text}."
            )

        return CalculationResult(
            request=request,
            element=element,
            calculated_configuration=predicted,
            accepted_configuration=accepted,
            method_name="Exact Coulomb central field" if request.atomic_number == 1 else self.method_name,
            converged=converged,
            iterations=iterations,
            total_orbital_energy_hartree=total_orbital_energy,
            orbitals=orbitals,
            levels=levels,
            quantum_defects=defects,
            trace=trace,
            warnings=warnings,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _opening_trace(symbol: str) -> list[TraceEvent]:
        return [
            TraceEvent(
                TheoryStage.CENTRAL_FIELD,
                "Partition the Hamiltonian",
                f"For {symbol}, place the spherical mean interaction in H0 and reserve smaller interactions for H1 and H2.",
                "H = H0 + H1 + H2",
                interpretation="H0 gives configurations, H1 gives terms, and H2 gives fine-structure levels.",
            ),
            TraceEvent(
                TheoryStage.CENTRAL_FIELD,
                "Choose the central-field basis",
                "Spherical symmetry separates every orbital into a radial function, a spherical harmonic, and spin.",
                "ψ_nlmlms = P_nl(r) Y_lml(θ,φ) χ_ms / r",
            ),
        ]

    @staticmethod
    def _log_grid(z: int, points: int, n_max: int) -> np.ndarray:
        # The inner radius resolves the Coulomb cusp; the outer radius resolves
        # the requested Rydberg orbitals. End points are excluded as Dirichlet boundaries.
        r_min = min(1.0e-5, 1.0e-4 / max(z, 1))
        r_max = max(80.0, 4.0 * n_max * n_max)
        x = np.linspace(np.log(r_min), np.log(r_max), points + 2)
        return np.exp(x[1:-1])

    @staticmethod
    def _initial_potential(z: int, r: np.ndarray) -> np.ndarray:
        if z == 1:
            return -1.0 / r
        core_radius = 0.65 / (z ** (1.0 / 3.0))
        screening = (z - 1.0) * (1.0 - np.exp(-r / core_radius)) / r
        return -z / r + screening

    @staticmethod
    def _required_states(configuration) -> dict[int, int]:
        required: dict[int, int] = defaultdict(int)
        for shell in configuration.subshells:
            required[shell.l] = max(required[shell.l], shell.n - shell.l)
        return required

    def _solve_l(
        self, r: np.ndarray, potential: np.ndarray, l: int, count: int
    ) -> tuple[np.ndarray, np.ndarray]:
        if count <= 0:
            return np.empty(0), np.empty((len(r), 0))
        x = np.log(r)
        dx = float(x[1] - x[0])
        a_diag = (
            np.full_like(r, 1.0 / dx**2 + 0.125 + 0.5 * l * (l + 1))
            + r * r * potential
        )
        a_off = np.full(len(r) - 1, -0.5 / dx**2)
        diag = a_diag / (r * r)
        off = a_off / (r[:-1] * r[1:])
        energies, z_vectors = eigh_tridiagonal(
            diag,
            off,
            select="i",
            select_range=(0, count - 1),
            check_finite=False,
            lapack_driver="stebz",
        )
        if z_vectors.ndim == 1:
            z_vectors = z_vectors[:, None]
        radial = z_vectors / np.sqrt(r[:, None])
        for index in range(radial.shape[1]):
            norm = np.sqrt(np.trapezoid(radial[:, index] ** 2, r))
            radial[:, index] /= norm
            if radial[np.argmax(np.abs(radial[:, index])), index] < 0:
                radial[:, index] *= -1
        return energies, radial

    def _solve_occupied(self, r, potential, configuration) -> list[OrbitalResult]:
        required = self._required_states(configuration)
        solutions: dict[int, tuple[np.ndarray, np.ndarray]] = {
            l: self._solve_l(r, potential, l, count) for l, count in required.items()
        }
        orbitals: list[OrbitalResult] = []
        for shell in configuration.subshells:
            radial_index = shell.n - shell.l - 1
            energies, radial = solutions[shell.l]
            orbitals.append(
                OrbitalResult(
                    shell.n,
                    shell.l,
                    shell.occupation,
                    float(energies[radial_index]),
                    r.copy(),
                    radial[:, radial_index].copy(),
                )
            )
        return orbitals

    @staticmethod
    def _density(orbitals: list[OrbitalResult], r: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        radial_charge = np.zeros_like(r)
        for orbital in orbitals:
            radial_charge += orbital.occupation * orbital.radial_u**2
        density = radial_charge / (4.0 * pi * r * r)
        return radial_charge, density

    @staticmethod
    def _build_potential(z: int, r: np.ndarray, radial_charge: np.ndarray, density: np.ndarray) -> np.ndarray:
        inner_charge = cumulative_trapezoid(radial_charge, r, initial=0.0)
        integrand = radial_charge / r
        cumulative_outer = cumulative_trapezoid(integrand, r, initial=0.0)
        outer = cumulative_outer[-1] - cumulative_outer
        hartree = inner_charge / r + outer
        exchange = -np.cbrt(3.0 * np.maximum(density, 0.0) / pi)
        return -z / r + hartree + exchange

    @staticmethod
    def _apply_latter_tail(potential: np.ndarray, r: np.ndarray) -> np.ndarray:
        """Restore the neutral atom's -1/r Rydberg tail after occupied SCF."""

        return np.minimum(potential, -1.0 / r)

    @staticmethod
    def _configuration_competitor(
        configuration: ElectronConfiguration, orbitals: list[OrbitalResult]
    ) -> ElectronConfiguration | None:
        """Propose the elementary d4/d9 -> d5/d10, s2 -> s1 competition.

        The condition combines an SCF result (d below s) with the model-level
        half/full-subshell stability argument. It is deliberately general in n
        and does not identify particular elements.
        """

        energies = {(orbital.n, orbital.l): orbital.energy_hartree for orbital in orbitals}
        shells = list(configuration.subshells)
        for s_index, s_shell in enumerate(shells):
            if s_shell.l != 0 or s_shell.occupation != 2:
                continue
            d_key = (s_shell.n - 1, 2)
            d_index = next(
                (index for index, shell in enumerate(shells) if (shell.n, shell.l) == d_key),
                None,
            )
            if d_index is None or shells[d_index].occupation not in {4, 9}:
                continue
            if energies.get(d_key, float("inf")) >= energies.get((s_shell.n, 0), -float("inf")):
                continue
            d_shell = shells[d_index]
            shells[s_index] = Subshell(s_shell.n, 0, 1)
            shells[d_index] = Subshell(d_shell.n, 2, d_shell.occupation + 1)
            return ElectronConfiguration(tuple(shells), "central-field shell competition")
        return None

    def _iterate_scf(self, request, r, potential, configuration, progress):
        mixing = 0.24
        history: list[float] = []
        previous_energy: float | None = None
        orbitals: list[OrbitalResult] = []
        converged = False
        for iteration in range(1, request.max_iterations + 1):
            orbitals = self._solve_occupied(r, potential, configuration)
            energy_sum = sum(o.energy_hartree * o.occupation for o in orbitals)
            radial_charge, density = self._density(orbitals, r)
            target = self._build_potential(request.atomic_number, r, radial_charge, density)
            if previous_energy is None:
                delta = float("inf")
            else:
                delta = abs(energy_sum - previous_energy)
            history.append(delta)
            if progress:
                progress(iteration, delta, f"Solving {configuration.electron_count}-electron central field")
            if previous_energy is not None and delta < request.tolerance:
                converged = True
                potential = target
                break
            # Reduce the update when an iteration moves uphill sharply.
            local_mix = mixing if len(history) < 3 or delta <= history[-2] * 1.5 else mixing * 0.45
            potential = (1.0 - local_mix) * potential + local_mix * target
            previous_energy = energy_sum
        # Re-solve in the final potential so returned orbital energies and field agree.
        orbitals = self._solve_occupied(r, potential, configuration)
        return orbitals, potential, iteration, converged, history

    @staticmethod
    def _scf_trace(iterations, converged, history, potential, r):
        finite = [value for value in history if np.isfinite(value)]
        final_delta = finite[-1] if finite else float("nan")
        return [
            TraceEvent(
                TheoryStage.CENTRAL_FIELD,
                "Iterate to self-consistency",
                "Solve the radial equations, rebuild the spherical electron field, mix it with the previous field, and repeat.",
                "U^(k+1) = (1-α) U^(k) + α U[density^(k)]",
                {
                    "iterations": str(iterations),
                    "final ΔΣocc ε": f"{final_delta:.3e} Ha",
                    "status": "converged" if converged else "not converged",
                },
                "The converged orbitals define the zero-order basis used by later perturbations.",
                kind="numerical",
            ),
            TraceEvent(
                TheoryStage.CENTRAL_FIELD,
                "Check the central-field limits",
                "Inspect the short- and long-range potential rather than treating convergence alone as proof of a physical result.",
                "U(r→0) ≈ -Z/r;  U(r→∞) ≈ -1/r",
                {
                    "r_min U(r_min)": f"{r[0] * potential[0]:.4f}",
                    "r_max U(r_max)": f"{r[-1] * potential[-1]:.4f}",
                },
            ),
        ]
