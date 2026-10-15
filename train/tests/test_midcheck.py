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
    assert M.score_one(r, resp("run.sh", 20))["line_hit"]                 # basename match
    assert not M.score_one(r, resp("other.sh", 20))["file_hit"]
    assert not M.score_one(r, "not json")["json_ok"]
    assert M.score_one(r, "<think>x</think>" + resp("bin/run.sh", 20))["line_hit"]

def test_pool_excludes_dell_and_holdout():
    rows = [row("hancore_concrete:good/plugin:1"), row("dell_x:foo", src="dell_broken_verified"), row("hancore_concrete:bad/hold:2"),
            row("hancore_concrete:key/id:3"), dict(row("nofl"), messages=[{"role": "assistant", "content": json.dumps(dict(verdict="approve", findings=[]))}])]
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    pool, skipped = M.build_pool(f.name, 30, forbidden_ids={"key/id"}, holdout={"bad/hold"})
    assert [r["id"] for r in pool] == ["hancore_concrete:good/plugin:1"]
    assert skipped == {"dell_source": 1, "holdout_plugin": 1, "dell_key_id": 1, "no_file_line_gold": 1}

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
