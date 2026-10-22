"""Writing systems linked to conlangs: closest-fit sound matching, storage, the primary system, and rendering text."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_api import make, signed_in  # noqa: E402

from conlang_forge.script.sounds import closest, cdist, vdist  # noqa: E402
from conlang_forge.script.text import split_sentences, to_sounds, write_word  # noqa: E402

CONS = ["p", "t", "k", "m", "n", "s", "l", "r"]
VOWS = ["a", "i", "u"]


def test_closest_sound_is_the_same_sound_when_it_exists():
    assert closest("p", CONS, VOWS) == {"to": ["p"], "exact": True, "cost": 0.0, "how": "same sound"}
    assert closest("a", CONS, VOWS)["exact"]


def test_closest_consonant_follows_voicing_place_and_manner():
    assert closest("b", CONS, VOWS)["to"] == ["p"]            # voiced -> its voiceless twin
    assert closest("d", CONS, VOWS)["to"] == ["t"]
    assert closest("g", CONS, VOWS)["to"] == ["k"]
    assert closest("z", CONS, VOWS)["to"] == ["s"]
    assert closest("ŋ", CONS, VOWS)["to"] in (["n"], ["k"])   # a nasal or the same place
    assert closest("ʃ", CONS, VOWS)["to"] == ["s"]
    assert cdist("b", "p") < cdist("b", "t") < cdist("b", "s")


def test_closest_vowel_and_glides():
    assert closest("e", CONS, VOWS)["to"] == ["i"] or closest("e", CONS, VOWS)["to"] == ["a"]
    assert closest("o", CONS, VOWS)["to"] == ["u"]
    assert closest("y", CONS, VOWS)["to"] == ["i"]
    assert closest("j", CONS, VOWS)["to"] == ["i"] and closest("w", CONS, VOWS)["to"] == ["u"]   # glides become vowels
    assert vdist("e", "i") < vdist("e", "u")


def test_complex_consonants_become_their_parts_and_a_throat_stop_can_drop():
    m = closest("ts", CONS, VOWS)
    assert m["to"] == ["t", "s"] and not m["exact"]
    assert closest("kp", CONS, VOWS)["to"] == ["k", "p"]
    assert closest("ts", CONS + ["ts"], VOWS)["exact"]
    assert closest("ʔ", ["p", "b", "m"], VOWS)["to"] == []


def test_reading_spelling_into_sounds_and_sentences():
    rom = {"ʃ": "sh", "s": "s", "h": "h", "a": "a", "i": "i", "tʃ": "ch", "t": "t", "k": "k"}
    assert to_sounds("Shata", rom) == ["ʃ", "a", "t", "a"]
    assert to_sounds("chik", rom) == ["tʃ", "i", "k"]
    s = split_sentences("Ka ta, si. Hi 12?")
    assert [e for _, e in s] == ["stop", "question"] and ("c",) in s[0][0] and ("n", "12") in s[1][0]


def _lang_script_ids(c, cid):
    r = c.post(f"/api/conlangs/{cid}/scripts/primary", {})
    assert r.status_code == 200, r.text
    return r.json()


def test_primary_script_follows_the_language_and_renders_exactly():
    be, c = make()
    signed_in(c, be)
    cid = c.post("/api/conlangs", {"name": "Zuro", "seed": 5}).json()["id"]
    first = _lang_script_ids(c, cid)
    rec = first["script_record"]
    assert rec["primary"] and rec["conlang_id"] == cid and first["language"]["id"] == cid
    assert _lang_script_ids(c, cid)["script_record"]["id"] == rec["id"]            # asking again does not make another
    assert first["specimen"].startswith("<svg") and len(first["sentences"]) >= 3 and first["sentences"][0]["svg"].startswith("<svg")
    # the letters cover every consonant and vowel of the language
    lang = c.get(f"/api/conlangs/{cid}/dictionary.json").json()
    w = [e for e in lang["entries"] if e.get("form")][:6] if "entries" in lang else []
    text = " ".join(e["form"] for e in w) or "ka ta."
    r = c.post(f"/api/conlangs/{cid}/render", {"text": text + "."})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["primary"] and out["designed_for_this"] and out["approximations"] == []
    assert out["svg"].startswith("<svg") and "fill=\"#fff\"" in out["svg"] and out["svg"].count("<path") >= len(out["sentences"])
    assert out["coverage"]["exact"] == out["coverage"]["total"] and out["sentences"][0]["svg"].startswith("<svg")


def test_rendering_in_a_non_matching_script_uses_closest_sounds():
    be, c = make()
    signed_in(c, be)
    a = c.post("/api/conlangs", {"name": "A", "seed": 5}).json()["id"]
    b = c.post("/api/conlangs", {"name": "B", "seed": 6}).json()["id"]
    sa = _lang_script_ids(c, a)["script_record"]["id"]
    sb = _lang_script_ids(c, b)["script_record"]["id"]
    assert sa != sb
    sounds_b = be.scripts.sounds_of(be.accounts.authenticate(c.token), b)
    own_a = set(be.scripts.sounds_of(be.accounts.authenticate(c.token), a)["consonants"] + be.scripts.sounds_of(be.accounts.authenticate(c.token), a)["vowels"])
    missing = [p for p in sounds_b["consonants"] + sounds_b["vowels"] if p not in own_a]
    r = c.post(f"/api/conlangs/{b}/render", {"text": "tika mono sheli.", "script_id": sa})
    assert r.status_code == 200, r.text
    out = r.json()
    assert not out["designed_for_this"] and not out["primary"] and out["script_id"] == sa
    assert out["sentences"]
    assert {x["sound"] for x in out["coverage"]["approximate"]} == set(missing)
    for row in out["coverage"]["approximate"]:
        assert row["written_as"] is not None and row["how"]


def test_create_edit_primary_and_delete_scripts():
    be, c = make()
    signed_in(c, be)
    cid = c.post("/api/conlangs", {"name": "Zuro", "seed": 5}).json()["id"]
    r = c.post("/api/scripts", {"name": "Plain", "seed": 11, "pins": {"kind": "alphabet", "family": "curvy"}})
    assert r.status_code == 200, r.text
    sid = r.json()["script_record"]["id"]
    assert r.json()["spec"]["kind"] == "alphabet" and "language" not in r.json()
    # a standalone script cannot be a primary script until it is designed for the language
    assert c.put(f"/api/conlangs/{cid}/primary-script", {"script_id": sid}).status_code == 422
    e = c.put(f"/api/scripts/{sid}", {"conlang_id": cid, "pins": {"kind": "abugida", "family": "bubbly"}})
    assert e.status_code == 200, e.text
    assert e.json()["spec"]["kind"] == "abugida" and e.json()["language"]["id"] == cid
    assert c.put(f"/api/conlangs/{cid}/primary-script", {"script_id": sid}).json()["script_record"]["primary"]
    listing = c.get(f"/api/conlangs/{cid}/scripts").json()
    assert listing["primary_id"] == sid and [s["id"] for s in listing["scripts"]] == [sid]
    # bad input is refused
    assert c.post("/api/scripts", {"seed": 1, "pins": {"nope": 1}}).status_code == 422
    assert c.put(f"/api/scripts/{sid}", {"seed": -4}).status_code == 422
    assert c.post("/api/scripts/preview", {"seed": 3, "conlang_id": cid}).json()["sentences"]
    assert c.delete(f"/api/scripts/{sid}").status_code == 200
    assert c.get(f"/api/scripts/{sid}").status_code == 404
    assert c.get(f"/api/conlangs/{cid}/scripts").json()["primary_id"] is None
    # asking for the primary again designs a new one
    assert _lang_script_ids(c, cid)["script_record"]["primary"]


def test_scripts_are_private_to_their_owner():
    be, c = make()
    signed_in(c, be)
    cid = c.post("/api/conlangs", {"name": "Zuro", "seed": 5}).json()["id"]
    sid = c.post("/api/scripts", {"seed": 2}).json()["script_record"]["id"]
    from asgi_client import Client
    d = Client(c.app)
    signed_in(d, be, "other@x.org")
    assert d.get(f"/api/scripts/{sid}").status_code in (403, 404)
    assert d.put(f"/api/scripts/{sid}", {"name": "mine"}).status_code in (403, 404)
    assert d.post(f"/api/conlangs/{cid}/render", {"text": "ka."}).status_code in (403, 404)
    assert d.get("/api/scripts").json()["scripts"] == []


def test_list_shows_one_stored_line_of_sample_text_per_system():
    be, c = make()
    signed_in(c, be)
    sid = c.post("/api/scripts", {"name": "A", "seed": 21, "pins": {"kind": "alphabet", "family": "curvy"}}).json()["script_record"]["id"]
    row = c.get("/api/scripts").json()["scripts"][0]
    assert row["preview"].startswith("<svg") and "currentColor" in row["preview"] and 'fill="#fff"' not in row["preview"]    # saved when it was made
    first = row["preview"]
    c.put(f"/api/scripts/{sid}", {"name": "renamed"})                                                          # same recipe: same picture, no redraw needed
    assert c.get("/api/scripts").json()["scripts"][0]["preview"] == first
    c.put(f"/api/scripts/{sid}", {"seed": 22})                                                                 # a new recipe: a new line
    new = c.get("/api/scripts").json()["scripts"][0]["preview"]
    assert new and new != first
    # a system saved before the column existed has no line until it is asked for
    with be.db.tx() as t:
        t.execute("UPDATE writing_systems SET preview_svg = NULL, preview_key = NULL WHERE id = ?", (sid,))
    assert c.get("/api/scripts").json()["scripts"][0]["preview"] is None
    got = c.get(f"/api/scripts/{sid}/line").json()
    assert got["preview"] == new and c.get("/api/scripts").json()["scripts"][0]["preview"] == new
    assert c.get("/api/scripts/nope/line").status_code == 404
