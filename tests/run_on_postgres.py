"""Run the test suites against a REAL PostgreSQL server, for machines where the psycopg driver cannot be installed.

    python tests/run_on_postgres.py [test_backend] [test_api] ...

Needs the `psql` client and a server. Set CONLANG_TEST_PG to the psql arguments that reach an empty scratch database,
for example:   CONLANG_TEST_PG="-h /tmp/pgsock -U postgres -d cf"

Every `Database.sqlite(...)` the tests ask for is replaced by a freshly emptied PostgreSQL schema, and a tiny stand-in for
psycopg talks to the server through one long-lived `psql` process per connection. Where psycopg is installed you do not need
this: point `Database.postgres` at a DSN and use the normal test runner.
"""
import json
import os
import re
import runpy
import shlex
import subprocess
import sys
import types
from pathlib import Path

ARGS = shlex.split(os.environ.get("CONLANG_TEST_PG", "-h /tmp/pgsock -U postgres -d cf"))
END = "@@END@@"


class Error(Exception):
    pass


def literal(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


class Cursor:
    def __init__(self, conn):
        self.conn, self.description, self.rowcount, self._rows = conn, None, -1, []

    def execute(self, sql, params=()):
        parts = iter(re.split(r"(%s|%%)", sql))
        ps, out = iter(params), []
        for piece in parts:
            out.append("%" if piece == "%%" else literal(next(ps)) if piece == "%s" else piece)
        text = "".join(out).strip().rstrip(";")
        head = text.split(None, 1)[0].upper() if text else ""
        if head in ("SELECT", "WITH"):
            raw = self.conn._run(f"SELECT COALESCE(json_agg(row_to_json(q)), '[]'::json) FROM ({text}) q")
            rows = json.loads(raw)
            self.description = [(k,) for k in rows[0]] if rows else []
            self._rows = [tuple(r.values()) for r in rows]
            self.rowcount = len(rows)
        elif head in ("INSERT", "UPDATE", "DELETE"):
            self.rowcount = int(self.conn._run(f"WITH r AS ({text} RETURNING 1) SELECT count(*) FROM r"))
            self._rows, self.description = [], None
        else:
            self.conn._run(text)
            self._rows, self.description, self.rowcount = [], None, -1
        return self

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows, self._rows = self._rows, []
        return rows


class Connection:
    closed = False

    def __init__(self):
        self.p = subprocess.Popen(["psql", "-X", "-q", "-A", "-t", *ARGS], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, bufsize=1)

    def _run(self, sql):
        self.p.stdin.write(sql + ";\n\\echo " + END + "\n")
        self.p.stdin.flush()
        lines = []
        while True:
            line = self.p.stdout.readline()
            if line == "":
                raise Error("psql exited")
            if line.rstrip("\n") == END:
                break
            lines.append(line.rstrip("\n"))
        for ln in lines:
            if ln.startswith("ERROR:") or ln.startswith("psql:") or ln.startswith("FATAL:"):
                raise Error(ln)
        return "\n".join(lines)

    def cursor(self):
        return Cursor(self)

    def execute(self, sql, params=()):
        return Cursor(self).execute(sql, params)

    def close(self):
        self.closed = True
        try:
            self.p.stdin.close()
            self.p.wait(timeout=5)
        except Exception:
            self.p.kill()


def install():
    stub = types.ModuleType("psycopg")
    stub.connect = lambda dsn, **kw: Connection()
    stub.Error = Error
    sys.modules["psycopg"] = stub
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from conlang_forge.backend.db import Database

    made = []

    def fresh(cls, path=":memory:"):
        for old in made:                       # each test builds a new Backend: free the connections of the last one
            old.close()
        made.clear()
        c = Connection()
        c._run("DROP SCHEMA public CASCADE")
        c._run("CREATE SCHEMA public")
        c.close()
        db = cls.postgres("shim")
        made.append(db)
        return db
    Database.sqlite = classmethod(fresh)


if __name__ == "__main__":
    install()
    sys.argv[0] = str(Path(__file__).with_name("run_without_pytest.py"))
    runpy.run_path(sys.argv[0], run_name="__main__")
