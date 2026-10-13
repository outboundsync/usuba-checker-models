"""Round-0 generation for new models: same 49 clean prompts (messages[:-1]), same chat() (ZDR provider, temp 0, 16000 tok,
reasoning low/excluded, retries), costs charged to the shared spend.json ledger under HARD_STOP. usage: gen_new.py NAME=model ..."""
import json, os, sys, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uplift as U
def job(spec):
    name, model = spec.split("=")
    outp = os.path.join(U.H, name, "gen.jsonl"); os.makedirs(os.path.dirname(outp), exist_ok=True)
    have = {json.loads(l)["i"]: json.loads(l) for l in open(outp)} if os.path.exists(outp) else {}
    def one(i):
        if i in have: return
        h = U.rescore.hold[i]
        with U.asem:
            if not U.reserve(name, 0.3, None): print(name, i, "budget stop"); return
            try: out, fin, c, prov = U.chat(model, [dict(m) for m in h["messages"][:-1]])
            except U.ApiError as e: U.settle(name, 0.3, 0); print(name, i, "API error", str(e)[:120], flush=True); return
            U.settle(name, 0.3, c)
        with U.L: open(outp, "a").write(json.dumps({"i": i, "task": h["task"], "output": out, "finish": fin, "usage": {"cost": c}, "provider": prov}) + "\n")
        print(name, i, fin, f"${c:.3f} total ${U.state['spent']:.2f}", flush=True)
    with cf.ThreadPoolExecutor(12) as ex: list(ex.map(one, U.clean))
with cf.ThreadPoolExecutor(len(sys.argv) - 1) as ex: list(ex.map(job, sys.argv[1:]))
