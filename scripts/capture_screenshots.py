"""Generate deterministic application screenshots for documentation and CI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))


def _save_window(window, destination: Path) -> None:
    from PySide6.QtWidgets import QApplication

    window.show()
    QApplication.processEvents()
    pixmap = window.grab()
    if pixmap.isNull() or not pixmap.save(str(destination), "PNG"):
        raise RuntimeError(f"Could not save screenshot to {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/screenshots"),
        help="Directory for generated PNG files (default: docs/screenshots)",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    from atomic_structure_explorer.gui.main_window import MainWindow
    from atomic_structure_explorer.models import CalculationRequest, TheoryStage
    from atomic_structure_explorer.solver import SphericalSCFSolver

    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Atomic Structure Explorer Screenshot Generator")
    app.setFont(QFont("Arial", 10))

    window = MainWindow()
    window.resize(1440, 900)
    _save_window(window, args.output_dir / "periodic-table.png")

    result = SphericalSCFSolver().calculate(
        CalculationRequest(11, grid_points=900, n_max=6, max_iterations=120)
    )
    window.workspace.element = result.element
    window.workspace.identity.setText(
        f"{result.element.symbol}   {result.element.name}   ·   Z = {result.element.atomic_number}"
    )
    window.workspace._apply_result(result)
    window.stack.setCurrentWidget(window.workspace)
    window.workspace.stage_buttons[TheoryStage.FINE_STRUCTURE].click()
    _save_window(window, args.output_dir / "sodium-fine-structure.png")

    window.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
