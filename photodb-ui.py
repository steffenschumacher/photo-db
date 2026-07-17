#!/usr/bin/env python3
"""Launch the PySide6 desktop "thick client" UI.

Requires the ``ui`` extra: ``uv sync --extra ui`` (or ``pip install
photo-db[ui]``).
"""

import sys

from photo_db.ui.app import main

if __name__ == "__main__":
    sys.exit(main())
