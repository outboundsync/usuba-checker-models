#!/usr/bin/env python3
"""Small GEPA-style system-prompt optimisation on a TRAIN split (train_v3 build_from_spec rows whose plugin
(repo+path) never appears in the 49 holdout). Candidate prompts are scored round-0 only; a reflection model reads
grader failures (train only) and rewrites the prompt. usage: gepa.py ITERS NTRAIN"""
import json, os, sys, re, random, hashlib, time, threading, urllib.request, concurrent.futures as cf
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, os.path.join(ROOT, "functest")); sys.path.insert(0, os.path.join(ROOT, "validator")); sys.path.insert(0, os.path.join(ROOT, "runs/clean"))
import functest; from build_parse import parse; from loopdet import loopy
ITERS, NTR = int(sys.argv[1]), int(sys.argv[2]); REFL = os.environ.get("REFL", "z-ai/glm-5.3")
hold = [json.loads(l) for l in open(os.path.join(ROOT, "data/holdout.jsonl"))]
hk = {(h["meta"]["repo"], h["meta"]["plugin_path"].strip("/")) for h in hold}
tr = [json.loads(l) for l in open(os.path.join(ROOT, "runs/q27/train_v3.jsonl"))]
tr = [r for r in tr if r["task"] == "build_from_spec" and (r["meta"].get("repo"), str(r["meta"].get("plugin_path", "")).strip("/")) not in hk]
random.Random(0).shuffle(tr); tr = tr[:NTR]
D = os.path.join(H, "gepa"); os.makedirs(D, exist_ok=True); LOG = open(os.path.join(D, "log.jsonl"), "a"); gsem = threading.Semaphore(8); spend = [0.0]
def call(model, msgs, mt=16000, reasoning=True):
    b = {"model": model, "messages": msgs, "temperature": 0, "max_tokens": mt, "usage": {"include": True}}
    if reasoning: b["reasoning"] = {"effort": "low", "exclude": True}
    for a in range(2):
        try:
            q = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", json.dumps(b).encode(),
                {"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"], "Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(q, timeout=240)); c = d["choices"][0]; spend[0] += (d.get("usage") or {}).get("cost", 0) or 0
            return c["message"]["content"] or "", c["finish_reason"]
        except Exception as e: err = str(e)[:200]
    return "", "error:" + err
CD = os.path.join(D, "cache"); os.makedirs(CD, exist_ok=True)
def ev1(sp, r):
    ck = os.path.join(CD, hashlib.sha1((sp + "\x00" + r["messages"][1]["content"]).encode()).hexdigest() + ".json")
    if os.path.exists(ck): out, fin = json.load(open(ck))
    else:
        out, fin = call("qwen/qwen3.6-27b", [{"role": "system", "content": sp}, r["messages"][1]])
        if not fin.startswith("error"): json.dump([out, fin], open(ck, "w"))
    files = parse(out)
    with gsem: res = functest.test(files=files) if files else {"pass": False, "static_fails": [["no-files-parsed", ""]], "runtime": None}
    lp = loopy(out); ok = bool(res["pass"]) and fin == "stop" and not lp
    errs = [f"{a}: {b}"[:200] for a, b in res["static_fails"]][:6] + [e[:200] for e in ((res.get("runtime") or {}).get("errors") or [])][:6]
    if fin == "length": errs.append("TRUNCATED at 16k tokens")
    if lp: errs.append("REPETITION LOOP")
    return {"ok": ok, "errs": errs, "partial": ok + 0.3 * (not res["static_fails"]) + 0.2 * (fin == "stop" and not lp), "spec": r["messages"][1]["content"][:600], "files": sorted(files)[:10]}
def ev(sp):
    ex = cf.ThreadPoolExecutor(len(tr)); fs = [ex.submit(ev1, sp, r) for r in tr]
    cf.wait(fs, timeout=900); ex.shutdown(wait=False, cancel_futures=True)
    R = [f.result() if f.done() and not f.exception() else {"ok": False, "errs": ["timeout"], "partial": 0, "spec": r["messages"][1]["content"][:600], "files": []} for f, r in zip(fs, tr)]
    return sum(x["ok"] for x in R), sum(x["partial"] for x in R), R
def reflect(sp, R):
    fails = [x for x in R if not x["ok"]][:12]
    txt = "\n\n".join(f"TASK: {x['spec']}\nFILES: {x['files']}\nGRADER: " + "; ".join(x["errs"]) for x in fails)
    m = [{"role": "user", "content": "You are optimising the SYSTEM PROMPT of a 27B code model that writes Omarchy 4.0.4 (Quickshell QML) plugins. "
          "Below is the current system prompt, then train tasks it failed with the automated grader's errors (real omarchy-shell runtime + static checks). "
          "Diagnose the recurring failure patterns and write an improved system prompt that prevents them (concrete rules, correct APIs/modules, conciseness). "
          "The model is also used inside a fixer loop that feeds these same grader errors back to it, so rules that make errors self-explaining help too. Keep everything in the current prompt that is correct (especially the allowed-binaries list, verbatim). Do not add task-specific answers. "
          "Return ONLY the new system prompt between <prompt> and </prompt>.\n\n=== CURRENT PROMPT ===\n" + sp + "\n\n=== FAILURES ===\n" + txt}]
    out, fin = call(REFL, m, 12000)
    mm = re.search(r"<prompt>(.*?)</prompt>", out, re.S)
    return mm.group(1).strip() if mm else None
best = hold[0]["messages"][0]["content"].strip(); t0 = time.time()
bs, bp, bR = ev(best); open(os.path.join(H, "STATUS.txt"), "a").write(f"{time.strftime('%H:%M')} gepa seed(base prompt) train={bs}/{len(tr)} partial={bp:.1f}\n"); print("seed", bs, round(bp, 1), f"${spend[0]:.2f}", flush=True)
LOG.write(json.dumps({"it": 0, "score": bs, "partial": bp, "prompt": best}) + "\n"); LOG.flush()
for it in range(1, ITERS + 1):
    cand = reflect(best, bR)
    if not cand: print("reflect failed", flush=True); continue
    s, p, R = ev(cand); acc = (s, p) > (bs, bp)
    print("it", it, s, round(p, 1), "accept" if acc else "reject", f"${spend[0]:.2f}", f"{time.time()-t0:.0f}s", flush=True)
    LOG.write(json.dumps({"it": it, "score": s, "partial": p, "accepted": acc, "prompt": cand}) + "\n"); LOG.flush()
    open(os.path.join(H, "STATUS.txt"), "a").write(f"{time.strftime('%H:%M')} gepa it{it} train={s}/{len(tr)} partial={p:.1f} {'accept' if acc else 'reject'} spend=${spend[0]:.2f}\n")
    if acc: best, bs, bp, bR = cand, s, p, R
open(os.path.join(H, "sys_gepa.txt"), "w").write(best + "\n")
s = f"{time.strftime('%H:%M')} gepa done train={len(tr)} best_train={bs}/{len(tr)} spend=${spend[0]:.2f}"
print(s); open(os.path.join(H, "STATUS.txt"), "a").write(s + "\n")
