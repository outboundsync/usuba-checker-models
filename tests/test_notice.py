import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("gen_notice", os.path.join(ROOT, "tools", "gen_notice.py"))
gn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gn)


def test_notice_covers_every_shipped_repo_and_has_no_boilerplate():
    text = open(gn.NOTICE).read()
    assert gn.problems(text, gn.shipped()) == []


def test_apache_text_is_shipped_when_apache_sources_ship():
    ship = gn.shipped()
    if any(e["license"] == "Apache-2.0" for e in ship.values()):
        assert os.path.getsize(os.path.join(ROOT, "sources", "licenses", "Apache-2.0.txt")) > 10000


def test_checker_flags_a_missing_repo_and_boilerplate():
    ship = {"a/b": {"repo": "a/b", "commit": "c", "license": "MIT", "copyright": "Copyright (c) 2026 X"}}
    assert any("missing from NOTICE: a/b" in p for p in gn.problems("hdr\n", ship))
    bad = "hdr\n- a/b @ abc — Apache-2.0 — copyright license to reproduce, prepare Derivative Works of, (1 rows)\n"
    assert any("unresolved copyright" in p for p in gn.problems(bad, ship))
    assert any("all are MIT" in p for p in gn.problems("all are MIT", {}))


def test_known_gaps_only_shrink():
    # every listed gap must still be a gap; fixing one means deleting it from the file
    text = open(gn.NOTICE).read()
    ls = gn.listed(text)
    for r in gn.gaps():
        assert r in ls and gn.bad_copyright(ls[r].group(5)) or gn.UNRESOLVED in ls[r].group(5), "remove fixed repo from sources/notice_known_gaps.txt: " + r


def test_manifest_is_plain_sha256sum_format():
    for ln in open(os.path.join(ROOT, "hf", "MANIFEST.sha256")):
        digest, path = ln.rstrip("\n").split("  ", 1)
        assert len(digest) == 64 and ":" not in path and not ln.startswith("#")
