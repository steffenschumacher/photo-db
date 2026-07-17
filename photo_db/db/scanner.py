from datetime import datetime
from sqlite3 import Connection, connect
from threading import Lock

from ..config import Config, default_config
from ..photo import LocalPhoto
from .store import _table as store_table


class ScanDB:
    def __init__(self, db_uri=":memory:", config: Config = default_config):
        self.config = config
        # A Scanner (and its ScanDB) is typically constructed on one thread
        # (e.g. the GUI thread, from ScanDialog) but driven from another
        # (e.g. a QThread worker running scan_dir()/uploading_complete()),
        # so the connection must allow cross-thread use; the lock serializes
        # actual access, since sqlite3 connections aren't safe for
        # concurrent simultaneous use even with check_same_thread disabled.
        self.cnx: Connection = connect(db_uri or ":memory:", check_same_thread=False)
        self._lock = Lock()
        self.table = store_table.copy()
        self.table.update(
            {
                "local_path": "VARCHAR(400) NOT NULL",
                "reject_reason": "VARCHAR(50)",
                "duplicate_uuid": "VARCHAR(30)",
                "duplicate_src": "VARCHAR(10)",
                "status": "VARCHAR(10) NOT NULL",
            }
        )
        self.select = f"SELECT {','.join(self.table.keys())} FROM photo"
        self.init_scanner_db()

    def init_scanner_db(self):
        with self._lock:
            cur = self.cnx.execute(
                """SELECT name FROM sqlite_master WHERE type='table' AND name='photo';"""
            )
            result = cur.fetchone()
            if result is None:
                fields = ",".join([f"{f} {d}" for f, d in self.table.items()])
                self.cnx.execute(f"""CREATE TABLE IF NOT EXISTS photo ({fields});""")
                self.cnx.execute("""CREATE INDEX index_hash ON photo(hash);""")
                self.cnx.commit()

    def upsert_photo(self, p: LocalPhoto):
        fields = []
        qms = []
        values = []
        for field in self.table.keys():
            fields.append(field)
            qms.append("?")
            value = getattr(p, field)
            if isinstance(value, datetime):
                value = int(value.timestamp())
            values.append(value)
        stmt = f"INSERT OR REPLACE INTO photo ({','.join(fields)}) VALUES ({','.join(qms)});"
        with self._lock:
            self.cnx.execute(stmt, tuple(values))
            self.cnx.commit()

    def get_photo(self, uuid: str) -> LocalPhoto:
        qry = f"{self.select} WHERE uuid = ?;"
        with self._lock:
            cur = self.cnx.execute(qry, (uuid,))
            r = next(cur, None)
        if r:
            photo_args = {f: r[idx] for idx, f in enumerate(self.table.keys())}
            return LocalPhoto(**photo_args, config=self.config)

    def lookup_hash(self, hash: str) -> str | None:
        with self._lock:
            cur = self.cnx.execute(f"{self.select} WHERE hash = ?;", (hash,))
            r = next(cur, None)
        if r:
            return r[0]  # uuid is first value

    def search(
        self,
        start: datetime = None,
        end: datetime = None,
        circle: tuple[float, float, float] = None,
    ) -> list[LocalPhoto]:
        fields = [f for f in self.table.keys()]
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
        qry = f"SELECT {','.join(fields)} FROM photo{where};"

        results = []
        with self._lock:
            rows = list(self.cnx.execute(qry, tuple(params)))
        for r in rows:
            photo_args = {f: r[idx] for idx, f in enumerate(self.table.keys())}
            results.append(LocalPhoto(**photo_args, config=self.config))
        return results


__all__ = ["ScanDB"]
