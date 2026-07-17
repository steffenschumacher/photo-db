"""Local sqlite cache of lean (metadata-only) photo records synced from a
central store (local or remote).

This lets the thick client:
  - determine locally whether a candidate photo (by hash) already exists in
    the library, without a network round trip per file during a scan;
  - browse/preview the library by year/month, fetching thumbnails lazily
    for whatever period is currently visible in the UI.

Only cheap metadata is stored here - never image bytes. Thumbnails are
fetched/cached separately (see ``photo_db.ui``), keyed by uuid.
"""

from datetime import UTC, datetime
from os import makedirs
from os.path import dirname, exists
from sqlite3 import Connection, connect

from ..config import Config, default_config

_table = {
    "uuid": "VARCHAR(50) PRIMARY KEY NOT NULL",
    "hash": "VARCHAR(250) NOT NULL",
    "date": "int(4) NOT NULL",
    "width": "int NOT NULL",
    "height": "int NOT NULL",
    "camera": "VARCHAR(50)",
    "latitude": "float",
    "longitude": "float",
    "extension": "VARCHAR(5) NOT NULL",
    "scanned": "int(4) NOT NULL",
}
_fields = list(_table.keys())
_select = f"SELECT {','.join(_fields)} FROM lean_photo"

# Single-row table tracking the last successful sync cursor (the
# `scanned` timestamp of the most recently synced row), so subsequent
# syncs only need to request what changed since then.
_meta_table_ddl = """
CREATE TABLE IF NOT EXISTS sync_meta (
    id INTEGER PRIMARY KEY CHECK (id = 0),
    last_synced REAL
);
"""


class LeanCache:
    """SQLite-backed local cache of lean photo metadata rows.

    Instantiated with an explicit ``Config`` (dependency injection), reading
    ``config.LEAN_CACHE_PATH`` for the database file location, so tests and
    multiple independent clients in the same process can use isolated
    caches instead of a shared global path.
    """

    def __init__(self, config: Config = default_config):
        self.config = config
        db_dir = dirname(config.LEAN_CACHE_PATH)
        if db_dir and not exists(db_dir):
            makedirs(db_dir)
        self.cnx: Connection = connect(config.LEAN_CACHE_PATH)
        self._init_db()

    def _init_db(self) -> None:
        cur = self.cnx.execute(
            """SELECT name FROM sqlite_master WHERE type='table' AND name='lean_photo';"""
        )
        if cur.fetchone() is None:
            fields = ",".join([f"{f} {d}" for f, d in _table.items()])
            self.cnx.execute(f"CREATE TABLE IF NOT EXISTS lean_photo ({fields});")
            self.cnx.execute("CREATE INDEX index_lean_hash ON lean_photo(hash);")
            self.cnx.execute("CREATE INDEX index_lean_date ON lean_photo(date);")
        self.cnx.execute(_meta_table_ddl)
        self.cnx.commit()

    def upsert_many(self, rows: list[dict]) -> None:
        if not rows:
            return
        qms = ",".join(["?"] * len(_fields))
        stmt = f"INSERT OR REPLACE INTO lean_photo ({','.join(_fields)}) VALUES ({qms});"
        values = [
            tuple(int(row[f]) if f in ("date", "scanned") else row[f] for f in _fields)
            for row in rows
        ]
        self.cnx.executemany(stmt, values)
        self.cnx.commit()

    def last_synced(self) -> float | None:
        cur = self.cnx.execute("SELECT last_synced FROM sync_meta WHERE id = 0;")
        row = cur.fetchone()
        return row[0] if row else None

    def set_last_synced(self, timestamp: float) -> None:
        self.cnx.execute(
            "INSERT INTO sync_meta (id, last_synced) VALUES (0, ?) "
            "ON CONFLICT(id) DO UPDATE SET last_synced = excluded.last_synced;",
            (timestamp,),
        )
        self.cnx.commit()

    def is_known_hash(self, hash_: str) -> str | None:
        """Return the uuid already stored for ``hash_``, or ``None`` if not
        present locally - the cheap, no-network duplicate pre-check."""
        cur = self.cnx.execute("SELECT uuid FROM lean_photo WHERE hash = ?;", (hash_,))
        row = cur.fetchone()
        return row[0] if row else None

    def hashes(self) -> dict[str, str]:
        cur = self.cnx.execute("SELECT hash, uuid FROM lean_photo;")
        return {r[0]: r[1] for r in cur}

    def query_by_month(self, year: int, month: int) -> list[dict]:
        """Return lean rows whose capture ``date`` falls within the given
        calendar month, ordered chronologically - the primary query used by
        the thumbnail grid to page results by the period the user is
        browsing."""
        start = datetime(year, month, 1, tzinfo=UTC)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=UTC)
        else:
            end = datetime(year, month + 1, 1, tzinfo=UTC)
        cur = self.cnx.execute(
            f"{_select} WHERE date >= ? AND date < ? ORDER BY date ASC;",
            (int(start.timestamp()), int(end.timestamp())),
        )
        return [dict(zip(_fields, r, strict=True)) for r in cur]

    def available_months(self) -> list[tuple[int, int]]:
        """Distinct (year, month) pairs present in the cache, for populating
        a year/month picker without scanning every row from the UI layer."""
        cur = self.cnx.execute("SELECT DISTINCT date FROM lean_photo ORDER BY date ASC;")
        months = set()
        for (ts,) in cur:
            d = datetime.fromtimestamp(ts, tz=UTC)
            months.add((d.year, d.month))
        return sorted(months)

    def count(self) -> int:
        cur = self.cnx.execute("SELECT COUNT(*) FROM lean_photo;")
        return cur.fetchone()[0]

    def sync(self, client, page_limit: int = 5000) -> int:
        """Pull lean rows from ``client`` (any ``AbstractPDBClient``,
        duck-typed via ``sync_since``) since our last sync cursor, paging
        through results until caught up. Returns the number of rows synced.
        """
        since = self.last_synced()
        total = 0
        while True:
            result = client.sync_since(since, limit=page_limit)
            photos = result.get("photos", [])
            if photos:
                self.upsert_many(photos)
                total += len(photos)
            next_since = result.get("next_since")
            if next_since is None or next_since == since or len(photos) < page_limit:
                since = next_since if next_since is not None else since
                break
            since = next_since
        if since is not None:
            self.set_last_synced(since)
        return total

    def close(self) -> None:
        self.cnx.close()


__all__ = ["LeanCache"]
