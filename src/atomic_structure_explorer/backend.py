from __future__ import annotations

from .solver import SphericalSCFSolver


class CentralFieldBackend(SphericalSCFSolver):
    backend_id = "central-field"

    def calculate(self, request, progress=None):
        result = super().calculate(request, progress)
        result.diagnostics["backend_id"] = self.backend_id
        return result
