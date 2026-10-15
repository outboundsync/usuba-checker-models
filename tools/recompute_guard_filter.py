"""Recompute sealed-holdout filter counts (audit F3) from dataset files, using train/holdout_guard.py.

    # entries for files that are already guard-filtered (publish-ready): expect dropped_holdout_overlap == 0
    python3 tools/recompute_guard_filter.py --staged DIR v3_r4_public/train.jsonl.gz v3_r4_public/val.jsonl.gz
    # pre-filter source files: counts what the guard would drop (reproduces the kept/dropped numbers in hf/GUARD_FILTER.json)
    python3 tools/recompute_guard_filter.py --source SRC clean/pool_chunked.jsonl
    ... --merge hf/GUARD_FILTER.json   # write the entries into that file (keys sorted, existing keys kept unless recomputed)

Output per file: rows, kept, dropped_holdout_overlap, sha256 of the file. Exit 1 when a --staged file has any overlap.
"""
import argparse
import gzip
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "train"))
import holdout_guard  # noqa: E402


def rows_of(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def entry(path, ids):
    rows = rows_of(path)
    dropped = sum(1 for r in rows if holdout_guard.row_repos(r) & ids)   # per row, not via id (rows may lack ids)
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    return {"rows": len(rows), "kept": len(rows) - dropped, "dropped_holdout_overlap": dropped, "sha256": digest}


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--staged")
    g.add_argument("--source")
    ap.add_argument("--merge")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    ids = holdout_guard.load_ids()
    base = a.staged or a.source
    out, rc = {}, 0
    for rel in a.files:
        e = entry(os.path.join(base, rel), ids)
        if a.staged:
            e = {k: v for k, v in e.items() if k != "rows"}
            if e["dropped_holdout_overlap"]:
                rc = 1
        else:
            e = {"kept": e["kept"], "dropped_holdout_overlap": e["dropped_holdout_overlap"]}
        out[rel] = e
        print(rel, e)
    if a.merge:
        cur = json.load(open(a.merge)) if os.path.exists(a.merge) else {}
        cur.update(out)
        with open(a.merge, "w") as f:
            json.dump(dict(sorted(cur.items())), f, indent=1)
            f.write("\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
