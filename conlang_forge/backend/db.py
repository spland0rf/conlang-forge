"""A small database layer over DB-API connections.

SQL is written once with `?` placeholders; the layer rewrites them for PostgreSQL (`%s`). SQLite is used for
tests and local development; `Database.postgres(dsn)` connects psycopg when it is installed. Writes run in an
explicit transaction (`with db.tx() as t:`), which is what makes the quota reservation atomic.
"""
from __future__ import annotations

import os
import queue
import sqlite3
import threading
import time
from contextlib import contextmanager
from decimal import Decimal

from .schema import MIGRATIONS


class Tx:
    def __init__(self, conn, paramstyle):
        self.conn, self.ps = conn, paramstyle

    def _sql(self, sql):
        # PostgreSQL drivers use %s placeholders and treat a bare % as special, so literal percent signs are doubled
        return sql.replace("%", "%%").replace("?", "%s") if self.ps == "format" else sql

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
        return default if r is None or r[0] is None else _plain(r[0])


def _plain(v):
    """PostgreSQL returns SUM() of integers as Decimal; hand back ordinary numbers like SQLite does."""
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    return v


def _row(cur, row):
    if isinstance(row, sqlite3.Row):
        return dict(row)
    return {d[0]: _plain(v) for d, v in zip(cur.description, row)}


class Database:
    def __init__(self, connect, paramstyle="qmark"):
        self._connect, self.paramstyle = connect, paramstyle
        self._local = threading.local()
        if paramstyle == "format":
            size = max(1, int(os.environ.get("CONLANG_DB_POOL", "8")))
            self._pool, self._slots = queue.LifoQueue(), threading.BoundedSemaphore(size)
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
    def postgres(cls, dsn: str):
        """PostgreSQL through psycopg 3 (`pip install "psycopg[binary]"`). Connections come from a small pool,
        opened in autocommit mode so that `tx()` controls transactions explicitly; a dropped connection (a database
        restart, an idle timeout) is replaced the next time it is needed."""
        try:
            import psycopg
        except ImportError as e:     # pragma: no cover
            raise RuntimeError('PostgreSQL support needs the psycopg driver: pip install "psycopg[binary]"') from e
        return cls(lambda: psycopg.connect(dsn, autocommit=True, connect_timeout=10), "format")

    # ---- connections and transactions
    # SQLite: one connection per thread (or one shared, locked connection for ":memory:").
    # PostgreSQL: a small pool, so many request threads never mean many database connections (hosted databases
    # allow only a few dozen). Size: CONLANG_DB_POOL (default 8) per app instance.
    def _checkout(self):
        if hasattr(self, "_shared"):
            return self._shared
        if self.paramstyle == "format":
            if not self._slots.acquire(timeout=30):
                raise RuntimeError("the database is busy: no free connection after 30 seconds")
            try:
                while True:
                    try:
                        conn, last = self._pool.get_nowait()
                    except queue.Empty:
                        return self._connect()
                    if getattr(conn, "closed", False):
                        continue
                    if time.monotonic() - last > 30:             # idle a while: a proxy or restart may have cut it
                        try:
                            conn.execute("SELECT 1")
                        except Exception:
                            self._discard(conn)
                            continue
                    return conn
            except BaseException:
                self._slots.release()
                raise
        c = getattr(self._local, "conn", None)
        if c is None:
            c = self._local.conn = self._connect()
        return c

    def _discard(self, conn):
        try:
            conn.close()
        except Exception:
            pass

    def _checkin(self, conn, broken=False):
        if self.paramstyle != "format" or hasattr(self, "_shared"):
            return
        if broken or getattr(conn, "closed", False):
            self._discard(conn)
        else:
            self._pool.put((conn, time.monotonic()))
        self._slots.release()

    def close(self):
        """Close pooled PostgreSQL connections (SQLite connections close with their threads)."""
        while self.paramstyle == "format" and not self._pool.empty():
            try:
                self._discard(self._pool.get_nowait()[0])
            except queue.Empty:
                break

    @contextmanager
    def tx(self):
        """A write transaction. Commits on success, rolls back on any exception."""
        lock = getattr(self, "_lock", None)
        if lock:
            lock.acquire()
        conn, broken = None, False
        try:
            conn = self._checkout()
            conn.execute("BEGIN IMMEDIATE" if self.paramstyle == "qmark" else "BEGIN")
            try:
                yield Tx(conn, self.paramstyle)
            except BaseException:
                try:
                    conn.execute("ROLLBACK")
                except Exception:       # the connection itself is gone: nothing to roll back
                    broken = True
                raise
            else:
                try:
                    conn.execute("COMMIT")
                except Exception:
                    broken = True
                    raise
        finally:
            if conn is not None:
                self._checkin(conn, broken)
            if lock:
                lock.release()

    @contextmanager
    def read(self):
        lock = getattr(self, "_lock", None)
        if lock:
            lock.acquire()
        conn, broken = None, False
        try:
            conn = self._checkout()
            try:
                yield Tx(conn, self.paramstyle)
            except Exception:
                broken = bool(getattr(conn, "closed", False))
                raise
        finally:
            if conn is not None:
                self._checkin(conn, broken)
            if lock:
                lock.release()

    # ---- migrations
    def migrate(self):
        with self.tx() as t:
            if self.paramstyle == "format":      # several app instances may start at once: one migrates, the rest wait
                t.execute("SELECT pg_advisory_xact_lock(727274)")
            t.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)")
            have = t.scalar("SELECT MAX(version) FROM schema_version", default=0)
            for version, statements in MIGRATIONS:
                if version > have:
                    for s in statements:
                        t.execute(s)
                    t.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
