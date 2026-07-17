from datetime import datetime
from os.path import join
from sqlite3 import Connection, connect

from ..config import Config
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
}
_select = f"SELECT {','.join(_table.keys())} FROM photo"


def init_store_db():
    global _table
    c = _cnx()
    try:
        cur = c.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='photo';""")
        result = cur.fetchone()
        if result is None:
            fields = ",".join([f"{f} {d}" for f, d in _table.items()])
            c.execute(f"""CREATE TABLE IF NOT EXISTS photo ({fields});""")
            c.execute("""CREATE INDEX index_hash ON photo(hash);""")
            c.commit()

    finally:
        if c:
            c.close()


def insert_photo(p: Photo):
    global _table
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
    c = _cnx()
    try:
        c.execute(stmt, tuple(values))
        c.commit()
    finally:
        if c:
            c.close()


def get_hashes() -> dict[str, str]:
    c = _cnx()
    try:
        cur = c.execute("""select hash, uuid from photo;""")
        return {r[0]: r[1] for r in cur}
    finally:
        if c:
            c.close()


def get_photo(uuid: str) -> Photo:
    global _select, _table
    qry = f"{_select} WHERE uuid = ?;"

    c = _cnx()
    try:
        for r in c.execute(qry, (uuid,)):
            photo_args = {f: r[idx] for idx, f in enumerate(_table.keys())}
            return Photo(**photo_args)
    finally:
        if c:
            c.close()


def lookup_hash(hash: str) -> str | None:
    global _select
    c = _cnx()
    try:
        for r in c.execute(f"{_select} WHERE hash = ?;", (hash,)):
            return r[0]  # uuid is first value
    finally:
        if c:
            c.close()


def search(
    start: datetime = None,
    end: datetime = None,
    circle: tuple[float, float, float] = None,
) -> list[Photo]:
    global _table
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

    c = _cnx()
    results = []
    try:
        for r in c.execute(qry, tuple(params)):
            photo_args = {f: r[idx] for idx, f in enumerate(_table.keys())}
            results.append(Photo(**photo_args))
        return results
    finally:
        if c:
            c.close()


def _cnx() -> Connection:
    return connect(join(Config.STORE_URL, ".photo.db"))


__all__ = [
    "init_store_db",
    "insert_photo",
    "get_photo",
    "get_hashes",
    "lookup_hash",
    "search",
]
