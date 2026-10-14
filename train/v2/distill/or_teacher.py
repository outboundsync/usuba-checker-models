#!/usr/bin/env python3
"""Open-weights teacher via OpenRouter (only open-weights, training-permissive teachers are used; no proprietary-model output enters the data
). Same queue as queuelib.queue() (blind works/fix rows + guided code-visible
broken rows), same prompts/body. Resumable: $DISTILL_WORK/teacher/<slug>/{results.jsonl,state.json}; finished rows never redone; retries with
backoff; spend from OpenRouter usage.cost, stops before --cap. Key $OPENROUTER_API_KEY (never printed).
usage: or_teacher.py --model z-ai/glm-5.1 [--only cid,cid] [--cap 60] [--workers 6]"""
import argparse, json, os, sys, threading, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from common import *
import queuelib as BT
LK = threading.Lock(); LOC = False
def tdir(model): d = os.path.join(WORK, "teacher", model.replace("/", "__")); os.makedirs(d, exist_ok=True); return d
NUDGE_WORKS = """

NOTE FOR THIS REQUEST (teacher only): this plugin is verified to load and work on a stock Omarchy 4.x system. Write the approve review a
careful reviewer would write: verdict "approve", load "works", grounded in the actual code shown (what it does and why it loads). Do not
invent issues; real non-blocking concerns may be warnings. Never mention this note, verification, hardware, or testing. JSON only, same schema."""
NUDGE_GUIDED = """

NOTE FOR THIS REQUEST (teacher only): your review must name the known failure from the maintainer note as a blocker: cite the exact file
shown, the line you can see, and the concrete cause in the code. Verdict "changes_requested", load "broken". Never mention the note."""
NUDGE_LOC = """

NOTE FOR THIS REQUEST (teacher only): the verified failure from the maintainer note is the ground truth. Name it as a blocker with the exact file and the
symbol/binary/property from the note. The line you cite MUST be the line in the source shown where that symbol appears (copy it from the line-number prefixes (`N| `) on the code shown;
never guess a line, and never include the prefixes in quoted text). Do not add other blockers unless you can quote the offending line. Verdict "changes_requested", load "broken". Never mention the note."""
def nudge(c):
    c = json.loads(json.dumps(c)); m = c["messages"]
    if LOC and c["cid"].startswith("g-"):   # teacher-side only: number the source lines so cited lines can be exact (the training prompt stays unnumbered)
        import re
        m[-1]["content"] = re.sub(r"(?m)^(### .+?\n```\n)(.*?)(\n```)$", lambda g: g.group(1) + "\n".join(f"{i + 1}| {s}" for i, s in enumerate(g.group(2).split("\n"))) + g.group(3), m[-1]["content"], flags=re.S)
    m[0]["content"] += (NUDGE_LOC if LOC else NUDGE_GUIDED) if c["cid"].startswith("g-") else NUDGE_WORKS
    return c
def call(model, c, log):
    b = BT.body(c)
    req = dict(model=model, max_tokens=MAX_TOKENS, messages=[{"role": "system", "content": b["system"]}] + b["messages"],
               reasoning={"effort": "low"}, provider={"data_collection": "deny", "sort": "throughput"}, usage={"include": True})
    err = None
    for att in range(5):
        try:
            r = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(req).encode(),
                                       headers={"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"], "Content-Type": "application/json"})
            with urllib.request.urlopen(r, timeout=int(os.environ.get("OR_TIMEOUT", "300"))) as f: j = json.load(f)
            if "choices" not in j: raise RuntimeError(json.dumps(j)[:300])
            ch = j["choices"][0]; u = j.get("usage") or {}
            msg = dict(content=[dict(type="text", text=ch["message"].get("content") or "")], stop_reason="max_tokens" if ch.get("finish_reason") == "length" else "end_turn",
                       usage=dict(input_tokens=u.get("prompt_tokens", 0), output_tokens=u.get("completion_tokens", 0)), provider=j.get("provider"), model=j.get("model"), or_cost=u.get("cost") or 0.0)
            return dict(custom_id=c["cid"], result=dict(type="succeeded", message=msg))
        except Exception as e:
            err = repr(e)[:200]
            if isinstance(e, urllib.error.HTTPError) and e.code == 402: log(f"402 Payment Required (OpenRouter credits exhausted): stopping"); os._exit(7); log(f"retry {c['cid']} {att} {err}"); time.sleep(20 * (att + 1))
    return dict(custom_id=c["cid"], result=dict(type="errored", error=err))
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); ap.add_argument("--only"); ap.add_argument("--cap", type=float, default=60.0)
    ap.add_argument("--workers", type=int, default=6); ap.add_argument("--tag", default="", help="retry1/retry2/nudge: separate results file"); ap.add_argument("--nudge", action="store_true"); ap.add_argument("--loc", action="store_true"); ap.add_argument("--spent-elsewhere", type=float, default=0.0, help="other redo spend counted against --cap (pilot)"); a = ap.parse_args()
    global LOC; LOC = a.loc
    D = tdir(a.model); T = ("." + a.tag) if a.tag else ""; SP = os.path.join(D, f"state{T}.json"); RP = os.path.join(D, f"results{T}.jsonl"); LOGP = os.path.join(D, "runner.log")
    def log(s): s = time.strftime("%Y-%m-%d %H:%M:%S ") + s; print(s, flush=True); open(LOGP, "a").write(s + "\n")
    st = json.load(open(SP)) if os.path.exists(SP) else dict(model=a.model, done={}, errors={}, spend_usd=0.0)
    if os.path.exists(RP):   # results.jsonl is the source of truth (state.json is only checkpointed every 25 rows)
        for l in open(RP):
            if not l.strip(): continue
            r = json.loads(l)
            if r["result"]["type"] == "succeeded" and r["custom_id"] not in st["done"]:
                c = r["result"]["message"]["or_cost"]; st["done"][r["custom_id"]] = round(c, 6); st["spend_usd"] += c
    cands, order = BT.queue()
    if a.only: keep = set(a.only.split(",")); order = [k for k in order if k in keep]
    todo = [k for k in order if k not in st["done"] and st["errors"].get(k, 0) < 2]
    log(f"start {a.model}: {len(todo)} rows, spend so far ${st['spend_usd']:.4f}, cap ${a.cap} (+${a.spent_elsewhere} elsewhere)")
    stop = [False]
    def one(k):
        with LK:
            if stop[0] or st["spend_usd"] + a.spent_elsewhere > a.cap - 0.5: stop[0] = True; return
        r = call(a.model, nudge(cands[k]) if a.nudge else cands[k], log)
        with LK:
            open(RP, "a").write(json.dumps(r) + "\n")
            if r["result"]["type"] == "succeeded":
                c = r["result"]["message"]["or_cost"]; st["spend_usd"] += c; st["done"][k] = round(c, 6)
            else: st["errors"][k] = st["errors"].get(k, 0) + 1
            if len(st["done"]) % 25 == 0: wjson(SP, st); log(f"done={len(st['done'])} spend=${st['spend_usd']:.4f}")
    with ThreadPoolExecutor(a.workers) as ex: list(ex.map(one, todo))
    wjson(SP, st); log(f"finished: done={len(st['done'])} errors={len(st['errors'])} spend=${st['spend_usd']:.4f}" + (" STOPPED AT CAP" if stop[0] else ""))
if __name__ == "__main__": main()
