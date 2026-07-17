"""Desktop UI entry point.

Usage::

    uv run --extra ui python -m photo_db.ui.app

or via the ``photodb-ui.py`` script at the repo root.
"""

import sys

from PySide6.QtWidgets import QApplication

from photo_db.config import default_config
from photo_db.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Photo DB")
    window = MainWindow(default_config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
