import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import pytest
import judge_panel as jp

ITEMS = [
    dict(id="a", kind="S1", plugin="p", rule="USB-HC10", claim="c", context="x"),
    dict(id="b", kind="S2", plugin="q", context="y"),
    dict(id="c", kind="S3", plugin="r", context="z"),
]


def fake_call(table):
    def call(model, prompt, key):
        lab = table[model]
        if "Labels: S2" in prompt:
            pass
        if "CLEAN set" in prompt:
            lab = {"real": "clean", "false_alarm": "not_clean"}.get(lab, lab)
        if lab == "boom":
            raise OSError("boom")
        return json.dumps(dict(label=lab, confidence=0.9, reason="r")), 0.01, "stop"

    return call


def test_refuses_banned_models():
    for bad in (
        ["anthropic/claude-x", "openai/gpt-oss-120b", "qwen/q"],
        ["openai/gpt-5", "qwen/q", "deepseek/d"],
        ["qwen/a", "qwen/b", "deepseek/d"],
        ["foo/bar", "qwen/q", "deepseek/d"],
    ):
        with pytest.raises(SystemExit):
            jp.check_models(bad)
    jp.check_models(jp.DEFAULT_PANEL)


def test_majority_and_flags():
    with tempfile.TemporaryDirectory() as d:
        table = {"qwen/qwen3.5-397b-a17b": "real", "openai/gpt-oss-120b": "real", "deepseek/deepseek-v3.2": "false_alarm"}
        recs, s = jp.run(ITEMS, jp.DEFAULT_PANEL, d, 8, 2, "k", fake_call(table))
        r = {x["id"]: x for x in recs}
        assert r["a"]["majority"] == "real" and r["a"]["needs_human"] and not r["a"]["unanimous"] and r["a"]["provisional"]
        assert r["b"]["majority"] == "clean"
        assert s["by_kind"]["S1"]["unanimous_rate"] == 0.0 and s["provisional"]
        assert os.path.getsize(os.path.join(d, "review_queue.jsonl")) > 0


def test_failed_call_is_abstain_not_vote():
    with tempfile.TemporaryDirectory() as d:
        table = {"qwen/qwen3.5-397b-a17b": "real", "openai/gpt-oss-120b": "real", "deepseek/deepseek-v3.2": "boom"}
        jp.time.sleep = lambda *_: None
        recs, _ = jp.run(ITEMS[:1], jp.DEFAULT_PANEL, d, 8, 1, "k", fake_call(table))
        assert recs[0]["n_valid"] == 2 and "missing_vote" in recs[0]["review_reasons"] and not recs[0]["unanimous"]


def test_budget_cap_stops_calls():
    with tempfile.TemporaryDirectory() as d:
        table = {m: "real" for m in jp.DEFAULT_PANEL}
        recs, s = jp.run(ITEMS, jp.DEFAULT_PANEL, d, 0.0, 1, "k", fake_call(table))
        assert s["calls"] == 0 and all(r["n_valid"] == 0 and r["needs_human"] for r in recs)


def test_kappa_perfect_and_chance():
    labs = ("real", "false_alarm", "unsure")
    rows = [jp.collections.Counter({"real": 3}), jp.collections.Counter({"false_alarm": 3})]
    assert jp.fleiss_kappa(rows, labs) == 1.0
    po, k, n = jp.cohen_kappa(["real", "false_alarm"], ["real", "false_alarm"], labs)
    assert po == 1.0 and k == 1.0 and n == 2


def test_parse_vote():
    assert jp.parse_vote('x {"label":"Not-Clean","confidence":2} y', "S2")[:2] == ("not_clean", 1.0)
    assert jp.parse_vote('{"label":"real"}', "S2") is None and jp.parse_vote("", "S1") is None
