import numpy as np

from atomic_structure_explorer.models import CalculationRequest, TheoryStage
from atomic_structure_explorer.solver import SphericalSCFSolver


def calculate(z: int, n_max: int = 5):
    return SphericalSCFSolver().calculate(
        CalculationRequest(z, n_max=n_max, grid_points=800, max_iterations=65, tolerance=2e-6)
    )


def test_hydrogen_ground_energy_and_quantum_defect():
    result = calculate(1)
    assert result.converged
    assert abs(result.orbitals[0].energy_hartree + 0.5) < 3e-3
    # Higher Rydberg states need a denser/larger box than this fast test grid.
    low_series = [point for point in result.quantum_defects if point.l <= 2 and point.n <= 3]
    assert low_series
    assert max(abs(point.defect) for point in low_series) < 0.12


def test_radial_orbitals_are_normalized_and_have_expected_nodes():
    result = calculate(11)
    for orbital in result.orbitals:
        assert abs(np.trapezoid(orbital.radial_u**2, orbital.radius_bohr) - 1.0) < 2e-6
    orbital_3s = next(orbital for orbital in result.orbitals if orbital.label == "3s")
    significant = np.abs(orbital_3s.radial_u) > np.max(np.abs(orbital_3s.radial_u)) * 1e-5
    signs = np.sign(orbital_3s.radial_u[significant])
    nodes = np.count_nonzero(signs[1:] * signs[:-1] < 0)
    assert nodes == 2


def test_sodium_reproduces_expected_quantum_defect_ordering():
    result = calculate(11)
    assert result.converged
    first = {}
    for point in result.quantum_defects:
        first.setdefault(point.l, point.defect)
    assert first[0] > first[1] > first[2]
    assert abs(first[0] - 1.34) < 0.18
    assert abs(first[1] - 0.88) < 0.18
    assert abs(first[2]) < 0.12


def test_magnesium_term_centre_and_lande_interval():
    result = calculate(12)
    assert result.diagnostics["ls_coupling"] == "supported"
    singlet = next(level for level in result.levels if level.term == "¹P")
    triplets = sorted((level for level in result.levels if level.term == "³P"), key=lambda level: int(level.j))
    assert singlet.energy_hartree > max(level.energy_hartree for level in triplets)
    intervals = np.diff([level.energy_hartree for level in triplets])
    np.testing.assert_allclose(intervals[1] / intervals[0], 2.0, rtol=2e-4)
    weights = np.array([1, 3, 5])
    centre = np.average([level.energy_hartree for level in triplets], weights=weights)
    assert np.isfinite(centre)


def test_trace_mirrors_atomic_structure_hierarchy():
    result = calculate(11)
    stages = {event.stage for event in result.trace}
    assert TheoryStage.CENTRAL_FIELD in stages
    assert TheoryStage.CONFIGURATION in stages
    assert TheoryStage.TERMS in stages
    assert TheoryStage.FINE_STRUCTURE in stages


def test_unsupported_valence_space_stops_at_boundary():
    result = calculate(26)
    assert result.levels == []
    assert any("limited" in warning for warning in result.warnings)


def test_copper_converges_and_predicts_filled_d_shell_competitor():
    result = SphericalSCFSolver().calculate(
        CalculationRequest(29, n_max=5, grid_points=700, max_iterations=120, tolerance=1e-7)
    )
    occupations = {(shell.n, shell.l): shell.occupation for shell in result.calculated_configuration.subshells}
    assert result.converged
    assert occupations[(3, 2)] == 10
    assert occupations[(4, 0)] == 1
    assert result.calculated_configuration.subshells == result.accepted_configuration.subshells
    assert result.diagnostics["configuration_selection"] == "s-d half/full-shell competition"


def test_chromium_predicts_half_filled_d_shell_competitor():
    result = SphericalSCFSolver().calculate(
        CalculationRequest(24, n_max=5, grid_points=700, max_iterations=120, tolerance=1e-7)
    )
    occupations = {(shell.n, shell.l): shell.occupation for shell in result.calculated_configuration.subshells}
    assert result.converged
    assert occupations[(3, 2)] == 5
    assert occupations[(4, 0)] == 1


def test_solver_does_not_advertise_hidden_controls():
    result = calculate(20)
    assert all("Compare both" not in warning for warning in result.warnings)
