"""Debug mode: an account flag (always on for administrators) that unlocks the settings export."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pytest  # noqa: E402

from conlang_forge.backend.errors import PermissionDenied  # noqa: E402
from test_api import PW, admin_client, make, signed_in  # noqa: E402


def test_debug_flag_is_on_for_admins_and_set_per_user_by_an_admin():
    be, c = make()
    me = signed_in(c, be)["user"]
    assert me["debug"] is False and me["debug_mode"] == 0
    adm = admin_client(be, c)
    assert adm.get("/api/me").json()["debug"] is True                       # administrators always have it
    r = adm.patch(f"/api/admin/users/{me['id']}", {"debug_mode": True})
    assert r.status_code == 200 and r.json()["debug"] is True and r.json()["debug_mode"] == 1
    assert c.get("/api/me").json()["debug"] is True
    assert adm.patch(f"/api/admin/users/{me['id']}", {"debug_mode": False}).json()["debug"] is False
    assert c.patch(f"/api/admin/users/{me['id']}", {"debug_mode": True}).status_code == 403    # users cannot grant it


def test_settings_export_needs_debug_and_rebuilds_the_same_language():
    be, c = make()
    me = signed_in(c, be)["user"]
    cid = c.post("/api/conlangs", {"name": "Ekki", "seed": 7, "pins": {}}).json()["id"]
    assert c.post(f"/api/conlangs/{cid}/settings/apply", {"set": {"phonology.max_cluster": 2}}).status_code == 200
    assert c.get(f"/api/conlangs/{cid}/debug/settings").status_code == 403
    adm = admin_client(be, c)
    adm.patch(f"/api/admin/users/{me['id']}", {"debug_mode": True})
    d = c.get(f"/api/conlangs/{cid}/debug/settings")
    assert d.status_code == 200
    d = d.json()
    assert d["format"] == "conlang-forge-debug/1" and d["language"]["seed"] == 7 and d["language"]["name"] == "Ekki"
    assert d["rebuild_from"]["seed"] == 7 and d["rebuild_from"]["pins"]["phonology.max_cluster"] == 2
    assert "phonology" in d["stored_spec"]
    from conlang_forge import settings_schema as S
    again = S.build_spec(d["rebuild_from"]["seed"], d["rebuild_from"]["pins"], d["rebuild_from"]["tuning"])
    assert again.phonology.syllable_templates == d["stored_spec"]["phonology"]["syllable_templates"]


def test_debug_does_not_open_other_peoples_languages():
    be, c = make()
    signed_in(c, be)
    cid = c.post("/api/conlangs", {"name": "Mine", "seed": 3}).json()["id"]
    from asgi_client import Client
    other = Client(c.app)
    other.token = other.post("/api/auth/register", {"email": "o@x.org", "password": PW}, token=None).json()["access_token"]
    adm = admin_client(be, c)
    uid = other.get("/api/me").json()["id"]
    adm.patch(f"/api/admin/users/{uid}", {"debug_mode": True})
    assert other.get(f"/api/conlangs/{cid}/debug/settings").status_code in (403, 404)
