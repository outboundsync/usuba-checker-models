#!/usr/bin/env python3
"""Rejection-sampling harvest: for each train prompt, N independent samples of stock qwen/qwen3.6-27b through the
runs/fixer feedback loop (gen -> functest grader -> grader errors fed back, up to ROUNDS fix rounds).
Writes one JSON line per (prompt, sample) to samples.jsonl incrementally. Hard spend cap via OpenRouter usage.cost.
usage: harvest.py [N=4] [ROUNDS=3] [CAP=21]"""
import json, os, sys, threading, time, random, urllib.request, concurrent.futures as cf
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, os.path.join(ROOT, "functest")); sys.path.insert(0, os.path.join(ROOT, "runs/clean")); sys.path.insert(0, H)
import importlib.util
import rescore, sanity
SYSP = open(os.path.join(ROOT, "runs/fixer/sys_hand2.txt")).read().strip()
from loopdet import loopy
# reuse the fixer's feedback text verbatim without executing loop.py's main (copy of runs/fixer/loop.py:feedback)
src = open(os.path.join(ROOT, "runs/fixer/loop.py")).read()
ns = {"loopy": loopy}; exec(src[src.index("def feedback"):src.index("def grade")], ns); feedback = ns["feedback"]
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4; ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
CAP = float(sys.argv[3]) if len(sys.argv) > 3 else 21.0
MODEL = "qwen/qwen3.6-27b"; GRADER = "functest@" + rescore.FT_VERSION + " (Omarchy 4.0.4)"
P = [json.loads(l) for l in open(os.path.join(H, "prompts.jsonl"))]
random.Random(0).shuffle(P)
outp = os.path.join(H, "samples.jsonl"); lock = threading.Lock(); gsem = threading.Semaphore(os.cpu_count() or 8)
done = {(r["pid"], r["sample"]) for r in map(json.loads, open(outp))} if os.path.exists(outp) else set()
spend = [sum(json.loads(l)["cost"] for l in open(outp)) if os.path.exists(outp) else 0.0]
def status(s):
    with lock: open(os.path.join(H, "STATUS.txt"), "a").write(time.strftime("%m-%d %H:%M ") + s + "\n")

def chat(msgs):
    b = {"model": MODEL, "messages": msgs, "temperature": 0.7, "max_tokens": 16000, "usage": {"include": True},
         "reasoning": {"effort": "low", "exclude": True}, "provider": {"sort": "throughput"}}
    err = ""
    for a in range(2):   # 1 retry
        try:
            q = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", json.dumps(b).encode(),
                {"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"], "Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(q, timeout=240)); c = d["choices"][0]
            cost = (d.get("usage") or {}).get("cost", 0) or 0
            with lock: spend[0] += cost
            return c["message"]["content"] or "", c["finish_reason"], cost, (d.get("usage") or {}).get("completion_tokens")
        except Exception as e: err = str(e)[:200]
    return "", "error:" + err, 0, None

def grade(h, out, fin):
    with gsem:
        try: r = rescore.score_row(0, h, {"output": out, "finish": fin})
        except Exception as e: r = {"pass_": False, "categories": ["grader-error"], "static_fails": [str(e)[:200]]}
    lp = loopy(out)
    return bool(r["pass_"]) and fin == "stop" and not lp, r, lp

def run(job):
    p, s = job
    if (p["pid"], s) in done or spend[0] >= CAP: return
    h = {"task": p["task"], "messages": p["messages"] + [{"role": "assistant", "content": p["ref"]}], "meta": p["meta"]}
    msgs = [{"role": "system", "content": SYSP}, dict(p["messages"][1])]; rounds = []; cost = 0
    for k in range(ROUNDS + 1):
        if k and spend[0] >= CAP + 2: break
        out, fin, c, ct = chat(msgs); cost += c
        ok, r, lp = grade(h, out, fin)
        san = sanity.check(out, fin) if ok else None
        rounds.append({"round": k, "output": out, "finish": fin, "completion_tokens": ct, "pass": ok, "sane": san == [], "sanity_fails": san,
                       "loop": lp, "categories": r.get("categories"), "static_fails": r.get("static_fails"),
                       "runtime_errors": r.get("runtime_errors"), "soft": r.get("soft"), "files": r.get("files"), "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
        if ok or k == ROUNDS: break
        msgs = msgs + [{"role": "assistant", "content": out if not lp and len(out) < 60000 else out[:8000] + "\n[... repetitive output removed ...]"},
                       {"role": "user", "content": feedback(r, out, fin)}]
    first = next((x["round"] for x in rounds if x["pass"]), None)
    rec = {"pid": p["pid"], "train_i": p["train_i"], "task": p["task"], "sample": s, "model": MODEL, "grader": GRADER,
           "temperature": 0.7, "system_prompt": "runs/fixer/sys_hand2.txt", "filters": "grader+filters", "first_pass_round": first, "cost": cost, "rounds": rounds}
    with lock:
        open(outp, "a").write(json.dumps(rec) + "\n")
    print(p["pid"], s, "pass@", first, f"${cost:.3f} total=${spend[0]:.2f}", flush=True)

jobs = [(p, s) for p in P for s in range(N)]
status(f"harvest start prompts={len(P)} N={N} rounds={ROUNDS} cap=${CAP} resume_done={len(done)} spend=${spend[0]:.2f}")
t0 = time.time(); ndone = [0]
def tick(_):
    ndone[0] += 1
    if ndone[0] % 100 == 0: status(f"harvest progress {ndone[0]}/{len(jobs)} jobs spend=${spend[0]:.2f}")
with cf.ThreadPoolExecutor(64) as ex:
    for f in [ex.submit(run, j) for j in jobs]: f.add_done_callback(tick)
R = [json.loads(l) for l in open(outp)]
status(f"harvest done samples={len(R)} prompts={len({r['pid'] for r in R})} passed={sum(r['first_pass_round'] is not None for r in R)} spend=${spend[0]:.2f} wall={time.time()-t0:.0f}s")
