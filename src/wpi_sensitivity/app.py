from __future__ import annotations

import sys
from pathlib import Path


def run(preset: Path | None = None) -> int:
    from PySide6.QtWidgets import QApplication

    from .gui.main_window import MainWindow

    application = QApplication(sys.argv)
    application.setApplicationName("WPI Sensitivity Analyzer")
    window = MainWindow(preset)
    window.show()
    return application.exec()
