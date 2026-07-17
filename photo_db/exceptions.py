"""Domain exceptions for duplicate/near-duplicate photo detection.

Deliberately free of any web-framework dependency (unlike the previous
version of this module, which subclassed ``werkzeug.exceptions.Conflict``)
so core scanning/storage code (``photo_db.scanner``, ``photo_db.store``,
``photo_db.client``) doesn't require the ``api`` extra (Flask/werkzeug) to
be installed - only ``photo_db.api.web_store`` (the Flask app) needs to
translate these into HTTP responses, which it does via an explicit
``errorhandler`` rather than relying on werkzeug's automatic handling of
``HTTPException`` subclasses.
"""

from json import dumps


class DuplicateException(Exception):
    """Raised when a photo being uploaded/checked already exists in the
    store (identical hash).

    Wire protocol: the web API responds with HTTP 409 and a JSON body (see
    :meth:`to_json`); ``WebPDBClient.process_response`` re-raises this
    client-side based on that body's ``pdb_code``.
    """

    code = 409
    pdb_code = 1001

    def __init__(self, uuid: str, description: str = ""):
        super().__init__(description)
        self.uuid = uuid
        self.description = description

    def to_json(self) -> str:
        return dumps(
            {
                "type": self.__class__.__name__,
                "pdb_code": self.pdb_code,
                "uuid": self.uuid,
                "msg": self.description,
            }
        )


class SimilarException(DuplicateException):
    """Raised when a photo isn't an exact duplicate, but is similar enough
    (within ``Config.SIMILARITY``) to a "preferable" existing photo."""

    pdb_code = 1002
