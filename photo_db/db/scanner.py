import time
from datetime import datetime
from sqlite3 import connect, Connection, OperationalError

from ..photo import Photo, LocalPhoto
from .store import _table as store_table


class ScanDB:
    def __init__(self, db_uri=":memory:"):
        self.cnx: Connection = connect(db_uri or ":memory:")
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
        self.cnx.execute(stmt, tuple(values))
        self.cnx.commit()

    def get_photo(self, uuid: str) -> LocalPhoto:
        qry = f"{ self.select} WHERE uuid = '{uuid}')"
        if cur := self.cnx.execute(qry):
            r = next(cur)
            photo_args = {f: r[idx] for idx, f in enumerate(self.table.keys())}
            return LocalPhoto(**photo_args)

    def lookup_hash(self, hash: str) -> str | None:
        if cur := self.cnx.execute(f"{ self.select} WHERE hash = '{hash}')"):
            r = next(cur)
            return r[0]  # uuid is first value

    def search(
        self,
        start: datetime = None,
        end: datetime = None,
        circle: tuple[float, float, float] = None,
    ) -> list[LocalPhoto]:
        fields = [f for f in self.table.keys()]
        criteria = []
        if start:
            criteria.append(f"date >= {int(start.timestamp())}")
        if end:
            criteria.append(f"date <= {int(end.timestamp())}")
        if circle:
            criteria.append(f"latitude >= {circle[0] - circle[2]}")
            criteria.append(f"latitude <= {circle[0] + circle[2]}")
            criteria.append(f"longitude >= {circle[1] - circle[2]}")
            criteria.append(f"longitude <= {circle[1] + circle[2]}")
        where = ""
        if criteria:
            where = f" WHERE {' AND '.join(criteria)}"
        qry = f"SELECT {','.join(fields)} FROM photo{where};"

        results = []
        for r in self.cnx.execute(qry):
            photo_args = {f: r[idx] for idx, f in enumerate(self.table.keys())}
            results.append(LocalPhoto(**photo_args))
        return results


__all__ = ["ScanDB"]
