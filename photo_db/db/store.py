from datetime import datetime
from os.path import join
from sqlite3 import Connection, connect

from ..config import Config, default_config
from ..photo import Photo

_table = {
    "uuid": "VARCHAR(50) PRIMARY KEY NOT NULL",
    "camera": "VARCHAR(50) NOT NULL",
    "date": "int(4) NOT NULL",
    "latitude": "float",
    "longitude": "float",
    "altitude": "float",
    "width": "int not NULL",
    "height": "int not NULL",
    "hash": "VARCHAR(250) not NULL",
    "extension": "VARCHAR(5) not NULL",
    "scanned": "int(4) not NULL",
    "rotation": "int NOT NULL DEFAULT 0",
}
_select = f"SELECT {','.join(_table.keys())} FROM photo"


class StoreDB:
    """SQLite-backed store of uploaded/imported photo metadata.

    Instantiated with an explicit ``Config`` (dependency injection) instead
    of relying on a shared global, so tests (and multiple stores in the same
    process) can use independent, isolated databases.
    """

    def __init__(self, config: Config = default_config):
        self.config = config
        self.init_store_db()

    def _cnx(self) -> Connection:
        return connect(join(self.config.STORE_URL, ".photo.db"))

    def init_store_db(self):
        c = self._cnx()
        try:
            cur = c.execute(
                """SELECT name FROM sqlite_master WHERE type='table' AND name='photo';"""
            )
            result = cur.fetchone()
            if result is None:
                fields = ",".join([f"{f} {d}" for f, d in _table.items()])
                c.execute(f"""CREATE TABLE IF NOT EXISTS photo ({fields});""")
                c.execute("""CREATE INDEX index_hash ON photo(hash);""")
                c.commit()
            else:
                # Migrate older stores created before a column existed.
                existing = {row[1] for row in c.execute("PRAGMA table_info(photo);")}
                for field, ddl in _table.items():
                    if field not in existing:
                        c.execute(f"ALTER TABLE photo ADD COLUMN {field} {ddl};")
                c.commit()
        finally:
            if c:
                c.close()

    def insert_photo(self, p: Photo):
        fields = []
        qms = []
        values = []
        for field in _table.keys():
            fields.append(field)
            qms.append("?")
            value = getattr(p, field)
            if isinstance(value, datetime):
                value = int(value.timestamp())
            values.append(value)
        stmt = f"INSERT INTO photo ({','.join(fields)}) VALUES ({','.join(qms)});"
        c = self._cnx()
        try:
            c.execute(stmt, tuple(values))
            c.commit()
        finally:
            if c:
                c.close()

    def get_hashes(self) -> dict[str, str]:
        c = self._cnx()
        try:
            cur = c.execute("""select hash, uuid from photo;""")
            return {r[0]: r[1] for r in cur}
        finally:
            if c:
                c.close()

    def get_photo(self, uuid: str) -> Photo:
        qry = f"{_select} WHERE uuid = ?;"
        c = self._cnx()
        try:
            for r in c.execute(qry, (uuid,)):
                photo_args = {f: r[idx] for idx, f in enumerate(_table.keys())}
                return Photo(**photo_args, config=self.config)
        finally:
            if c:
                c.close()

    def lookup_hash(self, hash: str) -> str | None:
        c = self._cnx()
        try:
            for r in c.execute(f"{_select} WHERE hash = ?;", (hash,)):
                return r[0]  # uuid is first value
        finally:
            if c:
                c.close()

    def update_rotation(self, uuid: str, rotation: int) -> None:
        c = self._cnx()
        try:
            c.execute("UPDATE photo SET rotation = ? WHERE uuid = ?;", (rotation, uuid))
            c.commit()
        finally:
            if c:
                c.close()

    def since(
        self,
        scanned_after: datetime | None = None,
        limit: int = 5000,
        after_uuid: str | None = None,
    ) -> list[Photo]:
        """Return photos with ``scanned`` after ``scanned_after`` (or all
        photos if ``None``), ordered by ``scanned`` ascending, for
        incremental "lean" sync to thick clients: cheap metadata only, no
        image bytes. ``limit`` caps a single page so very large libraries
        can be synced in several round trips using the last row's
        ``scanned`` timestamp as the next page's cursor."""
        fields = [f for f in _table.keys()]
        params = []
        where = ""
        if scanned_after is not None:
            timestamp = int(scanned_after.timestamp())
            if after_uuid is not None:
                where = " WHERE scanned > ? OR (scanned = ? AND uuid > ?)"
                params.extend((timestamp, timestamp, after_uuid))
            else:
                where = " WHERE scanned > ?"
                params.append(timestamp)
        qry = f"SELECT {','.join(fields)} FROM photo{where} ORDER BY scanned ASC, uuid ASC LIMIT ?"
        params.append(limit)

        c = self._cnx()
        results = []
        try:
            for r in c.execute(qry, tuple(params)):
                photo_args = {f: r[idx] for idx, f in enumerate(_table.keys())}
                results.append(Photo(**photo_args, config=self.config))
            return results
        finally:
            if c:
                c.close()

    def search(
        self,
        start: datetime = None,
        end: datetime = None,
        circle: tuple[float, float, float] = None,
    ) -> list[Photo]:
        fields = [f for f in _table.keys()]
        criteria = []
        params = []
        if start:
            criteria.append("date >= ?")
            params.append(int(start.timestamp()))
        if end:
            criteria.append("date <= ?")
            params.append(int(end.timestamp()))
        if circle:
            criteria.append("latitude >= ?")
            params.append(circle[0] - circle[2])
            criteria.append("latitude <= ?")
            params.append(circle[0] + circle[2])
            criteria.append("longitude >= ?")
            params.append(circle[1] - circle[2])
            criteria.append("longitude <= ?")
            params.append(circle[1] + circle[2])
        where = ""
        if criteria:
            where = f" WHERE {' AND '.join(criteria)}"
        qry = f"SELECT {','.join(fields)} FROM photo{where}"

        c = self._cnx()
        results = []
        try:
            for r in c.execute(qry, tuple(params)):
                photo_args = {f: r[idx] for idx, f in enumerate(_table.keys())}
                results.append(Photo(**photo_args, config=self.config))
            return results
        finally:
            if c:
                c.close()


__all__ = ["StoreDB"]
