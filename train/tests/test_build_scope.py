"""build_scope helpers (pure parts): evidence matching, file-level location, Dell/approve caps. Skipped without the private Checker checkout."""
import json, os, sys, tempfile
import pytest
H = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "v3data")
try:
    sys.path.insert(0, H)
    _old = sys.argv; sys.argv = ["x", tempfile.mkdtemp(), tempfile.mkdtemp()]
    import build_scope as B
    sys.argv = _old
except Exception as e:      # private sibling checkout missing
    pytest.skip("build_scope needs the Checker checkout: %s" % e, allow_module_level=True)


def f(rule="USB-W01", file="a.sh", line=0, level="warn"): return dict(rule=rule, file=file, line=line, message="runs `foo`, not stock", stage="static", level=level)


def test_match_ev_line_window():
    ev = [dict(file="a.sh", line=10)]
    assert B.match_ev(f(line=12), ev, False) and not B.match_ev(f(line=20), ev, False) and not B.match_ev(f(file="b.sh", line=10), ev, False)


def test_locate_token_and_comment_skip():
    files = {"a.sh": "# foo is great\nset -e\nfoo --run\n"}
    assert B.locate(f(), files) == 3 and B.locate(f(line=7), files) == 7


def test_cap_dell_share_and_approve():
    def row(src, verdict):
        return dict(source=src, id=src + verdict + str(id(object())), meta=dict(provisional=False), messages=[0, 0, dict(content=json.dumps(dict(verdict=verdict)))])
    non = [row("hancore_concrete", "approve")] * 3 + [row("hancore_concrete", "changes_requested")] * 7
    dell = [row("dell_works_verified", "approve") for _ in range(20)] + [row("dell_broken_verified", "changes_requested") for _ in range(20)]
    out = B.cap_dell(non + dell)
    nd = sum(r["source"].startswith("dell") for r in out)
    assert nd / len(out) <= B.DELL_SHARE + 1e-9
    assert sum(json.loads(r["messages"][-1]["content"])["verdict"] == "approve" for r in out) / len(out) <= B.APPROVE_MAX + 1e-9
