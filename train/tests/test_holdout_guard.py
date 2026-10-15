"""Holdout-guard tests (CPU only). Real data files are checked too when present (HOLDOUT_CHECK_FILES=a.jsonl.gz,b.jsonl or the default staged paths)."""
import glob, os, sys
import pytest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import holdout_guard as G

IDS = G.load_ids()


def test_ids_loaded():
    assert len(IDS) == 329


def test_known_holdout_repo_is_caught_in_every_field_shape():
    r = sorted(IDS)[0]
    for row in ({"meta": {"repo": f"https://github.com/{r}"}}, {"provenance": {"repo": r}}, {"provenance": {"repo_url": f"https://github.com/{r}.git"}},
                {"repo": f"git@github.com:{r}.git"}, {"meta": {"repo": f"https://GitHub.com/{r.upper()}/"}}):
        assert G.overlap([dict(row, id="x")], IDS) == ["x"], row


def test_unrelated_repo_passes():
    assert G.overlap([{"id": "ok", "meta": {"repo": "https://github.com/basecamp/omarchy"}, "provenance": {"repo": "basecamp/omarchy"}}], IDS) == []


def test_assert_clean_raises():
    with pytest.raises(SystemExit):
        G.assert_clean([{"id": "bad", "repo": "https://github.com/" + sorted(IDS)[3]}], IDS)


def test_published_data_has_no_holdout_rows():
    files = [f for f in os.environ.get("HOLDOUT_CHECK_FILES", "").split(",") if f]
    if not files:
        root = os.path.join(HERE, "..", "..")
        files = glob.glob(os.path.join(root, "..", "hf-staging", "datasets", "*", "**", "*.jsonl*"), recursive=True)
    if not files:
        pytest.skip("no data files present (download the Hugging Face dataset into the repo root to enable)")
    for p in files:
        assert G.overlap(G.read(p), IDS) == [], p
