"""A small database layer over DB-API connections.

SQL is written once with `?` placeholders; the layer rewrites them for PostgreSQL (`%s`). SQLite is used for
tests and local development; `Database.postgres(dsn)` connects psycopg when it is installed. Writes run in an
explicit transaction (`with db.tx() as t:`), which is what makes the quota reservation atomic.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager

from .schema import MIGRATIONS


class Tx:
    def __init__(self, conn, paramstyle):
        self.conn, self.ps = conn, paramstyle

    def _sql(self, sql):
        return sql.replace("?", "%s") if self.ps == "format" else sql

    def execute(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(self._sql(sql), tuple(params))
        return cur

    def one(self, sql, params=()):
        cur = self.execute(sql, params)
        row = cur.fetchone()
        return _row(cur, row) if row is not None else None

    def all(self, sql, params=()):
        cur = self.execute(sql, params)
        return [_row(cur, r) for r in cur.fetchall()]

    def scalar(self, sql, params=(), default=None):
        cur = self.execute(sql, params)
        r = cur.fetchone()
        return default if r is None or r[0] is None else r[0]


def _row(cur, row):
    if isinstance(row, sqlite3.Row):
        return dict(row)
    return {d[0]: v for d, v in zip(cur.description, row)}


class Database:
    def __init__(self, connect, paramstyle="qmark"):
        self._connect, self.paramstyle = connect, paramstyle
        self._local = threading.local()
        self.migrate()

    # ---- constructors
    @classmethod
    def sqlite(cls, path: str = ":memory:"):
        if path == ":memory:":      # one shared connection, guarded by a lock
            conn = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
            conn.row_factory = sqlite3.Row
            db = cls.__new__(cls)
            db._shared, db._lock = conn, threading.RLock()
            db._connect, db.paramstyle, db._local = (lambda: conn), "qmark", threading.local()
            db.migrate()
            return db

        def connect():
            c = sqlite3.connect(path, timeout=30, isolation_level=None)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA foreign_keys=ON")
            return c
        return cls(connect, "qmark")

    @classmethod
    def postgres(cls, dsn: str):    # pragma: no cover - needs a server
        import psycopg
        return cls(lambda: psycopg.connect(dsn, autocommit=True), "format")

    # ---- connections and transactions
    def _conn(self):
        if hasattr(self, "_shared"):
            return self._shared
        c = getattr(self._local, "conn", None)
        if c is None:
            c = self._local.conn = self._connect()
        return c

    @contextmanager
    def tx(self):
        """A write transaction. Commits on success, rolls back on any exception."""
        lock = getattr(self, "_lock", None)
        if lock:
            lock.acquire()
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE" if self.paramstyle == "qmark" else "BEGIN")
            try:
                yield Tx(conn, self.paramstyle)
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")
        finally:
            if lock:
                lock.release()

    @contextmanager
    def read(self):
        lock = getattr(self, "_lock", None)
        if lock:
            lock.acquire()
        try:
            yield Tx(self._conn(), self.paramstyle)
        finally:
            if lock:
                lock.release()

    # ---- migrations
    def migrate(self):
        with self.tx() as t:
            t.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)")
            have = t.scalar("SELECT MAX(version) FROM schema_version", default=0)
            for version, statements in MIGRATIONS:
                if version > have:
                    for s in statements:
                        t.execute(s)
                    t.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
