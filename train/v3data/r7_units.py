#!/usr/bin/env python3
"""r7: per-repo mining results (build_r7_mine.py) -> build_scope units. Security-like fix commits get a category from TWO open-weights models that must agree (and pick the removed line); labels from
the miner become `preset` triage labels (confirm = fix removed/changed the cited line; dismiss = provisional persistence). usage: r7_units.py MINEDIR WORKDIR"""
import sys, os, json, gzip, glob, pickle, collections
from concurrent.futures import ThreadPoolExecutor
H = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(H); sys.path[:0] = [T, H]
import llm_client as LC
MD, W = sys.argv[1], sys.argv[2]; os.makedirs(W, exist_ok=True)
SLUGS = ["secrets-credentials", "url-scheme-network", "remote-code-pinning", "user-config-modification", "listing-metadata-docs", "scope-policy-duplicate", "rich-text-markup-injection"]
SYS = """You classify ONE upstream commit of an Omarchy/Quickshell plugin. You get the commit message and the removed/added lines of its hunks. Decide whether it fixes a defect in one of these categories and pick the hunk whose REMOVED line holds the defect:
secrets-credentials (hardcoded secret/token/password; secret exposed in logs/args/URL), url-scheme-network (plain http, no TLS verification, unsafe redirect/scheme, URL from untrusted input),
remote-code-pinning (code/binary/script fetched or installed without pinned immutable ref or checksum), user-config-modification (overwrites/deletes user config or files without consent/backup),
listing-metadata-docs (missing/wrong licence, manifest/listing metadata, docs), scope-policy-duplicate (duplicate/overlapping id or scope policy), rich-text-markup-injection (untrusted text rendered as rich text/markup), none (anything else).
Reply JSON only: {"category": "<name>", "hunk": <index int or null>, "why": "<short>"}"""
cands = []
for f in sorted(glob.glob(os.path.join(MD, "repos", "*.json.gz"))):
    d = json.load(gzip.open(f, "rt"))
    if d["status"] != "ok": continue
    for c in d["cands"]: cands.append((d, c))
jobs = [(d, c) for d, c in cands if c["sec_like"] and c["hunks"]]
def one(job):
    d, c = job
    u = f"COMMIT: {c['subject']}\n{c['body'][:400]}\nHUNKS:\n" + "\n".join(f"[{i}] {h['file']} old_line {h['old_line']}\n  REMOVED: {h['removed'][:3]}\n  ADDED: {h['added'][:3]}" for i, h in enumerate(c["hunks"]))
    return LC.call(SYS, u, tag="r7_cls_qwen", max_tokens=250), LC.call(SYS, u, tag="r7_cls_gptoss", model=LC.GPT, effort="low", max_tokens=1500)
with ThreadPoolExecutor(12) as ex: res = list(ex.map(one, jobs))
LC.assert_error_budget(); cls = {}; cnt = collections.Counter()
for (d, c), (a, b) in zip(jobs, res):
    ok = a.get("category") == b.get("category") and a.get("category") in SLUGS and isinstance(a.get("hunk"), int) and a.get("hunk") == b.get("hunk") and 0 <= a["hunk"] < len(c["hunks"])
    cnt[a.get("category") if ok else "unclassified/disagree"] += 1
    if ok: cls[(d["repo"], c["version"])] = (a["category"], c["hunks"][a["hunk"]])
units = []
for d, c in cands:
    repo = d["url"].replace("https://github.com/", "").lower(); ev = []; preset = {}
    for f, l in zip(c["findings"], c["labels"]):
        if not l["decision"]: continue
        if l["decision"] == "confirm": ev.append(dict(file=f["file"], line=f["line"], text="A later commit (%s) removed or changed this line." % c["subject"][:100], basis="verified: fix commit removed or changed the cited line"))
        else: preset[(f["rule"], f["file"], f["line"])] = ("dismiss", l["basis"], dict(file=f["file"], line=f["line"], text="The same line stays unchanged and the plugin keeps working through %d later versions." % l["evidence"]["later"]))
    ext = []
    k = cls.get((d["repo"], c["version"]))
    if k:
        h = k[1]; ext.append(dict(plugin=repo, commit=c["version"], bug_kind=k[0], file=h["file"], line=h["old_line"], prose=f"{c['subject']}. Removed: {' / '.join(h['removed'][:2])}", strength="strong", verify="quoted_code_near_line", _strict=True))
    if not ev and not preset and not ext and c["kind"] != "clean": continue
    units.append(dict(id=f"r7:{d['repo']}:{c['version'][:10]}:{c['kind']}", source="version_history", repo=repo, commit=c["version"], spec=dict(files=c["files"]), origin="history_tree",
                      prov=dict(kind="version-history-fix", repo=repo, commit=c["commit"] or c["version"], parent=c["version"], license=d["license"], subject=c["subject"], head_date=d["head_date"], r7_kind=c["kind"]),
                      findings_cached=None, evidence=ev, preset=preset, verdict0="approve" if c["kind"] == "clean" else "changes_requested", extend=ext, weight=1.0))
pickle.dump(units, open(os.path.join(W, "units.pkl"), "wb")); print("cands", len(cands), "classified", dict(cnt), "units", len(units), LC.stats())
