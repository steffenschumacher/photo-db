"""Flask HTTP API (server side of a remote store). Requires the `api`
extra (Flask/werkzeug) - core scanning/storage code does not depend on
this package; see `photo_db.exceptions` for the framework-free duplicate/
similar exceptions shared across local and remote clients.
"""
