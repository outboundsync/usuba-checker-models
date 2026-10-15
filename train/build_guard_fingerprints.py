#!/usr/bin/env python3
"""Build guard_data/fingerprints.json.gz: HASHES ONLY of (a) the 329 sealed-holdout plugins (private code archives) and (b) the Dell answer-key trees.
Reads plugin code only to hash it; writes no plaintext, no labels. Needs the private holdout dir (USUBA_HOLDOUT_DIR: manifest.jsonl + code/*.tar.gz) and the
Dell key dir (--dell-key FILE.jsonl, --dell-root DIR for the 'path' fields).
  python3 build_guard_fingerprints.py --holdout DIR --dell-key functest/dell_ground_truth.jsonl --dell-root ROOT"""
import argparse, gzip, json, os, sys, tarfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import holdout_guard as G
from code_blob import FILE_CAP, render_file
HARNESS = {"SOURCE.txt", "checklist.md"}

def with_capped(files):
    """files + the version the model would see for files over the render cap (so truncated copies still match)"""
    out = dict(files)
    for p, t in files.items():
        if len(t) > FILE_CAP:
            _, info = render_file(p, t)
            out[p + "#cap"] = "\n".join(t.split("\n")[:info["shown"]])
    return out

def read_tar(path):
    files = {}
    with tarfile.open(path) as t:
        for m in t.getmembers():
            if m.isfile() and m.size < 2_000_000:
                try: files[m.name.split("/", 1)[-1]] = t.extractfile(m).read().decode("utf-8")
                except Exception: pass
    return files

def read_tree(d):
    files = {}
    for r, ds, fs in os.walk(d):
        ds[:] = [x for x in ds if x != ".git"]
        for f in fs:
            p = os.path.join(r, f)
            if f in HARNESS or os.path.islink(p) or os.path.getsize(p) > 2_000_000: continue
            try: files[os.path.relpath(p, d)] = open(p, encoding="utf-8").read()
            except Exception: pass
    return files

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--holdout", required=True); ap.add_argument("--dell-key", required=True); ap.add_argument("--dell-root", required=True)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "guard_data", "fingerprints.json.gz")); a = ap.parse_args()
    hold, mids, repos = [], [], []
    for l in open(os.path.join(a.holdout, "manifest.jsonl")):
        m = json.loads(l); repos.append(G.norm(m["repo"]) or m["repo"].lower()); files = read_tar(os.path.join(a.holdout, m["code_archive"]))
        try: mid = (json.loads(files.get("manifest.json", "{}")) or {}).get("id")
        except Exception: mid = None
        if isinstance(mid, str): mids.append(mid)
        hold.append(G.tree_fp(with_capped(files)))
    dids, dtrees = [], []
    for l in open(a.dell_key):
        k = json.loads(l); dids.append(k["id"]); p = os.path.join(a.dell_root, k.get("path") or "")
        if k.get("path") and os.path.isdir(p):
            fp = G.tree_fp(with_capped(read_tree(p)))
            if fp: dtrees.append(fp)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(dict(holdout=hold, manifest_ids=sorted(set(mids)), repos=sorted(set(repos)), dell_ids=sorted(set(dids)), dell_trees=dtrees,
                   note="hashes only; built from the private holdout code and Dell-key trees; used for exclusion"), gzip.open(a.out, "wt"))
    print(f"holdout plugins {len(hold)}, manifest ids {len(set(mids))}, dell ids {len(set(dids))}, dell trees {len(dtrees)} -> {a.out}")
if __name__ == "__main__": main()
