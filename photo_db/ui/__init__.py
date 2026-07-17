"""PySide6 desktop "thick client" UI.

Lets a user maintain a photo library both locally and against a remote
web backend: recursively scan folders and adopt non-duplicate photos into
the store, and browse the library via a lazily-loaded thumbnail grid backed
by a local :class:`~photo_db.db.lean_cache.LeanCache` synced from the
central store.

Import from here is intentionally avoided at package import time (PySide6
is an optional extra, see ``pyproject.toml``'s ``ui`` extra) - submodules
import Qt lazily so ``photo_db.ui`` can still be imported for constants/
helpers without Qt installed.
"""
