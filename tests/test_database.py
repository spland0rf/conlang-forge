"""Database-layer behaviour that matters most when the database is PostgreSQL (these also pass on SQLite).
Run on PostgreSQL with:  python tests/run_on_postgres.py test_database"""
import threading
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conlang_forge.backend.clock import FakeClock
from conlang_forge.backend.db import Database
from conlang_forge.backend.errors import QuotaExceeded
from conlang_forge.backend.limits import Limits
from conlang_forge.backend.quota import QuotaService


def _db():
    return Database.sqlite(":memory:")


def test_sums_come_back_as_plain_numbers_and_percent_signs_are_safe():
    db = _db()
    with db.tx() as t:
        t.execute("CREATE TABLE nums (a BIGINT, name TEXT)")
        t.execute("INSERT INTO nums VALUES (?, ?)", (3, "100% sure"))
        t.execute("INSERT INTO nums VALUES (?, ?)", (4, "50%"))
    with db.read() as t:
        total = t.scalar("SELECT SUM(a) FROM nums")
        row = t.one("SELECT SUM(a) AS s, COUNT(*) AS n FROM nums")
        hits = t.all("SELECT name FROM nums WHERE name LIKE '%0%' ORDER BY a")
    assert total == 7 and type(total) is int and type(row["s"]) is int and row["n"] == 2
    assert [h["name"] for h in hits] == ["100% sure", "50%"]


def test_a_failed_transaction_leaves_nothing_behind():
    db = _db()
    with db.tx() as t:
        t.execute("CREATE TABLE kv (k TEXT PRIMARY KEY, v INTEGER)")
        t.execute("INSERT INTO kv VALUES ('a', 1)")
    try:
        with db.tx() as t:
            t.execute("INSERT INTO kv VALUES ('b', 2)")
            t.execute("INSERT INTO kv VALUES ('a', 3)")        # duplicate key
    except Exception:
        pass
    with db.read() as t:
        assert t.scalar("SELECT COUNT(*) FROM kv") == 1
    with db.tx() as t:                                           # and the connection is still usable
        t.execute("INSERT INTO kv VALUES ('c', 4)")


def test_concurrent_reservations_never_exceed_the_allowance():
    db, clock = _db(), FakeClock()
    q = QuotaService(db, clock)
    limits = Limits(tokens_per_day=1000, tokens_per_month=10_000, requests_per_minute=None)
    won, lost, lock = [], [], threading.Lock()

    def worker():
        for _ in range(5):
            try:
                r = q.reserve("u1", 100, limits)
                with lock:
                    won.append(r)
            except QuotaExceeded:
                with lock:
                    lost.append(1)
    threads = [threading.Thread(target=worker) for _ in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(won) == 10 and len(lost) == 20, (len(won), len(lost))      # 30 attempts, room for exactly 10
    for r in won[:4]:
        q.release(r)
    assert q.reserve("u1", 100, limits)
