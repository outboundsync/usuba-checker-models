#!/usr/bin/env python3
"""Audit teacher-written reviews of broken plugins against the verified failure. Judge: open-weights Qwen3.5-397B-A17B via OpenRouter (key from env).
usage: audit.py run <final_dir> <out.json> | audit.py (summary)"""
import json, os, sys, re, threading
from concurrent.futures import ThreadPoolExecutor
import urllib.request
from common import *
MODEL = os.environ.get("JUDGE", "qwen/qwen3.5-397b-a17b")
SYS = """You grade a code review of a Quickshell/QML plugin that is KNOWN to be broken. You get the VERIFIED FAILURES (ground truth: file, symbol, mechanism) and the review's blocker findings.
Grade the review:
- names_actual_bug: at least one review blocker identifies the same verified failure: same file (or the same plugin-level cause for checker-level failures), same symbol/binary/property, and the same mechanism.
- loose: the review is in the right area (same file or same kind of problem) but names a different symbol/mechanism, is vague, or only matches by generic wording.
- wrong: no blocker corresponds to any verified failure.
Also count review blockers that do not correspond to any verified failure (extra_unmatched). Reply with JSON only: {"grade":"names_actual_bug|loose|wrong","matched_gold":[indices],"extra_unmatched":N,"why":"one sentence"}"""
def call(user):
    req = dict(model=MODEL, max_tokens=8000, messages=[{"role": "system", "content": SYS}, {"role": "user", "content": user}], reasoning={"effort": "low"},
               provider={"data_collection": "deny", "sort": "throughput"}, usage={"include": True}, temperature=0)
    for att in range(4):
        try:
            r = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(req).encode(), headers={"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"], "Content-Type": "application/json"})
            j = json.load(urllib.request.urlopen(r, timeout=240)); t = j["choices"][0]["message"].get("content") or ""
            m = re.search(r"\{.*\}", t, re.S); return json.loads(m.group(0)), (j.get("usage") or {}).get("cost") or 0.0
        except Exception as e: err = repr(e)[:150]
    return dict(grade="error", why=err), 0.0
def main():
    fd, out = sys.argv[2], sys.argv[3]
    G = {g["orig"]: g for g in jl(os.path.join(WORK, "guided.jsonl"))}
    rows = [json.loads(l) for sp in ("train", "val") for l in open(os.path.join(fd, sp + ".jsonl"))]
    rows = [x for x in rows if x["label"] == "broken" and x["source"] != "hancore" and x["target_kind"].startswith("teacher")]
    res = json.load(open(out)) if os.path.exists(out) else {}; spend = [0.0]; LK = threading.Lock()
    def one(x):
        if x["id"] in res: return
        g = G[x["id"].split(":")[-1]]; t = json.loads(x["messages"][-1]["content"])
        gold = "\n".join(f"[{i}] {v['category']}: {v['finding']}" for i, v in enumerate(g["vis"]))
        rev = "\n".join(f"- {f['file']}:{f['line']} [{f['category']}] {f['finding']}" for f in t["findings"] if str(f.get("severity")).lower() == "blocker") or "(no blockers)"
        r, c = call(f"VERIFIED FAILURES:\n{gold}\n\nREVIEW BLOCKERS:\n{rev}")
        with LK: res[x["id"]] = dict(r, split=x["split"], kind=x["target_kind"]); spend[0] += c
    with ThreadPoolExecutor(12) as ex: list(ex.map(one, rows))
    wjson(out, res); import collections
    print(collections.Counter(v["grade"] for v in res.values()), "spend", round(spend[0], 4))
if __name__ == "__main__": main()
