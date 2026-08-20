from __future__ import annotations

import html
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QStandardPaths, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models import CalculationRequest, CalculationResult, Element, TheoryStage
from ..cache import ResultCache
from ..periodic import ELEMENTS, format_configuration
from ..backend import CentralFieldBackend
from .widgets import EnergyDiagramWidget, RadialPlotWidget


APP_STYLE = """
QMainWindow, QWidget { font-size: 13px; }
QMainWindow { background: #f4f6fa; }
QFrame#header { background: #172b4d; color: white; }
QLabel#brand { color: white; font-size: 17px; font-weight: 600; }
QPushButton#nav { background: transparent; color: white; border: 1px solid #70819b; border-radius: 6px; padding: 7px 11px; }
QPushButton#nav:hover { background: #243c62; }
QPushButton#element { border: 1px solid #c5cfdd; border-radius: 6px; background: white; padding: 3px; min-width: 42px; min-height: 42px; }
QPushButton#element:hover { border: 2px solid #2f6fed; background: #edf3ff; }
QPushButton#element[family="one"] { background: #e2edff; }
QPushButton#element[family="two"] { background: #e4f5ea; }
QPushButton#stage { text-align: left; border: 1px solid #c5cfdd; border-radius: 7px; padding: 9px; background: white; }
QPushButton#stage:checked { background: #285a9f; color: white; border-color: #285a9f; }
QFrame#panel { background: white; border: 1px solid #d5dce7; border-radius: 9px; }
QLabel#warning { background: #fff4d6; color: #694d08; border: 1px solid #e3c66f; border-radius: 6px; padding: 7px; }
QLabel#statusGood { background: #def3e6; color: #235d3a; border-radius: 10px; padding: 5px 9px; }
QLabel#statusWarn { background: #fff0ce; color: #71500b; border-radius: 10px; padding: 5px 9px; }
QProgressBar { border: 1px solid #c9d2df; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background: #2f6fed; }
"""


class WorkerSignals(QObject):
    progress = Signal(int, float, str)
    completed = Signal(object)
    failed = Signal(str)


class CalculationWorker(QRunnable):
    def __init__(self, request: CalculationRequest):
        super().__init__()
        self.request = request
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            callback = lambda iteration, delta, message: self.signals.progress.emit(iteration, delta, message)
            result = CentralFieldBackend().calculate(self.request, callback)
            self.signals.completed.emit(result)
        except Exception:
            self.signals.failed.emit(traceback.format_exc())


class PeriodicTablePage(QWidget):
    element_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        title = QLabel("Choose an element")
        title.setFont(_heading_font(22))
        outer.addWidget(title)
        subtitle = QLabel("Select a neutral atom to calculate its central field and ground configuration.")
        subtitle.setStyleSheet("color: #5e697a; margin-bottom: 8px;")
        outer.addWidget(subtitle)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(5)
        for element in ELEMENTS:
            button = QPushButton(f"{element.atomic_number}\n{element.symbol}")
            button.setObjectName("element")
            family = "one" if element.group == 1 else "two" if element.group == 2 else "other"
            button.setProperty("family", family)
            defect_note = (
                "Quantum-defect explorer available."
                if element.group == 1 and element.atomic_number > 1
                else "Quantum defects are available for alkali metals only."
            )
            button.setToolTip(f"{element.name} — Z={element.atomic_number}. {defect_note}")
            button.setAccessibleName(f"{element.name}, atomic number {element.atomic_number}")
            button.clicked.connect(lambda checked=False, e=element: self.element_selected.emit(e))
            grid.addWidget(button, element.display_row - 1, element.display_column - 1)
        grid.setRowMinimumHeight(6, 12)
        grid.setRowMinimumHeight(7, 12)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        legend = QLabel(
            "Blue: one-valence teaching family    Green: two-valence teaching family    "
            "Others: central-field and configuration exploration    "
            "Quantum defects: alkali metals only"
        )
        legend.setWordWrap(True)
        legend.setStyleSheet("color: #596577;")
        outer.addWidget(legend)


class AtomWorkspace(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.element: Element | None = None
        self.result: CalculationResult | None = None
        self.cache: dict[int, CalculationResult] = {}
        app_data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        self.disk_cache = ResultCache(Path(app_data) / "calculation-cache")
        self.thread_pool = QThreadPool.globalInstance()
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        top = QHBoxLayout()
        back = QPushButton("← Periodic table")
        back.clicked.connect(self.back_requested)
        top.addWidget(back)
        self.identity = QLabel("No element selected")
        self.identity.setFont(_heading_font(20))
        top.addWidget(self.identity)
        top.addStretch(1)
        self.status = QLabel("Not calculated")
        self.status.setObjectName("statusWarn")
        top.addWidget(self.status)
        outer.addLayout(top)

        self.warning = QLabel()
        self.warning.setObjectName("warning")
        self.warning.setWordWrap(True)
        self.warning.hide()
        outer.addWidget(self.warning)

        stage_layout = QHBoxLayout()
        self.stage_group = QButtonGroup(self)
        self.stage_group.setExclusive(True)
        stage_names = ("1  Central field", "2  Configuration", "3  Terms", "4  Fine structure")
        self.stage_buttons: list[QPushButton] = []
        for index, name in enumerate(stage_names):
            button = QPushButton(name)
            button.setObjectName("stage")
            button.setCheckable(True)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.stage_group.addButton(button, index)
            self.stage_buttons.append(button)
            stage_layout.addWidget(button)
        self.stage_buttons[0].setChecked(True)
        self.stage_group.idClicked.connect(self._stage_changed)
        outer.addLayout(stage_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(left_panel)
        self.diagram_title = QLabel("Gross energy structure")
        self.diagram_title.setFont(_heading_font(16))
        left_layout.addWidget(self.diagram_title)
        self.diagram = EnergyDiagramWidget()
        left_layout.addWidget(self.diagram, 1)
        self.lower_tabs = QTabWidget()
        self.radial_plot = RadialPlotWidget()
        self.lower_tabs.addTab(self.radial_plot, "Radial orbitals")
        self.defect_stack = QStackedWidget()
        self.defect_table = QTableWidget(0, 4)
        self.defect_table.setHorizontalHeaderLabels(["n", "l", "Binding / Ha", "δₗ(n)"])
        self.defect_table.horizontalHeader().setStretchLastSection(True)
        self.defect_stack.addWidget(self.defect_table)
        self.defect_unavailable = QLabel(
            "Quantum defects are available only for alkali-metal atoms.\n\n"
            "An alkali atom has one valence electron outside filled subshells, so its excited states form "
            "identifiable Rydberg series converging on the singly ionized core."
        )
        self.defect_unavailable.setWordWrap(True)
        self.defect_unavailable.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.defect_unavailable.setStyleSheet("color: #5e697a; padding: 24px;")
        self.defect_stack.addWidget(self.defect_unavailable)
        self.defect_tab_index = self.lower_tabs.addTab(self.defect_stack, "Quantum defects (alkalis only)")
        left_layout.addWidget(self.lower_tabs)
        splitter.addWidget(left_panel)

        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right_layout = QVBoxLayout(right_panel)
        self.side_tabs = QTabWidget()
        learn_scroll = QScrollArea()
        learn_scroll.setWidgetResizable(True)
        learn_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.learn_label = QLabel()
        self.learn_label.setWordWrap(True)
        self.learn_label.setTextFormat(Qt.TextFormat.RichText)
        self.learn_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        learn_scroll.setWidget(self.learn_label)
        self.side_tabs.addTab(learn_scroll, "Learn")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.side_tabs.addTab(self.log, "Calculation log")
        self.compare_label = QLabel("No freely redistributable experimental dataset is installed yet.")
        self.compare_label.setWordWrap(True)
        self.compare_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.side_tabs.addTab(self.compare_label, "Compare")
        right_layout.addWidget(self.side_tabs, 1)
        self.progress_label = QLabel("Ready")
        right_layout.addWidget(self.progress_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 120)
        self.progress.setValue(0)
        right_layout.addWidget(self.progress)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, 1)

    def select_element(self, element: Element):
        self.element = element
        self.identity.setText(f"{element.symbol}   {element.name}   ·   Z = {element.atomic_number}")
        self._calculate_current()

    def _calculate_current(self):
        if not self.element:
            return
        element = self.element
        cached = self.cache.get(element.atomic_number)
        if cached is None:
            cached = self.disk_cache.get(element.atomic_number)
        if cached:
            self._apply_result(cached)
            return
        self.result = None
        self.diagram.set_result(None)
        self.radial_plot.set_result(None)
        self.status.setText("Calculating…")
        self.status.setObjectName("statusWarn")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.progress.setValue(0)
        self.progress_label.setText("Preparing radial grid")
        request = CalculationRequest(element.atomic_number, grid_points=1000, n_max=6)
        worker = CalculationWorker(request)
        worker.signals.progress.connect(self._progress)
        worker.signals.completed.connect(self._calculation_complete)
        worker.signals.failed.connect(self._calculation_failed)
        self.thread_pool.start(worker)

    @Slot(int, float, str)
    def _progress(self, iteration: int, delta: float, message: str):
        self.progress.setValue(min(iteration, self.progress.maximum()))
        delta_text = "first iteration" if delta == float("inf") else f"Δ = {delta:.2e} Ha"
        self.progress_label.setText(f"{message}: iteration {iteration}, {delta_text}")

    @Slot(object)
    def _calculation_complete(self, result: CalculationResult):
        if not self.element or result.element.atomic_number != self.element.atomic_number:
            self.cache[result.element.atomic_number] = result
            return
        self.cache[result.element.atomic_number] = result
        try:
            self.disk_cache.put(result)
        except OSError:
            pass
        self._apply_result(result)

    def _apply_result(self, result: CalculationResult):
        self.result = result
        self.diagram.set_result(result)
        self.radial_plot.set_result(result)
        self.progress.setValue(self.progress.maximum())
        self.progress_label.setText(
            f"{result.method_name} · {result.iterations} iteration(s) · "
            f"{'converged' if result.converged else 'not converged'}"
        )
        ls_status = str(result.diagnostics.get("ls_coupling", "not evaluated"))
        self.status.setText(f"LS: {ls_status}")
        self.status.setObjectName("statusGood" if ls_status in {"supported", "single valence electron"} else "statusWarn")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.warning.setText("\n".join(result.warnings))
        self.warning.setVisible(bool(result.warnings))
        self._populate_defects()
        self._populate_compare()
        self._stage_changed(self.stage_group.checkedId())

    @Slot(str)
    def _calculation_failed(self, details: str):
        self.progress_label.setText("Calculation failed")
        QMessageBox.critical(self, "Calculation failed", details)

    @Slot(int)
    def _stage_changed(self, stage_id: int):
        stage = TheoryStage(max(0, stage_id))
        self.diagram.set_stage(stage)
        self.diagram_title.setText(("Central-field orbitals", "Electron configuration", "Spectroscopic terms", "Fine-structure levels")[stage])
        if not self.result:
            self.learn_label.setText("<h3>Calculation in progress</h3><p>The derivation will appear here.</p>")
            return
        visible_events = [event for event in self.result.trace if event.stage <= stage]
        current = [event for event in visible_events if event.stage == stage] or visible_events[-1:]
        self.learn_label.setText("".join(_event_html(event) for event in current))
        log_text = "\n\n".join(_event_text(event) for event in visible_events)
        self.log.setPlainText(log_text)

    def _populate_defects(self):
        assert self.result is not None
        available = self.result.element.group == 1 and self.result.element.atomic_number > 1
        self.defect_stack.setCurrentWidget(self.defect_table if available else self.defect_unavailable)
        self.lower_tabs.setTabText(
            self.defect_tab_index,
            "Quantum defects" if available else "Quantum defects (alkalis only)",
        )
        if not available:
            self.defect_table.setRowCount(0)
            return
        self.defect_table.setColumnCount(4)
        self.defect_table.setHorizontalHeaderLabels(["n", "l", "Binding / Ha", "δₗ(n)"])
        self.defect_table.setRowCount(len(self.result.quantum_defects))
        for row, point in enumerate(self.result.quantum_defects):
            values = (str(point.n), "spdfgh"[point.l], f"{point.binding_hartree:.7f}", f"{point.defect:.5f}")
            for column, value in enumerate(values):
                self.defect_table.setItem(row, column, QTableWidgetItem(value))

    def _populate_compare(self):
        assert self.result is not None
        calculated = format_configuration(self.result.calculated_configuration)
        accepted = format_configuration(self.result.accepted_configuration)
        self.compare_label.setText(
            f"<h3>Configuration comparison</h3>"
            f"<p><b>Calculated filling:</b> {html.escape(calculated)}</p>"
            f"<p><b>Accepted:</b> {html.escape(accepted)}</p>"
            f"<p>Experimental energy values are deliberately absent until a dataset's free redistribution rights are verified. "
            f"Reference values will be overlays only and will never modify the calculation.</p>"
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Atomic Structure Explorer")
        self.resize(1240, 820)
        self.setStyleSheet(APP_STYLE)
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        brand = QLabel("ψ   Atomic Structure Explorer")
        brand.setObjectName("brand")
        header_layout.addWidget(brand)
        header_layout.addStretch(1)
        self.home_button = QPushButton("Periodic table")
        self.home_button.setObjectName("nav")
        self.home_button.clicked.connect(self.show_table)
        header_layout.addWidget(self.home_button)
        layout.addWidget(header)
        self.stack = QStackedWidget()
        self.table_page = PeriodicTablePage()
        self.workspace = AtomWorkspace()
        self.table_page.element_selected.connect(self.show_element)
        self.workspace.back_requested.connect(self.show_table)
        self.stack.addWidget(self.table_page)
        self.stack.addWidget(self.workspace)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        self.addAction(quit_action)

    @Slot()
    def show_table(self):
        self.stack.setCurrentWidget(self.table_page)

    @Slot(object)
    def show_element(self, element: Element):
        self.stack.setCurrentWidget(self.workspace)
        self.workspace.select_element(element)


def _heading_font(size: int) -> QFont:
    font = QFont()
    font.setPointSize(size)
    font.setWeight(QFont.Weight.DemiBold)
    return font


def _event_html(event) -> str:
    values = "".join(f"<li><b>{html.escape(k)}:</b> {html.escape(v)}</li>" for k, v in event.values.items())
    equation = f"<p style='font-family:serif;background:#edf2f8;padding:8px'>{html.escape(event.equation)}</p>" if event.equation else ""
    interpretation = f"<p><b>Interpretation:</b> {html.escape(event.interpretation)}</p>" if event.interpretation else ""
    return (
        f"<h3>{html.escape(event.title)}</h3><p>{html.escape(event.explanation)}</p>"
        f"{equation}{('<ul>' + values + '</ul>') if values else ''}{interpretation}"
    )


def _event_text(event) -> str:
    lines = [f"[{event.stage.name.replace('_', ' ').title()}] {event.title}", event.explanation]
    if event.equation:
        lines.append(f"Equation: {event.equation}")
    lines.extend(f"  {key}: {value}" for key, value in event.values.items())
    if event.interpretation:
        lines.append(f"Interpretation: {event.interpretation}")
    return "\n".join(lines)
