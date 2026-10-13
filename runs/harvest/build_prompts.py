"""Training prompt set for harvesting: full-plugin tasks (build_from_spec, add_panel) from v3/train_v3.jsonl.
Excludes all 56 data/holdout.jsonl prompts (superset of the 49 clean holdout): same (repo, plugin_path) plugin,
same plugin id, or prompt 8-gram jaccard >= 0.5 against any holdout prompt. Dedupes on normalized user prompt.
Tree tasks (chunk_*) are skipped: their grader needs the upstream tree at the exact commit (only available for holdout repos)."""
import json, os, re, hashlib, collections
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
FULL = ("build_from_spec", "add_panel")
hold = [json.loads(l) for l in open(os.path.join(ROOT, "data/holdout.jsonl"))]
def grams(t, n=8):
    w = re.findall(r"\w+", t.lower()); return {" ".join(w[i:i+n]) for i in range(max(1, len(w)-n+1))}
def pid(t):
    m = re.search(r"`([\w.-]+\.[\w.-]+)`", t) or re.search(r'"id":\s*"([^"]+)"', t); return m.group(1) if m else None
hp = {(h["meta"].get("repo"), h["meta"].get("plugin_path")) for h in hold}
hids = {pid(h["messages"][1]["content"]) for h in hold} - {None}
hg = [grams(h["messages"][1]["content"]) for h in hold]
out, seen, C = [], set(), collections.Counter()
for ti, l in enumerate(open(os.path.join(ROOT, "v3/train_v3.jsonl"))):
    r = json.loads(l)
    if r["task"] not in FULL: C["skip-tree-task"] += 1; continue
    u = r["messages"][1]["content"]; m = r["meta"]
    if (m.get("repo"), m.get("plugin_path")) in hp: C["excl-holdout-plugin"] += 1; continue
    if pid(u) and pid(u) in hids: C["excl-holdout-id"] += 1; continue
    g = grams(u); j = max(len(g & x) / len(g | x) for x in hg)
    if j >= 0.5: C["excl-holdout-jaccard"] += 1; continue
    k = hashlib.sha1(re.sub(r"\s+", " ", u.strip().lower()).encode()).hexdigest()
    if k in seen: C["dupe"] += 1; continue
    seen.add(k)
    out.append({"pid": f"v3-{ti}", "train_i": ti, "task": r["task"], "messages": r["messages"][:2], "meta": m, "ref": r["messages"][2]["content"], "max_holdout_jaccard8": round(j, 3)})
    C["kept"] += 1
with open(os.path.join(H, "prompts.jsonl"), "w") as f:
    for o in out: f.write(json.dumps(o) + "\n")
print(dict(C)); json.dump(dict(C), open(os.path.join(H, "prompts_manifest.json"), "w"), indent=1)
