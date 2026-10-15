"""No-GPU unit tests for train/midcheck.py. Run: python3 -m pytest train/tests/test_midcheck.py -q (pure python, no torch)."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import midcheck as M

def row(i, src="hancore_concrete", file="bin/run.sh", line=20, verdict="changes_requested"):
    tgt = dict(verdict=verdict, load="unsure", findings=[dict(category="privileged-system", severity="blocker", file=file, line=line, finding="x")])
    return dict(id=i, split="val", source=src, messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}, {"role": "assistant", "content": json.dumps(tgt)}])

def resp(file, line, verdict="changes_requested"):
    return json.dumps(dict(verdict=verdict, findings=[dict(file=file, line=line, finding="y")]))

def test_scoring():
    r = row("a")
    assert M.score_one(r, resp("bin/run.sh", 21))["line_hit"]            # within tolerance
    s = M.score_one(r, resp("bin/run.sh", 90)); assert s["file_hit"] and not s["line_hit"]
    assert not M.score_one(r, resp("run.sh", 20))["file_hit"]              # exact path only: no basename fallback (audit A10)
    assert M.score_one(dict(r, messages=row("a", file=".github/x")["messages"]), resp("./.github/x", 20))["line_hit"]   # './' prefix stripped, '.github' not mangled
    assert not M.score_one(r, resp("other.sh", 20))["file_hit"]
    assert not M.score_one(r, "not json")["json_ok"]
    assert M.score_one(r, "<think>x</think>" + resp("bin/run.sh", 20))["line_hit"]

def test_pool_excludes_dell_and_holdout():
    rows = [row("hancore_concrete:good/plugin:1"), row("dell_x:foo", src="dell_broken_verified"), row("hancore_concrete:bad/hold:2"),
            row("hancore_concrete:key/id:3"), dict(row("nofl"), messages=[{"role": "assistant", "content": json.dumps(dict(verdict="approve", findings=[]))}])]
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    pool, skipped = M.build_pool(f.name, 30, forbidden_ids={"key/id"}, holdout={"bad/hold"})
    assert sorted(r["id"] for r in pool) == ["hancore_concrete:good/plugin:1", "nofl"]     # negatives are part of the pool now
    assert skipped == {"dell_source": 1, "holdout_plugin": 1, "dell_key_id": 1}


def test_run_writes_and_never_raises():
    rows = [row("a"), row("b", line=50)]
    def gen(msgs): return resp("bin/run.sh", 20)
    with tempfile.TemporaryDirectory() as d, open(os.path.join(d, "log.jsonl"), "w") as log:
        s = M.run_midcheck(100, rows, gen, d, log=log)
        assert s["n"] == 2 and s["line_hit"] == 0.5 and s["file_hit"] == 1.0
        assert os.path.exists(os.path.join(d, "midcheck.jsonl")) and os.path.exists(os.path.join(d, "midcheck_step-100.json"))
        def boom(msgs): raise RuntimeError("cuda oom")
        s2 = M.run_midcheck(200, rows, boom, d, log=log); assert s2["line_hit"] == 0.0   # generation failure is scored, not raised
        assert M.run_midcheck(300, rows, gen, "/proc/forbidden/x") is None               # unwritable dir -> None, no exception


def test_invalid_output_is_wrong_for_both_classes_and_negatives_are_scored():
    neg = row("n", verdict="approve"); neg["messages"][-1]["content"] = json.dumps(dict(verdict="approve", load="works", findings=[]))
    assert M.score_one(neg, "garbage")["verdict_ok"] is False                  # an unparseable answer is not an approval
    assert M.score_one(neg, json.dumps(dict(verdict="maybe", findings=[])))["verdict_ok"] is False
    assert M.score_one(neg, json.dumps(dict(verdict="approve", findings=[])))["verdict_ok"] is True
    pos = row("p")
    s = M.summarize([M.score_one(pos, resp("bin/run.sh", 20)), M.score_one(neg, "garbage"), M.score_one(neg, json.dumps(dict(verdict="approve", findings=[])))])
    assert s["n_neg"] == 2 and s["neg_verdict_ok"] == 0.5 and s["n_invalid"] == 1 and s["selection_score"] == 0.75


def test_pool_is_stratified_and_seeded():
    rows = [row(f"p{i}") for i in range(20)] + [dict(row(f"n{i}", verdict="approve"), messages=[{"role": "assistant", "content": json.dumps(dict(verdict="approve", findings=[]))}]) for i in range(20)]
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    a, _ = M.build_pool(f.name, 10, forbidden_ids=set(), holdout=set(), seed=1); b, _ = M.build_pool(f.name, 10, forbidden_ids=set(), holdout=set(), seed=1)
    assert [r["id"] for r in a] == [r["id"] for r in b] and sum(r["id"].startswith("n") for r in a) == 5 and len(a) == 10
