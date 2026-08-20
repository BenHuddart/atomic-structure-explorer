from __future__ import annotations

from collections import defaultdict

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from ..models import CalculationResult, TheoryStage


_L_SYMBOLS = "spdf"


class EnergyDiagramWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: CalculationResult | None = None
        self._stage = TheoryStage.CENTRAL_FIELD
        self.setMinimumHeight(370)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("Calculated atomic energy-level diagram")

    def set_result(self, result: CalculationResult | None) -> None:
        self._result = result
        self.update()

    def set_stage(self, stage: TheoryStage) -> None:
        self._stage = stage
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        foreground = palette.color(palette.ColorRole.Text)
        muted = palette.color(palette.ColorRole.PlaceholderText)
        accent = palette.color(palette.ColorRole.Highlight)
        rect = self.rect().adjusted(58, 34, -22, -34)
        painter.setPen(QPen(muted, 1))
        painter.drawLine(rect.left(), rect.top(), rect.left(), rect.bottom())
        painter.drawText(QRectF(4, 4, 50, 24), Qt.AlignmentFlag.AlignCenter, "Energy")
        for index, symbol in enumerate(_L_SYMBOLS):
            x = rect.left() + (index + 0.5) * rect.width() / 4
            painter.drawText(QRectF(x - 30, 6, 60, 22), Qt.AlignmentFlag.AlignCenter, symbol)

        if not self._result:
            painter.setPen(muted)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Choose an element to calculate")
            return

        marks = self._marks_for_stage(self._result)
        if not marks:
            painter.setPen(muted)
            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                "This theory stage is not supported for the selected valence space.",
            )
            return
        energies = np.array([m[1] for m in marks], dtype=float)
        low = float(np.min(energies))
        high = min(0.0, float(np.max(energies) + 0.12 * max(np.ptp(energies), 0.1)))
        if high - low < 1e-8:
            high = low + 1.0

        grouped: dict[tuple[int, int], int] = defaultdict(int)
        for l, energy, label, provenance in marks:
            y = rect.bottom() - (energy - low) / (high - low) * rect.height()
            x_center = rect.left() + (l + 0.5) * rect.width() / 4
            collision_key = (l, round(y / 7))
            offset = grouped[collision_key] * 9
            grouped[collision_key] += 1
            y -= offset
            pen_color = QColor("#285a9f")
            if provenance != "calculated":
                pen_color = muted
            pen = QPen(pen_color, 2 if energy == low else 1.5)
            painter.setPen(pen)
            painter.drawLine(QPointF(x_center - 34, y), QPointF(x_center + 34, y))
            painter.setPen(foreground)
            font = QFont(painter.font())
            font.setPointSizeF(max(7.5, font.pointSizeF() - 1.0))
            painter.setFont(font)
            painter.drawText(QPointF(x_center + 39, y + 4), label)

        painter.setPen(muted)
        painter.drawText(QPointF(rect.left() - 48, rect.bottom() + 4), f"{low * 27.211386:.2f}")
        painter.drawText(QPointF(rect.left() - 22, rect.top() + 4), "0 eV")

    def _marks_for_stage(self, result: CalculationResult):
        if self._stage <= TheoryStage.CONFIGURATION or not result.levels:
            marks = []
            for orbital in result.orbitals:
                if orbital.l <= 3:
                    label = f"{orbital.label}  {orbital.energy_hartree * 27.211386:.2f} eV"
                    marks.append((orbital.l, orbital.energy_hartree, label, "calculated"))
            return marks

        fine = self._stage == TheoryStage.FINE_STRUCTURE
        if fine:
            selected = list(result.levels)
        else:
            # A term is the degeneracy-weighted centre of all of its J levels.
            # Some unsplit terms are stored directly at the TERMS stage, while
            # resolved multiplets exist only as FINE_STRUCTURE records.
            buckets: dict[tuple[str, str], list] = defaultdict(list)
            for level in result.levels:
                buckets[(level.configuration, level.term)].append(level)
            selected = []
            for (configuration, term), levels in buckets.items():
                explicit_terms = [level for level in levels if level.stage <= TheoryStage.TERMS]
                if explicit_terms:
                    energy = float(np.mean([level.energy_hartree for level in explicit_terms]))
                else:
                    weights = np.asarray([_j_degeneracy(level.j) for level in levels])
                    energy = float(np.average([level.energy_hartree for level in levels], weights=weights))
                selected.append(type(levels[0])(configuration, term, "", energy, TheoryStage.TERMS))
        marks = []
        for level in selected:
            l = _configuration_l(level.configuration)
            if l > 3:
                continue
            suffix = f"{level.term}{level.j}" if fine else level.term
            marks.append((l, level.energy_hartree, f"{level.configuration} {suffix}", level.provenance))
        return marks


def _configuration_l(configuration: str) -> int:
    for letter in reversed(configuration):
        if letter in _L_SYMBOLS:
            return _L_SYMBOLS.index(letter)
    return 0


def _j_degeneracy(j_text: str) -> float:
    try:
        if "/" in j_text:
            numerator, denominator = j_text.split("/", 1)
            j = float(numerator) / float(denominator)
        else:
            j = float(j_text)
        return 2.0 * j + 1.0
    except (TypeError, ValueError, ZeroDivisionError):
        return 1.0


class RadialPlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: CalculationResult | None = None
        self._hovered_label: str | None = None
        self._curve_geometry: list[tuple[object, np.ndarray, QColor]] = []
        self.setMinimumHeight(230)
        self.setMouseTracking(True)
        self.setAccessibleName("Central potential and radial orbital plot")

    def set_result(self, result: CalculationResult | None) -> None:
        self._result = result
        self._hovered_label = None
        if result:
            labels = ", ".join(orbital.label for orbital in result.orbitals[-4:])
            self.setAccessibleDescription(f"Radial probability curves for {labels}. Move the pointer over a curve for details.")
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(46, 47, -16, -30)
        foreground = self.palette().color(self.palette().ColorRole.Text)
        muted = self.palette().color(self.palette().ColorRole.PlaceholderText)
        painter.setPen(QPen(muted, 1))
        painter.drawRect(rect)
        painter.drawText(QRectF(rect.left(), 1, rect.width(), 20), Qt.AlignmentFlag.AlignCenter, "Radial probability P²(r)")
        painter.drawText(QRectF(rect.left(), rect.bottom() + 5, rect.width(), 20), Qt.AlignmentFlag.AlignCenter, "r / a₀ (log scale)")
        if not self._result or not self._result.orbitals:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No radial orbitals")
            return
        colors = [QColor("#2563b4"), QColor("#d06419"), QColor("#16804a"), QColor("#9449b5")]
        labels = [orbital.label for orbital in self._result.orbitals[-4:]]
        unique_labels = list(dict.fromkeys(labels))[-4:]
        color_by_label = {label: colors[index % len(colors)] for index, label in enumerate(unique_labels)}
        all_r = [orbital.radius_bohr for orbital in self._result.orbitals[-4:]]
        x_low = min(float(np.log10(radii[0])) for radii in all_r)
        x_high = max(float(np.log10(radii[-1])) for radii in all_r)
        self._curve_geometry = []
        for orbital in self._result.orbitals[-4:]:
            if orbital.label not in color_by_label:
                continue
            r = orbital.radius_bohr
            x = np.log10(r)
            values = orbital.radial_u**2
            peak = float(np.max(values)) or 1.0
            values = values / peak
            path = QPainterPath()
            screen_points = []
            for point_index in np.linspace(0, len(r) - 1, min(600, len(r))).astype(int):
                px = rect.left() + (x[point_index] - x_low) / (x_high - x_low) * rect.width()
                py = rect.bottom() - values[point_index] * rect.height() * 0.88
                screen_points.append((px, py))
                if path.elementCount() == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            color = color_by_label[orbital.label]
            self._curve_geometry.append((orbital, np.asarray(screen_points), color))
            draw_color = QColor(color)
            if self._hovered_label and self._hovered_label != orbital.label:
                draw_color.setAlpha(65)
            width = 3.4 if self._hovered_label == orbital.label else 1.9
            painter.setPen(QPen(draw_color, width))
            painter.drawPath(path)
        for index, label in enumerate(unique_labels):
            legend_x = rect.left() + index * max(76, rect.width() / max(len(unique_labels), 1))
            legend_color = color_by_label[label]
            painter.setPen(QPen(legend_color, 3))
            painter.drawLine(QPointF(legend_x, 30), QPointF(legend_x + 18, 30))
            painter.setPen(foreground)
            painter.drawText(QPointF(legend_x + 23, 34), label)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self._curve_geometry:
            return super().mouseMoveEvent(event)
        pointer = np.array([event.position().x(), event.position().y()])
        nearest = None
        nearest_distance = float("inf")
        for orbital, points, color in self._curve_geometry:
            distance = float(np.min(np.linalg.norm(points - pointer, axis=1)))
            if distance < nearest_distance:
                nearest = orbital
                nearest_distance = distance
        label = nearest.label if nearest is not None and nearest_distance <= 14.0 else None
        if label != self._hovered_label:
            self._hovered_label = label
            self.update()
        if label and nearest is not None:
            details = (
                f"{nearest.energy_hartree:.6f} Ha "
                f"({nearest.energy_hartree * 27.211386:.3f} eV)"
            )
            QToolTip.showText(
                event.globalPosition().toPoint(),
                f"{nearest.label} orbital\n{details}\nOccupation: {nearest.occupation}",
                self,
            )
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self._hovered_label is not None:
            self._hovered_label = None
            self.update()
        QToolTip.hideText()
        super().leaveEvent(event)
