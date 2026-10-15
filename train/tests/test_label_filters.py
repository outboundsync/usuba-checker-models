import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "v3data"))
import label_filters as F

def D(sha, shas): return dict(sha=sha, findings=[{"_sha": s} for s in shas])
SH1, SH2 = "a" * 40, "b" * 40

def test_attribution_requires_row_commit_equal_to_majority_reviewed_sha():
    strict = F.lower_keys({"https://github.com/Own/Name": D(SH1, [SH1, SH1, SH2])})
    assert F.attribution(strict, "hancore_concrete:own/name:" + SH1[:10], SH1) == (True, None)
    assert F.attribution(strict, "hancore_concrete:own/name:" + SH2[:10], SH2)[1] == "attribution:row_commit_is_not_the_reviewed_sha"
    assert F.attribution(strict, "hancore_concrete:other/x:aaaaaaaaaa", SH1)[1] == "attribution:plugin_not_in_strict_reviews"
    assert F.attribution(F.lower_keys({"https://github.com/o/n": D(None, [])}), "hancore_concrete:o/n:x", SH1)[1] == "attribution:no_reviewed_sha"

def test_findings_spread_over_commits_have_no_attribution():
    strict = {"https://github.com/o/n": D(SH1, [SH1, SH2, "c" * 40, "d" * 40])}
    assert F.attribution(strict, "hancore_concrete:o/n:" + SH1[:10], SH1)[1] == "attribution:no_majority_sha_among_findings"

def test_retraction_ids_whole_and_partial():
    L = [dict(row="r1", retracted=True), dict(row="r2", retracted=False, retracted_partial=True), dict(row="r3", retracted=False, retracted_partial=False)]
    assert F.retraction_ids(L) == {"r1", "r2"}

def test_synthetic_and_template_tells():
    assert F.synthetic_reason(dict(source="synthetic_lifecycle", id="x")) == "synthetic_row"
    assert F.synthetic_reason(dict(source="x", id="syn.a")) == "synthetic_row" and F.synthetic_reason(dict(source="x", id="a:b", provenance={})) is None
    rows = [dict(verdict="approve", messages=[{"content": '{"id": "sample.x"}'}, {"content": ""}]), dict(verdict="approve", messages=[{"content": '{"id": "real.x"}'}, {"content": ""}])]
    assert F.template_id_fraction(rows)["approve"]["share"] == 0.5

def test_real_strict_loader_matches_filter_contract(tmp_path, monkeypatch):
    import json, importlib.util
    root = os.environ.get("USUBA_CHECKER_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", "usuba-checker-scripts")
    p = os.path.join(root, "hancore", "common.py")
    if not os.path.exists(p): import pytest; pytest.skip("scripts checkout not found")
    spec = importlib.util.spec_from_file_location("hc_common", p); C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
    rev = tmp_path / "r.jsonl"; plug = "https://github.com/Own/Name"
    def it(d, text, typ="finding"): return dict(thread_repo="omacom/omarchy-plugin-marketplace", plugin=plug, date=d, item_type=typ, text=text, categories=["x"], labels=[])
    rows = [it("2026-01-01", f"reviewed {SH1} blocker"), it("2026-01-02", f"Fixed in {SH2}: the thing"), it("2026-01-03", "another issue at same commit")]
    rev.write_text("\n".join(json.dumps(r) for r in rows)); monkeypatch.setattr(C, "REV", str(rev))
    strict = F.lower_keys(C.load(strict_sha=True)); d = strict[plug.lower()]
    assert d["sha"] == SH1                                         # the "Fixed in <sha>" sentence does not become the reviewed commit
    assert F.attribution(strict, "hancore_concrete:own/name:" + SH1[:10], SH1)[0]
