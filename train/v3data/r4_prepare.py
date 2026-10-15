#!/usr/bin/env python3
"""r4 step 1: version-history verified pairs -> license filter, exclusions, pre/post source trees (text sources only), copyright, exact-line class.
usage: r4_prepare.py OUT_DIR   (reads verified_pairs.jsonl (round 1) and verified_pairs_2.jsonl (round 2, if present); clones in /workspace/vh_repos). No model calls."""
import sys, os, re, json, subprocess, collections, hashlib
from concurrent.futures import ThreadPoolExecutor
H = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(H); ROOT = os.path.dirname(T)
sys.path[:0] = [T, os.path.join(ROOT, "functest"), os.path.join(ROOT, "hancore"), H]
import build_train_set as B, functest as FT
OUT = sys.argv[1]; TR = os.path.join(OUT, "trees2"); os.makedirs(TR, exist_ok=True)
VH = ["/workspace/usuba-runs/version-history/data/verified_pairs.jsonl", "/workspace/usuba-runs/version-history/data/verified_pairs_2.jsonl"]; REPOS = "/workspace/vh_repos/"
OK_LIC = {"MIT", "Apache-2.0", "BSD", "ISC"}
GLOBS = ["*." + e for e in "qml js mjs sh bash py lua json toml md txt service desktop conf rs yaml yml".split()] + ["LICENSE*", "COPYING*", "NOTICE*", "LICENCE*", "bin/*", "*/bin/*", "scripts/*", "*/scripts/*"]
pairs = [dict(json.loads(l), round=i + 1) for i, f in enumerate(VH) if os.path.exists(f) for l in open(f)]
st = collections.Counter(); st["pairs_in"] = len(pairs)
h_repos, h_ids, h_trees = B.holdout_fingerprint()
key_ids, key_trees = set(), []
for l in open(os.path.join(ROOT, "functest", "dell_ground_truth.jsonl")):
    k = json.loads(l); key_ids.add(k["id"].lower())      # ids/paths only
    p = os.path.join(ROOT, k.get("path") or "")
    if k.get("path") and os.path.isdir(p):
        fh = B.file_hashes(FT.read_dir(p))
        if fh: key_trees.append(fh)
excl_repos = {B.norm_repo(u) for u in json.load(open("/workspace/usuba-runs/hancore-labels/excluded_plugins.json"))}
def arch(repo, rev, dest, extra=()):
    if os.path.isdir(dest) and os.path.exists(dest + "/.done"): return True
    os.makedirs(dest, exist_ok=True)
    p1 = subprocess.Popen(["git", "-C", REPOS + repo, "archive", rev], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p2 = subprocess.run(["tar", "-x", "--wildcards", "-C", dest] + GLOBS + list(extra), stdin=p1.stdout, capture_output=True); p1.stdout.close(); err = p1.stderr.read(); p1.wait()
    if p1.returncode: return False
    open(dest + "/.done", "w").write("1"); return True
def work(p):
    rid = f"{p['repo']}_{p['commit'][:10]}"
    pre = arch(p["repo"], p["parent"], f"{TR}/{rid}_pre", [p["file"]]); post = arch(p["repo"], p["commit"], f"{TR}/{rid}_post", [p["file"]])
    return rid, pre, post
cands = []
for p in pairs:
    if p["license"] not in OK_LIC: st["excluded_license_" + p["license"]] += 1; continue
    repo = B.norm_repo(p["url"])
    if repo in h_repos or repo in excl_repos: st["excluded_holdout_or_key_repo"] += 1; continue
    cands.append(p)
st["after_license_and_repo_exclusion"] = len(cands)
with ThreadPoolExecutor(8) as ex: R = list(ex.map(work, cands))
out = []
for p, (rid, pre, post) in zip(cands, R):
    if not pre: st["archive_failed_pre"] += 1; continue
    d = f"{TR}/{rid}_pre"; files = {k: v for k, v in FT.read_dir(d).items() if k != ".done"}
    mid = B.manifest_id({"manifest.json": files.get("manifest.json", "")}); fh = B.file_hashes(files)
    if mid and (mid.lower() in h_ids or mid.lower() in key_ids): st["excluded_manifest_id"] += 1; continue
    if B.near_dup(fh, h_trees) or B.near_dup(fh, key_trees): st["excluded_near_dup_holdout_or_key"] += 1; continue
    lines = files.get(p["file"], "").split("\n"); L = int(p["pre_fix_line"])
    if L < 1 or L > len(lines) or lines[L - 1].strip() != p["pre_fix_line_text"].strip(): st["pre_fix_line_text_mismatch"] += 1; continue
    rem = [x.strip() for x in p["removed"]]
    cls = "exact_removed" if p["pre_fix_line_text"].strip() in rem and rem else ("insertion_anchor" if not rem else "other")
    lic = next((v for k, v in files.items() if re.match(r"(LICEN[CS]E|COPYING)", os.path.basename(k), re.I) and "/" not in k), "")
    cr = re.findall(r"(?im)^\s*(copyright\s*(?:\(c\)|©)?\s*[^\n]{3,90})$", lic)
    out.append(dict(p, pre_fix_line=L, cls=cls, tree_pre=d, tree_post=(f"{TR}/{rid}_post" if post else None), copyright=(cr[0].strip() if cr else None), license_file_present=bool(lic)))
    st["class_" + cls] += 1
json.dump(dict(st), open(OUT + "/prepare_stats.json", "w"), indent=1)
with open(OUT + "/prepared.jsonl", "w") as f:
    for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(json.dumps(dict(st), indent=1), len(out))
