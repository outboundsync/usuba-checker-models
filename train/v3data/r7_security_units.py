#!/usr/bin/env python3
"""r7 gap (b): classify the 207 prepared version-history `security` fix pairs into the weak added-finding slugs with two open-weights models (must agree), and write build_scope-compatible units
(pre-fix tree on disk, the verified pre-fix line as the finding location). usage: r7_security_units.py WORKDIR   then: build_scope.py WORKDIR OUT --stage render|llm|assemble"""
import sys, os, json, pickle, collections
from concurrent.futures import ThreadPoolExecutor
H = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(H); sys.path[:0] = [T, H]
import llm_client as LC
W = sys.argv[1]; os.makedirs(W, exist_ok=True)
SLUGS = ["secrets-credentials", "url-scheme-network", "remote-code-pinning", "user-config-modification", "listing-metadata-docs", "scope-policy-duplicate", "rich-text-markup-injection"]
SYS = """You classify one upstream security-flavoured fix of an Omarchy/Quickshell plugin into the category of the DEFECT that was removed. Categories:
secrets-credentials (hardcoded secret/token/password, secret exposed in logs/args/URL), url-scheme-network (plain http, missing TLS verification, unsafe redirect/scheme, URL built from untrusted input),
remote-code-pinning (code/binary/script fetched or installed without a pinned immutable ref or checksum), user-config-modification (plugin overwrites or deletes user config/files without consent or backup),
listing-metadata-docs (missing/wrong licence, manifest or listing metadata, docs), scope-policy-duplicate (duplicate/overlapping plugin id or scope policy violation), rich-text-markup-injection (untrusted text rendered as rich text/markup),
none (anything else, e.g. TOCTOU/symlink/permissions, shell injection, resource limits, logic bugs).
Reply JSON only: {"category": "<one of the names above>", "why": "<short>"}"""
pr = [json.loads(l) for l in open("/workspace/r4/prepared.jsonl")]; sec = [p for p in pr if p["bug_kind"] == "security"]
def one(p):
    u = f"COMMIT: {p['subject']}\nDEFECT: {p['defect']}\nFIX: {p['fix']}\nFILE: {p['file']} LINE {p['pre_fix_line']}\nREMOVED LINES: {p['removed'][:6]}\nADDED LINES: {p['added'][:6]}"
    return LC.call(SYS, u, tag="r7_sec_cls_qwen", max_tokens=250), LC.call(SYS, u, tag="r7_sec_cls_gptoss", model=LC.GPT, effort="low", max_tokens=1500)
with ThreadPoolExecutor(12) as ex: res = list(ex.map(one, sec))
LC.assert_error_budget(); units = []; c = collections.Counter()
for p, (a, b) in zip(sec, res):
    ca, cb = a.get("category"), b.get("category")
    c[(ca if ca == cb else "disagree")] += 1
    if ca != cb or ca not in SLUGS or p["cls"] == "other": continue
    repo = p["repo"].replace("__", "/").lower()
    r = dict(plugin=repo, commit=p["parent"], bug_kind=ca, file=p["file"], line=p["pre_fix_line"], prose=f"{p['defect']} {p['fix']}", strength="strong", verify="quoted_code_near_line", _strict=True)
    units.append(dict(id=f"vh_security:{repo}:{p['commit'][:10]}", source="version_history", repo=repo, commit=p["parent"], spec=dict(dir=p["tree_pre"]), origin="history_tree",
                      prov=dict(kind="version-history-fix", repo=repo, commit=p["commit"], parent=p["parent"], license=p["license"], subject=p["subject"]), findings_cached=None,
                      evidence=[dict(file=p["file"], line=p["pre_fix_line"], text=p["defect"], kind=ca, basis="verified upstream fix changed this location")], verdict0="changes_requested", extend=[r], weight=1.0))
pickle.dump(units, open(os.path.join(W, "units.pkl"), "wb")); print(dict(c), "units", len(units), LC.stats())
