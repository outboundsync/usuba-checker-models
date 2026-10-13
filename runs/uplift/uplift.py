#!/usr/bin/env python3
"""Checker uplift: round 0 = existing generation (graded by Usuba Checker v0.1); failing rows get up to 3 fix rounds where ONLY the
Checker's output goes back to the model. One process, shared OpenRouter spend ledger with a hard stop, <=6 concurrent grader runs.
usage: uplift.py NAME=openrouter_model=gen.jsonl[=budget] ...   writes runs/uplift/<NAME>/rows.jsonl incrementally."""
import json, os, re, sys, threading, time, urllib.request, urllib.error, concurrent.futures as cf
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, os.path.join(ROOT, "functest")); sys.path.insert(0, os.path.join(ROOT, "runs/clean")); sys.path.insert(0, os.path.join(ROOT, "runs/fixer"))
import rescore
from loopdet import loopy
HARD = float(os.environ.get("HARD_STOP", "29")); ROUNDS = 3
PROVIDER = {"zdr": True, "data_collection": "deny"}       # zero data retention: only ZDR endpoints, no prompt logging/training
clean = [json.loads(l)["holdout_i"] for l in open(os.path.join(ROOT, "clean/holdout_clean.jsonl"))]
gsem = threading.Semaphore(int(os.environ.get("GRADERS", "6"))); asem = threading.Semaphore(int(os.environ.get("API", "24")))
L = threading.Lock(); LEDGER = os.path.join(H, "spend.json")
state = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {"spent": 0.0, "by_model": {}}
reserved = [0.0]

def reserve(name, est, budget):
    with L:
        if state["spent"] + reserved[0] + est > HARD: return False
        if budget and state["by_model"].get(name, 0) + est > budget: return False
        reserved[0] += est; return True
def settle(name, est, cost):
    with L:
        reserved[0] -= est; state["spent"] += cost; state["by_model"][name] = state["by_model"].get(name, 0) + cost
        json.dump(state, open(LEDGER, "w"), indent=1)

def chat(model, msgs, mt=16000):
    b = {"model": model, "messages": msgs, "temperature": 0, "max_tokens": mt, "usage": {"include": True},
         "reasoning": {"effort": "low", "exclude": True}, "provider": PROVIDER}
    err = ""
    for a in range(3):
        try:
            q = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", json.dumps(b).encode(),
                {"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"], "Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(q, timeout=600)); c = d["choices"][0]
            return c["message"]["content"] or "", c["finish_reason"], (d.get("usage") or {}).get("cost", 0) or 0, d.get("provider")
        except urllib.error.HTTPError as e: err = f"HTTP {e.code} {e.read()[:200]!r}"; time.sleep(5)
        except Exception as e: err = str(e)[:200]; time.sleep(5)
    return "", "error:" + err, 0, None

def feedback(r, out, fin):
    Lx = []
    if fin == "length": Lx.append("Your answer was cut off at the token limit (truncated). Be much more concise; write only the files needed.")
    if loopy(out): Lx.append("Your answer degenerated into a repetition loop. Do not repeat content; write each file once, compactly.")
    if "no-files-parsed" in (r.get("categories") or []): Lx.append("No files could be parsed. Return every file as '### relative/path' followed by a fenced code block.")
    for s in (r.get("reasons") or r.get("static_fails") or []): Lx.append(s)
    seen = set()
    # the shell's own explanation for a load failure ("Plugin x has no barWidget entry point", QML errors) is logged as a warning;
    # without it "component never registered" is not actionable, so pass plugin-attributed shell warnings through as well
    soft = [e for e in (r.get("soft") or []) if re.search(r"Plugin |entry point|manifest|is not a type|Cannot assign|ReferenceError|TypeError|SyntaxError|file://|\.qml", e)]
    for e in (r.get("runtime_errors") or []) + soft:
        if e[:120] in seen: continue
        seen.add(e[:120]); Lx.append("runtime (real omarchy-shell 4.0.4): " + e)
    return ("Usuba Checker (Omarchy 4.0.4 plugin standard v0.1) rejected the answer:\n- " + "\n- ".join(Lx[:14]) +
            "\n\nFix every problem above. Return the corrected COMPLETE answer: every file in full as '### path' followed by a fenced code block.")

def grade(i, out, fin):
    with gsem:
        try: r = rescore.score_row(i, rescore.hold[i], {"output": out, "finish": fin})
        except Exception as e: r = {"pass_": False, "categories": ["grader-error"], "static_fails": [str(e)[:200]]}
    lp = loopy(out)
    return bool(r["pass_"]) and fin == "stop" and not lp, r, lp

def run(name, model, g0, budget, est, outp, i):
    h = rescore.hold[i]; out, fin = g0["output"], g0.get("finish", "stop")
    msgs = [dict(m) for m in h["messages"][:-1]]
    rounds = []; cost = 0; stopped = None
    for k in range(ROUNDS + 1):
        if k:
            with asem:                                   # reserve only once an API slot is held: at most API x est is ever reserved
                if not reserve(name, est, budget): stopped = "budget"; break
                out, fin, c, prov = chat(model, msgs)
                settle(name, est, c); cost += c
        ok, r, lp = grade(i, out, fin)
        rounds.append({"round": k, "output": out, "finish": fin, "pass": ok, "loop": lp, "categories": r.get("categories"),
                       "reasons": r.get("reasons"), "static_fails": r.get("static_fails"), "runtime_errors": r.get("runtime_errors"), "soft": r.get("soft"), "files": r.get("files")})
        if ok or k == ROUNDS: break
        msgs = msgs + [{"role": "assistant", "content": out if not lp and len(out) < 60000 else out[:8000] + "\n[... repetitive output removed ...]"},
                       {"role": "user", "content": feedback(r, out, fin)}]
    first = next((x["round"] for x in rounds if x["pass"]), None)
    rec = {"i": i, "task": h["task"], "first_pass_round": first, "cost": cost, "stopped": stopped, "rounds": rounds}
    with L: open(outp, "a").write(json.dumps(rec) + "\n")
    print(name, i, h["task"], "pass@", first, f"${cost:.3f}", stopped or "", f"total ${state['spent']:.2f}", flush=True)

def model_job(spec):
    name, model, gen = spec.split("=")[:3]; budget = float(spec.split("=")[3]) if spec.count("=") >= 3 else None
    G = [json.loads(l) for l in open(os.path.join(ROOT, gen))]
    if G and "rounds" in G[0]: G = {g["i"]: {"output": g["rounds"][0]["output"], "finish": g["rounds"][0]["finish"]} for g in G}
    else:
        if len(G) == 56: G = [G[i] for i in clean]   # full-holdout gen file -> the 49 clean prompts (same as score49.py)
        assert len(G) == 49, (name, len(G)); G = dict(zip(clean, G))
    c0 = [((g.get("usage") or {}).get("cost", 0) or 0) for g in G.values()]
    est = max(0.03, 1.5 * (sum(c0) / max(1, len(c0)))) if any(c0) else float(os.environ.get("EST_" + name.replace("-", "_").replace(".", "_"), "0.08"))
    os.makedirs(os.path.join(H, name), exist_ok=True); outp = os.path.join(H, name, "rows.jsonl")
    done = {json.loads(l)["i"] for l in open(outp)} if os.path.exists(outp) else set()
    with cf.ThreadPoolExecutor(12) as ex: list(ex.map(lambda i: run(name, model, G[i], budget, est, outp, i), [i for i in clean if i not in done]))
    R = [json.loads(l) for l in open(outp)]
    cum = [sum(r["first_pass_round"] is not None and r["first_pass_round"] <= k for r in R) for k in range(ROUNDS + 1)]
    s = f"{time.strftime('%H:%M')} {name} done n={len(R)} checker_pass_by_round={cum} cost=${sum(r['cost'] for r in R):.2f} stopped={sum(bool(r['stopped']) for r in R)}"
    print(s, flush=True); open(os.path.join(H, "STATUS.txt"), "a").write(s + "\n")
    return name

if __name__ == "__main__":
    with cf.ThreadPoolExecutor(len(sys.argv) - 1) as ex:
        for n in cf.as_completed([ex.submit(model_job, s) for s in sys.argv[1:]]):
            nm = n.result()
            os.system(f"cd {ROOT} && git add runs/uplift/{nm} runs/uplift/STATUS.txt runs/uplift/spend.json && git -c user.name='Harris Kenny' -c user.email=osiharris@users.noreply.github.com commit -qm 'uplift: {nm} done' >/dev/null 2>&1")
