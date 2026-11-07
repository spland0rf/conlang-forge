"""The per-script generator config (scripts/script_analysis/script_config/<script>.json) is complete and the generator modules read their numbers from it."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for d in ("scripts/script_analysis", "scripts/script_analysis/compound_gen"): sys.path.insert(0, os.path.join(ROOT, d))
import script_config as SC


def test_devanagari_config_is_complete():
    cfg = SC.validate("devanagari")
    assert cfg["frame"]["bar_y"] < cfg["frame"]["desc_y"] < cfg["frame"]["base_y"]


def test_every_configured_path_exists_except_outputs():
    outputs = {"library_out"}
    for k, v in SC.get()["paths"].items():
        if k in outputs: continue
        for p in (v if isinstance(v, list) else [v]): assert os.path.exists(os.path.join(SC.ROOT, p)), (k, p)


def test_validate_flags_a_missing_rule():
    import pytest
    cfg = dict(SC.get("devanagari")); cfg["rules"] = {k: v for k, v in cfg["rules"].items() if k != "MAX_VOID"}
    SC._cache["broken"] = cfg
    with pytest.raises(ValueError, match="MAX_VOID"): SC.validate("broken")


def test_generator_reads_rules_from_config():
    import rules, compound_gen as C
    assert rules.R["BASE_Y"] == SC.get()["frame"]["base_y"] == C.BASE
    assert C.RECIPES["chain"][0] == SC.get()["recipes"]["chain"]["weight"]
