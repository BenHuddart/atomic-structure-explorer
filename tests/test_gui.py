from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QIcon, QMouseEvent
from PySide6.QtWidgets import QPushButton

import atomic_structure_explorer.app as application
from atomic_structure_explorer.gui.main_window import MainWindow
from atomic_structure_explorer.models import CalculationRequest, TheoryStage
from atomic_structure_explorer.solver import SphericalSCFSolver


def test_packaged_application_icon_is_loadable(qapp):
    icon_path = Path(application.__file__).with_name("assets") / "app-icon.png"
    assert icon_path.is_file()
    assert not QIcon(str(icon_path)).isNull()


def test_main_window_contains_full_periodic_table(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    element_buttons = [
        button for button in window.table_page.findChildren(QPushButton) if button.objectName() == "element"
    ]
    assert window.windowTitle() == "Atomic Structure Explorer"
    assert len(element_buttons) == 118


def test_workspace_stage_navigation_updates_diagram(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    result = SphericalSCFSolver().calculate(CalculationRequest(1, grid_points=500, n_max=4))
    window.workspace.element = result.element
    window.workspace._apply_result(result)
    window.workspace.stage_buttons[3].click()
    assert window.workspace.diagram._stage == TheoryStage.FINE_STRUCTURE
    assert "Fine-structure" in window.workspace.diagram_title.text()
    assert "spin-orbit" in window.workspace.learn_label.text().lower()


def test_terms_view_contains_singlet_and_triplet_centres(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    magnesium = SphericalSCFSolver().calculate(CalculationRequest(12, grid_points=500, n_max=4))
    window.workspace.element = magnesium.element
    window.workspace._apply_result(magnesium)
    window.workspace.stage_buttons[2].click()
    labels = [mark[2] for mark in window.workspace.diagram._marks_for_stage(magnesium)]
    assert any("¹P" in label for label in labels)
    assert any("³P" in label for label in labels)


def test_quantum_defect_tab_is_explicitly_alkali_only(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    magnesium = SphericalSCFSolver().calculate(CalculationRequest(12, grid_points=500, n_max=4))
    window.workspace.element = magnesium.element
    window.workspace._apply_result(magnesium)
    assert window.workspace.defect_stack.currentWidget() is window.workspace.defect_unavailable
    assert "alkalis only" in window.workspace.lower_tabs.tabText(window.workspace.defect_tab_index).lower()

    sodium = SphericalSCFSolver().calculate(CalculationRequest(11, grid_points=500, n_max=4))
    window.workspace.element = sodium.element
    window.workspace._apply_result(sodium)
    assert window.workspace.defect_stack.currentWidget() is window.workspace.defect_table
    assert window.workspace.defect_table.rowCount() > 0


def test_radial_curve_identifies_orbital_on_hover(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    hydrogen = SphericalSCFSolver().calculate(CalculationRequest(1, grid_points=500, n_max=4))
    plot = window.workspace.radial_plot
    plot.resize(600, 260)
    plot.set_result(hydrogen)
    plot.show()
    qtbot.waitExposed(plot)
    plot.grab()  # populate screen-space curve geometry
    orbital, points, _ = plot._curve_geometry[0]
    point = points[points[:, 1].argmin()]
    local = QPointF(float(point[0]), float(point[1]))
    event = QMouseEvent(
        QEvent.Type.MouseMove,
        local,
        plot.mapToGlobal(local.toPoint()),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    plot.mouseMoveEvent(event)
    assert plot._hovered_label == orbital.label
