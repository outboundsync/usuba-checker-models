#!/usr/bin/env python3
"""Model+fixer loop on the 49 clean holdout. usage: loop.py VARIANT [sysprompt.txt|base] [rounds=3]
Each prompt: gen (round 0) -> functest grader -> if fail, feed grader error text back -> up to N fix rounds.
Only grader output is ever shown to the model (no reference answers). Writes VARIANT/rows.jsonl incrementally."""
import json, os, sys, threading, time, urllib.request, concurrent.futures as cf
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, os.path.join(ROOT, "functest")); sys.path.insert(0, os.path.join(ROOT, "runs/clean"))
import rescore
from loopdet import loopy
VAR = sys.argv[1]; SP = sys.argv[2] if len(sys.argv) > 2 else "base"; ROUNDS = int(sys.argv[3]) if len(sys.argv) > 3 else 3
MODEL = os.environ.get("MODEL", "qwen/qwen3.6-27b")
HOLD = os.environ.get("HOLD")  # optional alternative prompt set (jsonl with messages[, task]) for GEPA train split
clean = [json.loads(l)["holdout_i"] for l in open(os.path.join(ROOT, "clean/holdout_clean.jsonl"))]
sysp = None if SP == "base" else open(SP).read().strip()
os.makedirs(os.path.join(H, VAR), exist_ok=True)
outp = os.path.join(H, VAR, "rows.jsonl"); lock = threading.Lock(); gsem = threading.Semaphore(8)
done = {json.loads(l)["i"] for l in open(outp)} if os.path.exists(outp) else set()

def chat(msgs):
    b = {"model": MODEL, "messages": msgs, "temperature": 0, "max_tokens": 16000, "usage": {"include": True},
         "reasoning": {"effort": "low", "exclude": True}, "provider": {"sort": "throughput"}}
    err = ""
    for a in range(2):
        try:
            q = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", json.dumps(b).encode(),
                {"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"], "Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(q, timeout=240)); c = d["choices"][0]
            return c["message"]["content"] or "", c["finish_reason"], (d.get("usage") or {}).get("cost", 0) or 0
        except Exception as e: err = str(e)[:200]
    return "", "error:" + err, 0

def feedback(r, out, fin):
    L = []
    if fin == "length": L.append("Your answer was cut off at the token limit (truncated). Be much more concise; write only the files needed.")
    if loopy(out): L.append("Your answer degenerated into a repetition loop. Do not repeat content; write each file once, compactly.")
    if "no-files-parsed" in r["categories"]: L.append("No files could be parsed. Return every file as '### relative/path' followed by a fenced code block.")
    for s in r.get("static_fails") or []: L.append("static check: " + s)
    seen = set()
    for e in (r.get("runtime_errors") or []) + (r.get("soft") or []):
        k = e[:120]
        if k in seen: continue
        seen.add(k); L.append("runtime (real omarchy-shell 4.0.4 on the target machine): " + e)
    return ("The plugin failed automated testing on the target Omarchy 4.0.4 machine. Grader output:\n- " + "\n- ".join(L) +
            "\n\nFix every problem above. Ship every helper script or file you reference, only call binaries that exist on the machine, "
            "only import modules that exist (Quickshell*, QtQuick*, qs.Commons, qs.Ui). Return the corrected COMPLETE answer: every file in full "
            "as '### path' followed by a fenced code block, nothing omitted.")

def grade(i, out, fin):
    with gsem:
        try: r = rescore.score_row(i, rescore.hold[i], {"output": out, "finish": fin})
        except Exception as e: r = {"task": rescore.hold[i]["task"], "pass_": False, "categories": ["grader-error"], "static_fails": [str(e)[:200]]}
    lp = loopy(out)
    ok = bool(r["pass_"]) and fin == "stop" and not lp
    return ok, r, lp

def run(i):
    if i in done: return
    h = rescore.hold[i]; msgs = [dict(m) for m in h["messages"][:-1]]
    if sysp: msgs[0] = {"role": "system", "content": sysp}
    rounds = []; cost = 0
    for k in range(ROUNDS + 1):
        out, fin, c = chat(msgs); cost += c
        ok, r, lp = grade(i, out, fin)
        rounds.append({"round": k, "output": out, "finish": fin, "pass": ok, "loop": lp, "categories": r.get("categories"),
                       "static_fails": r.get("static_fails"), "runtime_errors": r.get("runtime_errors"), "soft": r.get("soft"), "files": r.get("files")})
        if ok or k == ROUNDS: break
        msgs = msgs + [{"role": "assistant", "content": out if not lp and len(out) < 60000 else out[:8000] + "\n[... repetitive output removed ...]"},
                       {"role": "user", "content": feedback(r, out, fin)}]
    first = next((x["round"] for x in rounds if x["pass"]), None)
    rec = {"i": i, "task": h["task"], "first_pass_round": first, "cost": cost, "rounds": rounds}
    with lock:
        open(outp, "a").write(json.dumps(rec) + "\n")
        open(os.path.join(H, "STATUS.txt"), "a").write(f"{time.strftime('%H:%M')} {VAR} i={i} {h['task']} pass_round={first} ${cost:.3f}\n") if False else None
    print(VAR, i, h["task"], "pass@", first, f"${cost:.3f}", flush=True)

t0 = time.time()
with cf.ThreadPoolExecutor(49) as ex: list(ex.map(run, clean))
R = [json.loads(l) for l in open(outp)]
cum = [sum(r["first_pass_round"] is not None and r["first_pass_round"] <= k for r in R) for k in range(ROUNDS + 1)]
s = f"{time.strftime('%H:%M')} {VAR} done n={len(R)} pass_by_round={cum} cost=${sum(r['cost'] for r in R):.2f} wall={time.time()-t0:.0f}s"
print(s); open(os.path.join(H, "STATUS.txt"), "a").write(s + "\n")
