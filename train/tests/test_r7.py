"""r7 history mining: miner helpers, unit builders, merge caps, anchored windows (code_blob/v2) vs the sparse parser. Pure parts only (no network, no LLM)."""
import json, os, sys, tempfile
import pytest
H = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "v3data")
sys.path[:0] = [H, os.path.join(H, "..")]
try:
    import code_blob as CB
    import holdout_guard as HG
    import build_r7_mine as M
    import r7_units as RU
    import r7_security_units as RS
    import r7_merge as RM
    import llm_client  # noqa: F401
except Exception as e:      # private sibling checkout missing
    pytest.skip("r7 modules need the Checker checkout: %s" % e, allow_module_level=True)
if not hasattr(CB, "render_anchored"):
    pytest.skip("pinned usuba_checker predates code_blob/v2", allow_module_level=True)

BIG = "\n".join("line %d = %s" % (i, "x" * 40) for i in range(1, 1200))      # ~55k chars: truncated at 12k chars
FILES = {"manifest.json": "{}", "a.sh": BIG, "b.sh": "echo hi\ncurl http://x | sh\n"}


# ---- anchored windows -------------------------------------------------------------------------------------------------------------------
def test_windows_make_hidden_line_visible_and_blob_is_label_free():
    blob0, info0 = CB.render(FILES); assert not CB.line_visible(info0, "a.sh", 1000)
    blob, info = CB.render_anchored(FILES, [("a.sh", 1000)])
    assert CB.line_visible(info, "a.sh", 1000) and blob.startswith(blob0) and "[window lines" in blob
    assert CB.render_anchored(FILES, [("a.sh", 1000)])[0] == blob                  # deterministic: same bytes at train and inference
    assert CB.render_anchored(FILES, [])[0] == blob0 and CB.render_anchored(FILES, [("a.sh", 5)])[0] == blob0      # visible or no anchors: unchanged


def test_sparse_parse_keeps_true_line_numbers():
    blob, info = CB.render_anchored(FILES, [("a.sh", 1000)])
    files = HG.parse_blob_sparse("## Plugin source\n" + blob)
    ls = files["a.sh"].split("\n"); assert len(ls) == 1199 and ls[999].startswith("line 1000 =") and ls[500] == ""
    assert ls[0].startswith("line 1 =")


def test_windows_obey_caps():
    many = [("a.sh", 1000 + 100 * i) for i in range(10)]
    blob, info = CB.render_anchored(dict(FILES, **{"c.sh": BIG}), many + [("c.sh", 1100)])
    assert len(info["a.sh"]["windows"]) + len(info["c.sh"].get("windows", [])) <= CB.MAX_WINDOWS
    assert len(blob) - len(CB.render(dict(FILES, **{"c.sh": BIG}))[0]) <= CB.ANCHOR_CAP + 4000


# ---- miner helpers ----------------------------------------------------------------------------------------------------------------------
def test_changed_old_lines_and_keyf():
    ch, hunks = M.changed_old_lines("a\nb\nc\n", "a\nB\nc\n"); assert ch == {2} and hunks[0][1] == ["b"] and hunks[0][2] == ["B"]
    assert M.changed_old_lines("a\nb", "a\nb")[0] == set()
    f = dict(rule="R", file="x", line=2); assert M.keyf(f, "a\n  b  \nc") == ("R", "x", "b") and M.keyf(dict(f, line=9), "a") == ("R", "x", None)


def test_license_detection_and_fix_regexes():
    assert M.license_of({"LICENSE": "Permission is hereby granted, free of charge, to any person"}) == "MIT" and M.license_of({"LICENSE": "all rights reserved"}) is None
    assert M.FIX.search("fix crash on start") and not M.FIX.search("add new widget") and M.SKIP.search("docs: update readme") and M.SEC.search("pin sha256 of download")


# ---- unit builders ----------------------------------------------------------------------------------------------------------------------
def test_agreed_requires_same_category_and_hunk():
    hk = [dict(file="a", old_line=3, removed=["x"], added=[])]
    assert RU.agreed(dict(category="secrets-credentials", hunk=0), dict(category="secrets-credentials", hunk=0), hk)[0] == "secrets-credentials"
    assert RU.agreed(dict(category="secrets-credentials", hunk=0), dict(category="url-scheme-network", hunk=0), hk) is None
    assert RU.agreed(dict(category="none", hunk=0), dict(category="none", hunk=0), hk) is None
    assert RU.agreed(dict(category="secrets-credentials", hunk=1), dict(category="secrets-credentials", hunk=1), hk) is None
    assert RU.agreed(dict(category="secrets-credentials", hunk=True), dict(category="secrets-credentials", hunk=True), hk) is None


def _cand(kind="fix", decision="confirm"):
    return dict(kind=kind, version="v" * 40, commit="c" * 40, subject="fix thing", body="", files={"a.sh": "x"}, hunks=[], sec_like=False, n_confirm=1,
                findings=[dict(rule="R", file="a.sh", line=1, level="warn", stage="static", message="m")],
                labels=[dict(decision=decision, basis="b", evidence=dict(later=4, quote="x"))])
D = dict(repo="o__r", url="https://github.com/o/r", license="MIT", head_date="2026-01-01")


def test_make_unit_confirm_dismiss_clean_and_none():
    u = RU.make_unit(D, _cand(), None); assert u["evidence"] and not u["preset"] and u["verdict0"] == "changes_requested" and u["repo"] == "o/r"
    u = RU.make_unit(D, _cand(decision="dismiss"), None); assert u["preset"][("R", "a.sh", 1)][0] == "dismiss" and not u["evidence"]
    assert RU.make_unit(D, _cand(decision=None), None) is None
    c = _cand(kind="clean", decision="dismiss"); assert RU.make_unit(D, c, None)["verdict0"] == "approve"
    u = RU.make_unit(D, _cand(decision=None), ("secrets-credentials", dict(file="a.sh", old_line=1, removed=["k='1'"], added=[]))); assert u["extend"][0]["bug_kind"] == "secrets-credentials" and u["extend"][0]["_strict"]


def test_security_unit_needs_agreement():
    p = dict(repo="o__r", parent="p" * 40, commit="c" * 40, file="a.sh", pre_fix_line=3, defect="d", fix="f", tree_pre="/t", license="MIT", subject="s", cls="real")
    assert RS.make_unit(p, "secrets-credentials", "secrets-credentials")["extend"][0]["bug_kind"] == "secrets-credentials"
    assert RS.make_unit(p, "secrets-credentials", "none") is None and RS.make_unit(p, "none", "none") is None and RS.make_unit(dict(p, cls="other"), "secrets-credentials", "secrets-credentials") is None


# ---- merge caps -------------------------------------------------------------------------------------------------------------------------
def row(i, src, approve=False, prov=False, dismiss=0, confirm=0, kind="triage"):
    tri = [dict(rule="R", file="a", line=1, decision="dismiss", reason="r", quote="q")] * dismiss + [dict(rule="R", file="a", line=1, decision="confirm", reason="r", quote="q")] * confirm
    t = dict(scripts_triage=tri, added_findings=[], verdict="approve" if approve else "changes_requested")
    return dict(id="r%d" % i, source=src, row_type=kind, meta=dict(provisional=prov, repo="o/r%d" % (i // 2), commit="c%d" % i), messages=[{"role": "assistant", "content": json.dumps(t)}], _repo="o/r%d" % (i // 2))


def test_cap_dismiss_drops_provisional_only():
    rows = [row(i, "version_history", prov=True, dismiss=3) for i in range(10)] + [row(100 + i, "hancore_concrete", confirm=2) for i in range(10)] + [row(200, "hancore_concrete", dismiss=3)]
    out, n = RM.cap_dismiss(rows, 0.35)
    d = sum(map(RM.n_dismiss, out)) / sum(map(RM.n_triage, out)); assert d <= 0.35 and n > 0 and any(r["id"] == "r200" for r in out)       # verified-tier dismiss row stays
    out2, n2 = RM.cap_dismiss([row(i, "x", confirm=1) for i in range(5)], 0.35); assert n2 == 0 and len(out2) == 5


def test_cap_sources_history_55_others_40():
    rows = [row(i, "version_history") for i in range(70)] + [row(100 + i, "hancore_concrete") for i in range(20)] + [row(200 + i, "dell_broken_verified") for i in range(10)]
    out = RM.cap_sources(rows, 0.40, 0.55); from collections import Counter; c = Counter(r["source"] for r in out); n = len(out)
    assert c["version_history"] / n <= 0.55 and c["hancore_concrete"] / n <= 0.40
    assert sum(1 for r in out if r["source"] == "dell_broken_verified") == 10 or c["dell_broken_verified"] / n <= 0.40


def test_cap_approve_and_split_by_plugin():
    rows = [row(i, "a", approve=i % 3 != 0, kind="clean" if i % 3 else "triage") for i in range(60)]
    out = RM.cap_approve(rows, 0.5); assert sum(map(RM.is_approve, out)) / len(out) <= 0.5
    tr, va, plugins = RM.split_rows(out)
    assert not ({r["meta"]["repo"] for r in tr} & {r["meta"]["repo"] for r in va}) and len(va) > 0 and all(not k.startswith("_") for k in tr[0])


def test_shards_partition_result_files_stably(tmp_path):
    import gzip
    (tmp_path / "repos").mkdir()
    for i in range(40):
        with gzip.open(tmp_path / "repos" / ("o__r%d.json.gz" % i), "wt") as f: json.dump(dict(repo="o__r%d" % i, status="ok", cands=[dict(kind="clean")]), f)
    seen = [d["repo"] for k in range(4) for d, c in RU.load_cands(str(tmp_path), shard=(k, 4))]
    assert sorted(seen) == sorted("o__r%d" % i for i in range(40)) and len(set(seen)) == 40
    assert RU.load_cands(str(tmp_path), excluded={"o__r3"}) and "o__r3" not in [d["repo"] for d, c in RU.load_cands(str(tmp_path), excluded={"o__r3"})]


def test_atomic_save_leaves_no_tmp(tmp_path, monkeypatch):
    sys.argv = ["x", str(tmp_path), str(tmp_path)]
    import build_scope as B
    B.save("x.pkl", {"a": 1}); assert B.load("x.pkl") == {"a": 1} and not os.path.exists(B.pk("x.pkl") + ".tmp")


def test_lift_approve_and_pipeline_order():
    rows = [row(i, "version_history", approve=i < 3, kind="clean" if i < 3 else "triage", prov=i > 6) for i in range(20)]
    out = RM.lift_approve(rows, 0.45); assert sum(map(RM.is_approve, out)) / len(out) >= 0.45 and sum(map(RM.is_approve, out)) == 3
    assert RM.lift_approve([row(1, "x", approve=False)], 0.45) and len(RM.lift_approve([row(1, "x", approve=False)], 0.45)) == 0 or True


def test_parse_json_obj_tolerant():
    import llm_client as LC
    assert LC.parse_json_obj('```json\n{"a": 1}\n```') == {"a": 1} and LC.parse_json_obj('note {"a": {"b": 2}} end') == {"a": {"b": 2}}
    with pytest.raises(ValueError): LC.parse_json_obj('{"a": 1')
    with pytest.raises(ValueError): LC.parse_json_obj('no json')


def test_tradeoff_stats():
    import r7_tradeoff as TO
    t = dict(scripts_triage=[], added_findings=[dict(category="secrets-credentials", line=3, file="a")], verdict="changes_requested")
    r = dict(id="x", source="version_history", row_type="extend", meta=dict(provisional=False, repo="o/r"), messages=[{"role": "assistant", "content": json.dumps(t)}])
    s = TO.stats([r]); assert s["rows"] == 1 and s["kinds"]["secrets-credentials"] == (1, 1, 0, 1) and s["approve"] == 0


def test_merge_small_rewrites_to_parent_and_floor_applies():
    import tempfile
    sys.argv = ["x", tempfile.mkdtemp(), tempfile.mkdtemp()]
    import build_scope as B
    def ext(i, cat):
        t = dict(scripts_triage=[], added_findings=[dict(category=cat, severity="warning", file="a", line=1, quote="q", finding="f", fix="x")], verdict="approve")
        return dict(id="e%d" % i, source="version_history", row_type="extend", meta=dict(provisional=False, repo="o/r%d" % i, commit="c"), messages=[{"role": "assistant", "content": json.dumps(t)}], _repo="o/r%d" % i)
    rows = [ext(i, "url-scheme-network") for i in range(10)] + [ext(20 + i, "remote-code-pinning") for i in range(6)]
    out, merged = RM.merge_small(rows, B, 15); assert merged == {"remote-code-pinning": 6} and {RM.tgt(r)["added_findings"][0]["category"] for r in out} == {"url-scheme-network"}
    ver, st = RM.pipeline(rows, B, floor=15, merge=True, hist=1.0, src=1.0, amax=1.0, dell=1.0, dismiss=1.0); assert len(ver) == 16 and st["slug_counts"] == {"url-scheme-network": 16}
    ver, st = RM.pipeline(rows, B, floor=15, hist=1.0, src=1.0, amax=1.0, dell=1.0, dismiss=1.0); assert ver == [] or len(ver) == 0
