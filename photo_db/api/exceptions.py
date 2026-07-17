from json import dumps
from werkzeug.exceptions import Conflict


class DuplicateException(Conflict):
    uuid: str
    pdb_code = 1001

    def __init__(self, uuid, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uuid = uuid

    def get_body(
        self,
        environ=None,
        scope: dict | None = None,
    ) -> str:
        return dumps(
            {
                "type": self.__class__.__name__,
                "pdb_code": self.pdb_code,
                "uuid": self.uuid,
                "msg": self.description,
            }
        )

    def get_headers(
        self,
        environ=None,
        scope: dict | None = None,
    ) -> list[tuple[str, str]]:
        """Get a list of headers."""
        return [("Content-Type", "application/json; charset=utf-8")]


class SimilarException(DuplicateException):
    pdb_code = 1002
