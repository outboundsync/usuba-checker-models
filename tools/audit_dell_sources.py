#!/usr/bin/env python3
"""Audit the dell_* training sources against the sealed Dell answer key and the sealed holdout (audit 6). CPU, no network, hashes/counts only in the output.

    python3 tools/audit_dell_sources.py --data /workspace/usuba-runs/v3-data-r5 --holdout /workspace/wt-retrain-v2/eval/hancore_holdout \
        --dell-key /workspace/wt-retrain-v2/functest/dell_ground_truth.jsonl --dell-root /workspace/omarchy-specialist --corpus /workspace/wt-retrain-v2/dell/sweep/corpus.jsonl --out v3/r5/DELL_AUDIT.md

1. Rebuild the guard fingerprints from the private key trees and holdout archives (independently of the committed file) and compare them with the committed one.
2. Run the content guard (whitespace-normalised file sha1 + 5-token-shingle MinHash Jaccard >= 0.6, same thresholds as the builder) of EVERY train/val row
   against those fresh fingerprints, and compare manifest ids / repos / Dell-key ids.
3. Describe what the dell_* rows are: the Dell SWEEP (public marketplace / github-search repos run on the Dell box, runtime-verified), not the key."""
import argparse
import collections
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(MODELS, "train"))
import holdout_guard as G  # noqa: E402


def rows_of(p):
    with gzip.open(p, "rt") as f:
        return [json.loads(x) for x in f if x.strip()]


def canon(path):
    d = json.load(gzip.open(path, "rt"))
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest(), d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--holdout", required=True)
    ap.add_argument("--dell-key", required=True)
    ap.add_argument("--dell-root", required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tmp = os.path.join(tempfile.mkdtemp(), "fp.json.gz")
    subprocess.run([sys.executable, os.path.join(MODELS, "train", "build_guard_fingerprints.py"), "--holdout", a.holdout, "--dell-key", a.dell_key, "--dell-root", a.dell_root, "--out", tmp], check=True, capture_output=True)
    fresh_sha, fresh = canon(tmp)
    com_sha, com = canon(os.path.join(MODELS, "train", "guard_data", "fingerprints.json.gz"))
    key = [json.loads(x) for x in open(a.dell_key)]
    nodir = sorted(k["id"] for k in key if not (k.get("path") and os.path.isdir(os.path.join(a.dell_root, k["path"]))))
    import build_guard_fingerprints as B
    empty = sorted(k["id"] for k in key if k["id"] not in nodir and not G.tree_fp(B.with_capped(B.read_tree(os.path.join(a.dell_root, k["path"])))))
    guard = G.Guard(tmp)
    corpus = {}
    for x in open(a.corpus):
        c = json.loads(x)
        corpus[c["key"].lower()] = c
    key_ids = {k["id"].lower() for k in key}
    rows = [dict(r, _sp=sp) for sp in ("train", "val") for r in rows_of(os.path.join(a.data, sp + ".jsonl.gz"))]
    hits = collections.Counter()
    by_src = collections.Counter()
    idhit = []
    for r in rows:
        by_src[r["source"]] += 1
        why = guard.check_row(r)
        if why:
            hits[r["source"]] += 1
        mf = G.parse_blob(r["messages"][-2]["content"]).get("manifest.json")
        try:
            mid = (json.loads(mf) or {}).get("id") if mf else None
        except Exception:
            mid = None
        if isinstance(mid, str) and mid.lower() in key_ids:
            idhit.append(r["id"])
    dell = [r for r in rows if r["source"].startswith("dell") or r["source"] == "nudged_approve"]
    prov = collections.Counter()
    srcs = collections.Counter()
    runs = collections.Counter()
    notin = 0
    for r in dell:
        pv = r["provenance"]
        prov[pv.get("kind")] += 1
        runs[pv.get("dell_run")] += 1
        m = re.match(r"^[\w-]+:([^:]+):", r["id"])
        c = corpus.get(m.group(1).lower()) if m else None
        if c is None:
            notin += 1
            continue
        srcs[",".join(sorted(c["sources"]))] += 1
    L = ["# Dell source audit (r5)\n",
         f"- data: train+val {len(rows)} rows; dell_* / nudged rows: {len(dell)}; by source `{dict(by_src)}`",
         f"- fresh fingerprints rebuilt from the private key trees + holdout archives: sha256(canonical json) `{fresh_sha[:16]}`; committed `{com_sha[:16]}`; **identical: {fresh_sha == com_sha}**",
         f"- sealed holdout plugins fingerprinted: {len(fresh['holdout'])}; Dell key ids {len(fresh['dell_ids'])}, key trees available and fingerprinted {len(fresh['dell_trees'])}; key ids WITHOUT a local tree (not content-checkable, id-checked only): {len(nodir)} {nodir[:20]}; key ids whose tree has no non-trivial file to fingerprint (id-checked only): {len(empty)} {empty}",
         f"- content guard (file sha1 + MinHash Jaccard >= {G.JACCARD}, >= {int(G.FILE_SHARE * 100)}% of non-trivial files in one plugin) of every train/val row against the fresh fingerprints: **rows rejected {sum(hits.values())}** `{dict(hits)}`",
         f"- manifest ids of train/val rows equal to a Dell-key id: **{len(idhit)}** {idhit[:5]}",
         f"- provenance kinds of the dell rows `{dict(prov)}`; sweep runs `{dict(runs)}`",
         f"- the dell rows' plugins in the sweep corpus: {len(dell) - notin}/{len(dell)}; corpus `sources` of those plugins `{dict(srcs)}`",
         "", "Reading: the Dell KEY is 116 hand-run plugins (registry + generated, ids like fab.pillbar, verdicts from real hardware runs). The dell_* TRAINING rows are plugins from the Dell SWEEP corpus "
         "(public marketplace / github-search repositories, pinned commit) whose label comes from the sweep's own runtime verdict (+ Checker agreement). "
         "They are different plugins; the content check above is the evidence, and any overlap would have been rejected by the same guard at build and at train_lora load."]
    open(a.out, "w").write("\n".join(L) + "\n")
    print("\n".join(L))
    sys.exit(0 if not hits and not idhit and fresh_sha == com_sha else 1)


if __name__ == "__main__":
    main()
