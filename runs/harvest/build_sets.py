"""samples.jsonl -> verified.jsonl (shortest grader+sanity passing final answer per prompt) and repairs.jsonl
(failed answer, grader feedback, fixed passing answer) + stats.json (lengths vs train_v3)."""
import json, os, sys, collections, random
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, H); sys.path.insert(0, os.path.join(ROOT, "runs/clean"))
from tokenizers import Tokenizer
from loopdet import loopy
import sanity
src = open(os.path.join(ROOT, "runs/fixer/loop.py")).read(); ns = {"loopy": loopy}
exec(src[src.index("def feedback"):src.index("def grade")], ns); feedback = ns["feedback"]
TOK = Tokenizer.from_file(os.path.join(ROOT, "runs/clean_b/tokenizer.json")); ntok = lambda t: len(TOK.encode(t).ids)
P = {p["pid"]: p for p in map(json.loads, open(os.path.join(H, "prompts.jsonl")))}
S = [json.loads(l) for l in open(os.path.join(H, "samples.jsonl"))]
def prov(s, r): return {"model": s["model"], "prompt_id": s["pid"], "train_v3_index": s["train_i"], "sample": s["sample"], "round": r["round"],
                        "grader": s["grader"], "filters": "grader+filters", "system_prompt": "runs/fixer/sys_hand2.txt", "grader_version": "Omarchy 4.0.4", "timestamp": r["ts"], "temperature": s["temperature"], "reasoning": "low"}
best, reps, C = {}, [], collections.Counter()
for s in S:
    C["samples"] += 1; fin = s["rounds"][-1]
    if not fin["pass"]: C["sample-fail"] += 1; continue
    C["sample-grader-pass"] += 1
    fin["sanity_fails"] = sanity.check(fin["output"], fin["finish"]); fin["sane"] = not fin["sanity_fails"]
    if not fin["sane"]:
        C["sample-sanity-reject"] += 1
        for w in fin["sanity_fails"]: C["reject:" + w.split(":")[0]] += 1
        continue
    C["sample-kept"] += 1; t = ntok(fin["output"]); p = P[s["pid"]]
    row = {"messages": p["messages"] + [{"role": "assistant", "content": fin["output"]}], "task": s["task"], "answer_tokens": t, "provenance": prov(s, fin)}
    if s["pid"] not in best or t < best[s["pid"]]["answer_tokens"]: best[s["pid"]] = row
    if fin["round"] > 0:
        prev = s["rounds"][-2]
        fb = feedback({"categories": prev["categories"] or [], "static_fails": prev["static_fails"], "runtime_errors": prev["runtime_errors"], "soft": prev["soft"]}, prev["output"], prev["finish"])
        reps.append({"messages": p["messages"] + [{"role": "assistant", "content": prev["output"]}, {"role": "user", "content": fb},
                     {"role": "assistant", "content": fin["output"]}], "task": s["task"], "failed_round": prev["round"],
                     "grader_categories": prev["categories"], "failed_finish": prev["finish"], "failed_loop": prev["loop"],
                     "answer_tokens": t, "provenance": prov(s, fin)})
V = sorted(best.values(), key=lambda r: r["provenance"]["prompt_id"])
for name, rows in (("verified.jsonl", V), ("repairs.jsonl", reps)):
    with open(os.path.join(H, name), "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
def st(x):
    x = sorted(x); return {"n": len(x), "p50": x[len(x)//2], "p95": x[int(.95*len(x))], "max": x[-1], "mean": round(sum(x)/len(x))} if x else {}
tv = [ntok(json.loads(l)["messages"][2]["content"]) for l in open(os.path.join(ROOT, "v3/train_v3.jsonl"))]
tvf = [ntok(p["ref"]) for p in P.values()]
pr = collections.Counter(s["pid"] for s in S)
out = {"counts": dict(C), "prompts_attempted": len(pr), "prompts_full_N": sum(v >= 4 for v in pr.values()), "prompts_with_verified": len(V), "repairs": len(reps),
       "pass_by_round_samples": [sum(s["first_pass_round"] is not None and s["first_pass_round"] <= k for s in S) for k in range(4)],
       "spend_usage_cost": round(sum(s["cost"] for s in S), 2),
       "tokens": {"verified": st([r["answer_tokens"] for r in V]), "repairs_final": st([r["answer_tokens"] for r in reps]),
                  "train_v3_all": st(tv), "train_v3_same_prompts_ref": st(tvf),
                  "train_v3_ref_for_verified_prompts": st([ntok(P[r["provenance"]["prompt_id"]]["ref"]) for r in V])}}
json.dump(out, open(os.path.join(H, "stats.json"), "w"), indent=1); print(json.dumps(out, indent=1))
