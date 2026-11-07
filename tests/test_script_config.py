"""The per-script generator config (scripts/script_analysis/script_config/<script>.json) is complete, and the generators read the ACTIVE profile at call time
(so a profile can take its ingredients from different scripts)."""
import copy, os, sys
import pytest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for d in ("scripts/script_analysis", "scripts/script_analysis/compound_gen", "scripts/script_analysis/body_units"): sys.path.insert(0, os.path.join(ROOT, d))
import script_config as SC


@pytest.fixture
def fake_script():
    """A second 'script' with a different frame and rules, registered in memory only."""
    cfg = copy.deepcopy(SC.get("devanagari")); cfg["id"] = "fake"
    cfg["frame"].update({"bar_y": 10.0, "base_y": 90.0, "desc_y": 30.0}); cfg["rules"].update({"BAR_Y": 10.0, "BASE_Y": 90.0, "DESC_Y": 30.0, "MAX_VOID": 40.0})
    cfg["recipes"] = {"chain": {"weight": 1, "skeletons": ["stem"]}}
    SC._cache["fake"] = cfg
    yield "fake"
    SC._cache.pop("fake", None)


def test_devanagari_config_is_complete():
    cfg = SC.validate("devanagari")
    assert cfg["frame"]["bar_y"] < cfg["frame"]["desc_y"] < cfg["frame"]["base_y"]


def test_every_configured_path_exists_except_outputs():
    outputs = {"library_out"}
    for k, v in SC.get("devanagari")["paths"].items():
        if k in outputs: continue
        for p in (v if isinstance(v, list) else [v]): assert os.path.exists(os.path.join(SC.ROOT, p)), (k, p)


def test_validate_flags_a_missing_rule():
    cfg = copy.deepcopy(SC.get("devanagari")); cfg["rules"].pop("MAX_VOID"); SC._cache["broken"] = cfg
    try:
        with pytest.raises(ValueError, match="MAX_VOID"): SC.validate("broken")
    finally: SC._cache.pop("broken", None)


def test_generator_reads_rules_at_call_time(fake_script):
    import rules, compound_gen as C
    assert rules.R["BAR_Y"] == 20.0 and C.recipes()["chain"][1] == ("stem", "desc", "bar")
    with SC.use(fake_script):
        assert rules.R["BAR_Y"] == 10.0 and rules.R["MAX_VOID"] == 40.0 and C.recipes() == {"chain": (1, ("stem",))}
    assert rules.R["BAR_Y"] == 20.0 and rules.R["MAX_VOID"] == 47.0          # restored after the block


def test_profile_takes_each_ingredient_from_its_own_script(fake_script):
    import rules, compound_gen as C
    prof = SC.Profile({"rules": "devanagari", "frame": "devanagari", "skeleton": fake_script, "body": "devanagari", "modifier": "devanagari"})
    assert prof.scripts() == ["devanagari", "fake"]
    with SC.use(prof):
        assert rules.R["MAX_VOID"] == 47.0                      # rules from devanagari
        assert list(C.recipes()) == ["chain"]                   # skeleton mix from the fake script
        assert prof.path("units").endswith("body_units/units.json")


def test_body_vocabulary_is_tagged_with_its_source():
    import body_gen
    V = body_gen.vocab()
    assert V.script == "devanagari" and len(V.UNITS["line"]) > 0


def test_common_frame_mapping_round_trips(fake_script):
    prof = SC.Profile.of("devanagari")
    assert prof.to_common([(10, 20), (10, 88)]) == [(10.0, 20.0), (10.0, 88.0)]           # Devanagari's frame IS the common frame
    pts = [(12.0, 10.0), (40.0, 50.0), (70.0, 90.0)]
    c = prof.to_common(pts, fake_script)
    assert c[0][1] == 20.0 and c[-1][1] == 88.0                                            # bar -> common bar, baseline -> common baseline
    back = prof.from_common(c, fake_script)
    assert all(abs(a - b) < 1e-9 for p, q in zip(pts, back) for a, b in zip(p, q))


def test_library_entries_carry_their_source():
    import json
    doc = json.load(open(os.path.join(ROOT, "conlang_forge/script/forms/devanagari_library.json")))
    assert doc["script"] == "devanagari" and all(l["source"] == "devanagari" for l in doc["letters"])
