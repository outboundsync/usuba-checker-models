#!/usr/bin/env python3
"""v2 calibration val set: ~150 working + ~150 broken Dell plugins (label works+Checker PASS / broken+Checker FAIL),
disjoint from the 90-plugin Dell answer key and the HANCORE holdout (repo, manifest id, near-dup code tree).
Deterministic: pick by sha1(key) order. -> train/data/val_v2_keys.json. Every other v2 source excludes these repos."""
import json, os, sys, hashlib, collections
H = os.path.dirname(os.path.abspath(__file__)); TR = os.path.dirname(H); ROOT = os.path.dirname(TR)
sys.path[:0] = [TR, os.path.join(ROOT, "functest")]
import build_train_set as B
def answer_key():
    ids, trees, repos = set(), [], set()
    for l in open(ROOT + "/functest/dell_ground_truth.jsonl"):
        g = json.loads(l); ids.add(g["id"].lower())
        p = os.path.join(ROOT, g["path"])
        if os.path.isdir(p):
            import functest; files = functest.read_dir(p); fh = B.file_hashes(files)
            if fh: trees.append(fh)
            mid = B.manifest_id(files)
            if mid: ids.add(mid.lower())
        if g.get("repo"): repos.add(B.norm_repo(g["repo"]))
    return ids, trees, repos
def build(n_each=150):
    import functest
    h_repos, h_ids, h_trees = B.holdout_fingerprint(); k_ids, k_trees, k_repos = answer_key()
    C = {json.loads(l)["key"]: json.loads(l) for l in open(B.SW + "/corpus.jsonl")}
    pools = collections.defaultdict(list)
    for l in open(B.SW + "/results.jsonl"):
        r = json.loads(l); ck = (r.get("checker") or {}).get("pass_"); c = C.get(r["key"]) or {}
        if not r.get("dell") or not c.get("local_dir") or not os.path.isdir(c["local_dir"]): continue
        lab = "works" if (r["label"] == "works" and ck is True) else "broken" if (r["label"] == "broken" and ck is False) else None
        if not lab: continue
        pools[lab].append(r)
    out = {}
    for lab, L in pools.items():
        L.sort(key=lambda r: hashlib.sha1(("v2val:" + r["key"]).encode()).hexdigest()); pick = []
        for r in L:
            repo = B.norm_repo(r["key"]); files = functest.read_dir(C[r["key"]]["local_dir"]); fh = B.file_hashes(files)
            mid = (B.manifest_id(files) or r.get("plugin_id") or "").lower()
            if repo in h_repos or repo in k_repos or mid in h_ids or mid in k_ids or (r.get("plugin_id") or "").lower() in k_ids: continue
            if B.near_dup(fh, h_trees) or B.near_dup(fh, k_trees): continue
            pick.append(dict(key=r["key"], repo=repo, plugin_id=r.get("plugin_id"), label=lab, local_dir=C[r["key"]]["local_dir"]))
            if len(pick) == n_each: break
        out[lab] = pick
    json.dump(out, open(os.path.join(TR, "data", "val_v2_keys.json"), "w"), indent=0)
    return out
def val_repos():
    d = json.load(open(os.path.join(TR, "data", "val_v2_keys.json")))
    return {x["repo"] for L in d.values() for x in L}
if __name__ == "__main__":
    o = build(); print({k: len(v) for k, v in o.items()})
