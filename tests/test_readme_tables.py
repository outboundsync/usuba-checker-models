import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_readme_tables_match_result_files():
    g = _mod("gen_readme_tables")
    cur = open(os.path.join(ROOT, "README.md")).read()
    assert g.build(cur) == cur, "README results tables drifted from eval/hancore_holdout/results; run python3 tools/gen_readme_tables.py"


def test_every_rendered_number_comes_from_a_result_file():
    g = _mod("gen_readme_tables")
    d = g.load("usuba-9b-q4km")
    block = g.render()
    assert "%.3f" % d["verdict_accuracy"] in block and "%.3f" % d["negative_false_alarm"] in block


def test_usuba_v1_and_v2_rows_are_labelled_with_their_own_prompt():
    g = _mod("gen_readme_tables")
    block = g.render()
    v1 = next(ln for ln in block.splitlines() if "Usuba v1" in ln and ln.startswith("|"))
    v2 = next(ln for ln in block.splitlines() if "Usuba v2" in ln and ln.startswith("|"))
    assert "0.812" in v1 and "0.696" in v2 and "| v2 |" in v2
    assert "not** run on prompt v2 or v3" in block


def test_wilson_interval_sane():
    g = _mod("gen_readme_tables")
    lo, hi = g.wilson(27, 29)
    assert 0.77 < lo < 0.79 and 0.97 < hi < 0.99
    assert g.wilson(0, 0)[0] != g.wilson(0, 0)[0]   # nan


def test_result_files_are_consistent():
    g = _mod("gen_readme_tables")
    for f in sorted(os.listdir(g.RES)):
        if f.endswith(".json"):
            d = json.load(open(os.path.join(g.RES, f)))
            assert d["positives"] + d["negatives"] == d["n"], f
