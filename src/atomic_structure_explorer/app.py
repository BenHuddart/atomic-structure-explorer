from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:  # pragma: no cover - depends on local installation
        raise SystemExit(
            "PySide6 is required for the desktop application. Install the project with: pip install -e ."
        ) from exc

    from .gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Atomic Structure Explorer")
    app.setOrganizationName("Atomic Structure Teaching")
    icon_path = Path(__file__).with_name("assets") / "app-icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(100, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
