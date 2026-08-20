from atomic_structure_explorer.cache import ResultCache
from atomic_structure_explorer.models import CalculationRequest
from atomic_structure_explorer.solver import SphericalSCFSolver


def test_result_cache_round_trip(tmp_path):
    result = SphericalSCFSolver().calculate(CalculationRequest(1, grid_points=500, n_max=4))
    cache = ResultCache(tmp_path)
    assert cache.get(1) is None
    cache.put(result)
    restored = cache.get(1)
    assert restored is not None
    assert restored.element.symbol == "H"
    assert restored.orbitals[0].energy_hartree == result.orbitals[0].energy_hartree
