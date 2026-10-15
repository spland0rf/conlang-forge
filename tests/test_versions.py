"""Checkpoints of writing systems and languages: made only on request, read only, compressed, branchable."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_api import PW, make, signed_in  # noqa: E402

from conlang_forge.backend.versions import pack, unpack  # noqa: E402


def test_pack_round_trips_and_compresses():
    obj = {"a": ["x"] * 2000, "b": "ʃ"}
    digest, raw, text = pack(obj)
    assert unpack(text) == obj and len(text) < raw / 10 and pack(obj)[0] == digest
    assert pack({"b": "ʃ", "a": ["x"] * 2000})[0] == digest            # key order does not matter


def test_writing_system_checkpoints_are_only_made_on_request():
    be, c = make()
    signed_in(c, be)
    sid = c.post("/api/scripts", {"name": "Plain", "seed": 11, "pins": {"family": "curvy"}}).json()["script_record"]["id"]
    v = c.get(f"/api/scripts/{sid}/versions").json()
    assert v["versions"] == [] and v["working"] == 1 and not v["has_checkpoints"]
    c.put(f"/api/scripts/{sid}", {"pins": {"family": "boxy"}})                # editing never makes a checkpoint
    assert c.get(f"/api/scripts/{sid}/versions").json()["versions"] == []
    assert be.db.read().__enter__().scalar("SELECT COUNT(*) FROM versions", (), 0) == 0

    made = c.post(f"/api/scripts/{sid}/versions", {"label": "boxy start"})
    assert made.status_code == 200, made.text
    v = made.json()
    assert v["working"] == 2 and [x["n"] for x in v["versions"]] == [1] and v["versions"][0]["label"] == "boxy start"
    assert 0 < v["versions"][0]["stored_bytes"] < 12000                       # a few KB, not the 16 KB drawing
    again = c.post(f"/api/scripts/{sid}/versions", {})                        # nothing changed: nothing new to keep
    assert again.status_code == 409 and "version 1" in again.json()["message"]

    c.put(f"/api/scripts/{sid}", {"pins": {"family": "spikey"}, "name": "Plain 2"})
    assert c.post(f"/api/scripts/{sid}/versions", {}).json()["working"] == 3
    old = c.get(f"/api/scripts/{sid}/versions/1").json()
    assert old["read_only"] and old["pins"]["family"] == "boxy" and old["specimen"].startswith("<svg") and old["sample"].startswith("<svg")
    assert {"label": "Main style", "then": "boxy", "now": "spikey"} in old["changes_since"]
    assert any(x["label"] == "Name" for x in old["changes_since"])
    assert c.get(f"/api/scripts/{sid}/versions/9").status_code == 404


def test_new_version_from_an_old_one_is_an_identical_editable_copy():
    be, c = make()
    signed_in(c, be)
    sid = c.post("/api/scripts", {"name": "One", "seed": 21, "pins": {"family": "bubbly"}}).json()["script_record"]["id"]
    c.post(f"/api/scripts/{sid}/versions", {})
    c.put(f"/api/scripts/{sid}", {"pins": {"family": "boxy"}})
    r = c.post(f"/api/scripts/{sid}/versions/1/branch", {})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["kind"] == "script" and out["exact"] is True
    rec = out["item"]["script_record"]
    assert rec["id"] != sid and rec["pins"]["family"] == "bubbly" and rec["seed"] == 21 and rec["name"] == "One (from v1)"
    assert c.put(f"/api/scripts/{rec['id']}", {"name": "Edited"}).status_code == 200      # the copy is editable
    assert c.get(f"/api/scripts/{rec['id']}/versions").json()["branched_from"]["n"] == 1
    # the original keeps its working version and its checkpoint
    assert c.get(f"/api/scripts/{sid}").json()["script_record"]["pins"]["family"] == "boxy"
    assert [x["n"] for x in c.get(f"/api/scripts/{sid}/versions").json()["versions"]] == [1]


def test_checkpoints_are_private_and_go_with_the_item():
    be, c = make()
    signed_in(c, be)
    sid = c.post("/api/scripts", {"seed": 3}).json()["script_record"]["id"]
    c.post(f"/api/scripts/{sid}/versions", {})
    other = type(c)(c.app)
    other.token = other.post("/api/auth/register", {"email": "o@x.org", "password": PW}, token=None).json()["access_token"]
    assert other.get(f"/api/scripts/{sid}/versions").status_code in (403, 404)
    assert other.post(f"/api/scripts/{sid}/versions", {}).status_code in (403, 404)
    assert c.delete(f"/api/scripts/{sid}/versions/1").json()["versions"] == []
    c.post(f"/api/scripts/{sid}/versions", {})
    c.delete(f"/api/scripts/{sid}")
    with be.db.read() as t:
        assert t.scalar("SELECT COUNT(*) FROM versions", (), 0) == 0
    assert c.post(f"/api/scripts/{sid}/versions", {}).status_code == 404


def test_language_checkpoint_view_and_branch():
    be, c = make()
    signed_in(c, be)
    cid = c.post("/api/conlangs", {"name": "Zuro", "seed": 5}).json()["id"]
    assert c.get(f"/api/conlangs/{cid}/versions").json()["versions"] == []
    c.post(f"/api/conlangs/{cid}/settings/apply", {"set": {"syntax.word_order": "VSO"}})    # editing: still no checkpoint
    assert c.get(f"/api/conlangs/{cid}/versions").json()["versions"] == []
    v = c.post(f"/api/conlangs/{cid}/versions", {"label": "VSO"}).json()
    assert v["working"] == 2 and 20000 < v["versions"][0]["stored_bytes"] < 200000
    assert c.post(f"/api/conlangs/{cid}/versions", {}).status_code == 409
    c.post(f"/api/conlangs/{cid}/settings/apply", {"set": {"syntax.word_order": "SOV"}})
    d = c.get(f"/api/conlangs/{cid}/versions/1").json()
    assert d["read_only"] and d["words"] > 100 and d["name"] and d["consonants"] and d["vowels"]
    assert any(x["then"].startswith("VSO") and x["now"].startswith("SOV") for x in d["changes_since"])
    before = c.get(f"/api/conlangs/{cid}").json()
    b = c.post(f"/api/conlangs/{cid}/versions/1/branch", {"name": "Zuro old"})
    assert b.status_code == 200, b.text
    new = b.json()["item"]
    assert new["id"] != cid and new["name"] == "Zuro old"
    assert c.get(f"/api/conlangs/{new['id']}").json()["profile"]["grammar"]["word_order"] == "VSO"      # identical to v1
    assert c.get(f"/api/conlangs/{cid}").json()["profile"]["grammar"]["word_order"] == "SOV"          # original untouched
    assert c.get(f"/api/conlangs/{new['id']}/versions").json()["branched_from"]["n"] == 1
    assert c.delete(f"/api/conlangs/{new['id']}").status_code in (200, 204)
    assert before["id"] == cid
