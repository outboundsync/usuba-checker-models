#!/usr/bin/env python3
"""Step 1: build every candidate row (prompt + label + templated target + gold reasons) -> $DISTILL_WORK/candidates.jsonl.
Prompts use exactly the leak-free eval functions: run_eval.strip_harness / code_blob_whole / scrub, checker_report (shared), prompt_v2.messages.
Exclusions (train AND val): the 90-plugin Dell answer key (id, manifest id, repo, near-dup tree >=50% shared file hashes),
the HANCORE holdout (repo, manifest id, near-dup tree). Train additionally excludes the v2 val repos. Exact-duplicate code trees are dropped."""
import collections, gzip, hashlib, json, os, random, re, sys
from concurrent.futures import ProcessPoolExecutor
from common import *
import build_train_set as B, splits, functest, prompt_v2 as P, run_eval as E
from fetch import read_files as hc_read
HC_CAP = 1000; WORKS_CAP = 2000
def norm_finding(f):
    f = dict(f); f["finding"] = B.clean_finding(f.get("finding", ""))
    return dict(category=f["category"], severity=f["severity"], file=f.get("file"), line=f.get("line"), finding=f["finding"])

QWEN_TOK = os.path.expanduser("~/.cache/huggingface/hub/models--Qwen--Qwen3.5-9B/snapshots/c202236235762e1c871ad0ccb60c8ee5ba337b9a/tokenizer.json")
_TK = []
def qwen_tokens(msgs):
    """Training-model (Qwen3.5-9B) token count of a chat row: content tokens + 8 per message for the chat template."""
    if not _TK:
        from tokenizers import Tokenizer; _TK.append(Tokenizer.from_file(QWEN_TOK))
    return sum(len(_TK[0].encode(m["content"]).ids) + 8 for m in msgs)
def build_prompt(job):
    """job: dict(dir, reader) -> code, report, file hashes, manifest id, names, tokens"""
    files = hc_read(job["dir"]) if job["reader"] == "hc" else functest.read_dir(job["dir"])
    files = E.strip_harness(files)
    import checker_report
    rep = checker_report.report(files)
    code = E.scrub(E.code_blob_whole(files)); rep = [E.scrub(r) for r in rep] if rep is not None else None
    msgs = P.messages(code, rep)
    try: man = json.loads(files.get("manifest.json", "{}")) or {}
    except Exception: man = {}
    return dict(messages=msgs, fh=sorted(B.file_hashes(files)), mid=(man.get("id") if isinstance(man, dict) else None),
                mname=(man.get("name") if isinstance(man, dict) else None), files=sorted(files), est=E.est_tokens(msgs), qtok=qwen_tokens(msgs),
                code_sha=hashlib.sha1(code.encode()).hexdigest())

def cache_prompt(job):
    b = build_prompt(job); tmp = job["out"] + ".tmp"; json.dump(b, open(tmp, "w")); os.replace(tmp, job["out"]); return 1
def main():
    st = collections.Counter(); rnd = random.Random(1337)
    h_repos, h_ids, h_trees = B.holdout_fingerprint(); k_ids, k_trees, k_repos = splits.answer_key()
    VAL = json.load(open(os.path.join(TR, "data", "val_v2_keys.json"))); val_repos = {x["repo"] for L in VAL.values() for x in L}
    val_keys = {x["key"] for L in VAL.values() for x in L}
    C = []   # candidate dicts before prompts
    # --- Dell (train buckets + val) ---
    dc = B.dell_candidates(k_ids, st)
    res_by_key = {json.loads(l)["key"]: json.loads(l) for l in open(B.SW + "/results.jsonl")}
    for b, L in dc.items():
        for r in L:
            key = r["provenance"]; rk = r["repo"]
            C.append(dict(source=b, repo=rk, plugin_id=r["plugin_id"], dir=r["local_dir"], reader="dell",
                          label="works" if r["target"]["verdict"] == "approve" else "broken",
                          target=dict(verdict=r["target"]["verdict"], load=r["target"]["load"], findings=[norm_finding(f) for f in r["target"]["findings"]]),
                          provenance=r["provenance"]))
    # --- fix pairs ---
    for u in jl("/workspace/v2fix/upstream.jsonl"):
        if u["status"] != "pass": continue
        C.append(dict(source="fix_upstream", repo=B.norm_repo(u["repo"]), plugin_id=None, dir=u["code_dir"], reader="hc", label="works",
                      target=dict(verdict="approve", load="works", findings=[]),
                      provenance=dict(kind="upstream-fix", repo=u["repo"], commit=u["fix_commit"], parent_commit=u["parent_commit"], fixes=u["threads"], grader=u["grader"]),
                      pair=f"{B.norm_repo(u['repo'])}@{u['parent_commit']}"))
    for m in jl("/workspace/v2fix/model_fixes.jsonl"):
        if m["status"] != "pass" or not m.get("code_dir"): continue
        C.append(dict(source="fix_model", repo=B.norm_repo(m["repo"]), plugin_id=None, dir=m["code_dir"], reader="dell", label="works",
                      target=dict(verdict="approve", load="works", findings=[]),
                      provenance=dict(kind="model-fix", generator=m["generator"], parent_commit=m["parent_commit"], grader="usuba-checker", grader_verdict=m["grader_verdict"], changed_files=m["changed_files"]),
                      pair=f"{B.norm_repo(m['repo'])}@{m['parent_commit']}"))
    pair_parents = {c["pair"] for c in C if "pair" in c}
    # --- HANCORE (non-weak, strong first, fix parents always in) ---
    hc = B.hancore_examples(st)
    for r in hc:
        r["_parent"] = f"{r['repo']}@{r['_commit']}" in pair_parents
    hc.sort(key=lambda r: (not r["_parent"], r["_rank"], hashlib.sha1(r["repo"].encode()).hexdigest()))
    for r in hc:
        C.append(dict(source="hancore", repo=r["repo"], plugin_id=None, reader="hc",
                      dir=None, _hc=r, label="broken" if r["target"]["verdict"] == "changes_requested" else "works",
                      target=dict(verdict=r["target"]["verdict"], load=None, findings=[norm_finding(dict(f, file=f.get("file"))) for f in r["target"]["findings"]]),
                      provenance=r["provenance"], is_pair_parent=r["_parent"]))
    gzrepo = {}
    for l in gzip.open(os.path.join(ROOT, "data", "hancore_reviewer", "examples.jsonl.gz"), "rt"):
        e = json.loads(l); gzrepo[(B.norm_repo(e["repo"]), e["commit"])] = e["repo"]
    for c in C:
        if c["source"] == "hancore":
            c["dir"] = "/workspace/hancore_cache/" + gzrepo[(c["repo"], c["provenance"]["commit"])].replace("/", "__") + "@" + c["provenance"]["commit"]
            del c["_hc"]
    # mark model-fix parents among Dell rows
    for c in C:
        if c["source"].startswith("dell") and f"{c['repo']}@{c['provenance'].get('commit')}" in pair_parents: c["is_pair_parent"] = True
    # --- val rows (v2 calibration split): Dell rows whose key is in val_v2_keys ---
    for c in C:
        c["split"] = "val" if (c["source"].startswith("dell") and c["repo"] in val_repos) else "train"
    st["candidates_pre_exclusion"] = len(C)
    # cheap exclusions first (repo / id), then prompts
    keep = []
    for c in C:
        if c["repo"] in k_repos or (c.get("plugin_id") or "").lower() in k_ids: st["excl_answer_key_repo_or_id:" + c["source"]] += 1; continue
        if c["repo"] in h_repos: st["excl_holdout_repo:" + c["source"]] += 1; continue
        if c["split"] == "train" and c["repo"] in val_repos: st["excl_val_repo_from_train:" + c["source"]] += 1; continue
        if not c["dir"] or not os.path.isdir(c["dir"]): st["excl_no_code:" + c["source"]] += 1; continue
        keep.append(c)
    # caps before the expensive prompt build: works <= WORKS_CAP (+ margin for exclusions), HANCORE <= HC_CAP (+ margin)
    by = collections.defaultdict(list)
    for c in keep: by[(c["split"], c["source"])].append(c)
    keep = []
    for (sp, s), L in by.items():
        if s == "dell_works_verified" and sp == "train":
            L.sort(key=lambda c: hashlib.sha1(("v2w:" + c["repo"]).encode()).hexdigest()); L = L[:int(WORKS_CAP * 1.6)]
        if s == "hancore": L = L[:int(HC_CAP * 2)]
        keep += L
    # prompt build is cached per code dir on disk (resumable, low memory): workers write, parent reads one at a time
    PC = os.path.join(WORK, "prompt_cache"); os.makedirs(PC, exist_ok=True)
    pth = lambda c: os.path.join(PC, hashlib.sha1((c["reader"] + c["dir"]).encode()).hexdigest() + ".json")
    todo = [dict(dir=c["dir"], reader=c["reader"], out=pth(c)) for c in keep if not os.path.exists(pth(c))]
    import multiprocessing as mp
    with mp.get_context("fork").Pool(5, maxtasksperchild=40) as pool:
        for i, _ in enumerate(pool.imap_unordered(cache_prompt, todo, chunksize=4)):
            if i % 250 == 0: print("prompts", i, "/", len(todo), flush=True)
    out, seen = [], set()
    for c in keep:
        b = json.load(open(pth(c)))
        mid = (b["mid"] or "").lower()
        if mid and (mid in k_ids): st["excl_answer_key_manifest_id:" + c["source"]] += 1; continue
        if mid and mid in h_ids: st["excl_holdout_manifest_id:" + c["source"]] += 1; continue
        fh = set(b["fh"])
        if B.near_dup(fh, k_trees): st["excl_answer_key_near_dup:" + c["source"]] += 1; continue
        if B.near_dup(fh, h_trees): st["excl_holdout_near_dup:" + c["source"]] += 1; continue
        if b["code_sha"] in seen: st["excl_dup_code:" + c["source"]] += 1; continue
        if b["qtok"] + 1200 > ROW_TOKEN_CAP: st["excl_over_32k_tokens:" + c["source"]] += 1; continue   # prompt + room for the target
        seen.add(b["code_sha"]); c.update(messages=b["messages"], est_tokens=b["est"], prompt_tokens_qwen=b["qtok"], files=b["files"], manifest_id=b["mid"], manifest_name=b["mname"], code_sha=b["code_sha"])
        out.append(c)
    # final caps
    fin, cnt = [], collections.Counter()
    for c in out:
        k = (c["split"], c["source"])
        if c["source"] == "hancore" and cnt[k] >= HC_CAP: st["cap_dropped:hancore"] += 1; continue
        if c["source"] == "dell_works_verified" and c["split"] == "train" and cnt[k] >= WORKS_CAP: st["cap_dropped:dell_works_verified"] += 1; continue
        cnt[k] += 1; fin.append(c)
    for i, c in enumerate(fin): c["cid"] = f"r{i:05d}-" + hashlib.sha1((c["source"] + c["repo"] + c["code_sha"]).encode()).hexdigest()[:10]
    wjl(os.path.join(WORK, "candidates.jsonl"), fin)
    st.update({f"final:{sp}:{s}:{lab}": n for (sp, s, lab), n in collections.Counter((c["split"], c["source"], c["label"]) for c in fin).items()})
    wjson(os.path.join(WORK, "candidates_stats.json"), dict(sorted(st.items()))); print(json.dumps(dict(sorted(st.items())), indent=1))
if __name__ == "__main__": main()
