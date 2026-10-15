#!/usr/bin/env python3
"""Holdout guard: no training/validation row may come from a sealed-holdout plugin repo.

The public id list is eval/hancore_holdout/plugin_ids.txt (329 repo URLs; the labelled manifest itself is private, only its SHA-256 is published).
The data builders also exclude by the private manifest; this guard is an independent check that needs only the public ids, so anyone can run it.

    python3 train/holdout_guard.py train.jsonl[.gz] val.jsonl[.gz] ...      # exit 1 on overlap
    from holdout_guard import assert_clean; assert_clean(rows)                # used by assemble_r4.py / build_train_set.py
"""
import gzip, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
IDS = os.environ.get("HOLDOUT_IDS") or os.path.join(HERE, "..", "eval", "hancore_holdout", "plugin_ids.txt")
_GH = re.compile(r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:[/#?\"'\s]|$)", re.I)


def norm(url):
    m = _GH.search(url if url.endswith("/") else url + "/")
    return (m.group(1) + "/" + m.group(2)).lower() if m else None


def load_ids(path=IDS):
    ids = {norm(l.strip()) for l in open(path) if l.strip()}
    ids.discard(None)
    if len(ids) < 300:
        raise SystemExit(f"holdout id list looks wrong ({len(ids)} ids) at {path}")
    return ids


def row_repos(row):
    """Every repository a row claims to come from (meta/provenance fields only, not free text)."""
    out = set()
    for d in (row, row.get("meta"), row.get("provenance")):
        if not isinstance(d, dict):
            continue
        for k in ("repo", "repo_url", "plugin", "source_repo"):
            v = d.get(k)
            if isinstance(v, str):
                n = norm(v) or (v.lower() if re.fullmatch(r"[\w.-]+/[\w.-]+", v) else None)
                if n:
                    out.add(n)
    prov = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
    for u in (prov.get("comment_urls") or []):
        if isinstance(u, str) and "/issues/" not in u:
            n = norm(u)
            if n:
                out.add(n)
    return out


def overlap(rows, ids=None):
    ids = ids or load_ids()
    return [r.get("id", "?") for r in rows if row_repos(r) & ids]


def assert_clean(rows, ids=None):
    bad = overlap(list(rows), ids)
    if bad:
        raise SystemExit(f"HOLDOUT GUARD: {len(bad)} row(s) come from sealed-holdout repos, e.g. {bad[:5]}")


def read(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


if __name__ == "__main__":
    ids = load_ids(); bad = 0
    for p in sys.argv[1:]:
        o = overlap(read(p), ids); bad += len(o)
        print(f"{p}: {len(o)} overlapping row(s)")
    sys.exit(1 if bad else 0)
