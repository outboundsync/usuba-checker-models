"""Build runs/uplift/results.csv (one row per model x prompt) from <model>/rows.jsonl + handcheck.json, and write each first and final
answer's files under <model>/answers/<i>/attempt<k>/ so every row points at real files. Charts read ONLY results.csv.
category (code definitions):
  works right away : Checker pass on the first answer AND hand_first == accept
  fixed by Checker : not the above, a later answer passes the Checker AND hand_final == accept
  fully broken     : no Checker pass; the final answer does not load (category in LOAD_FAIL, or no files parsed)
  still buggy      : everything else (loads but Checker errors remain, or Checker pass rejected by hand)
  unchecked        : Checker pass whose hand verdict is not recorded yet (never filled in automatically)"""
import json, os, csv, sys
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, os.path.join(ROOT, "functest")); import rescore
LOAD_FAIL = {"no-files-parsed", "manifest", "entry-not-qml", "no-qml", "not-shell-surface", "bad-import", "qt5-api", "qml-syntax",
             "usuba-USB-T01", "usuba-USB-T02", "usuba-USB-Q01", "usuba-USB-A03",
             "rt-load-failed", "rt-unresolved-type/import", "rt-not-instantiated", "rt-manifest-rejected", "rt-qml-syntax", "rt-shell-broken"}
MODELS = [("Frontier", "gpt-5.6-sol"), ("Frontier", "claude-opus-5.5"), ("Frontier", "claude-sonnet-5.5"), ("Frontier", "gemini-3.1-pro"), ("Frontier", "grok-4.3"),
          ("Open", "qwen3.6-27b"), ("Open", "qwen3-coder"), ("Open", "kimi-k3"), ("Open", "deepseek-v4-pro")]
HC = json.load(open(os.path.join(H, "handcheck.json"))) if os.path.exists(os.path.join(H, "handcheck.json")) else {}
def dump(m, i, k, out):
    d = os.path.join(H, m, "answers", str(i), f"attempt{k}")
    if not os.path.isdir(d):
        for p, c in rescore.parse(out).items():
            if ".." in p or p.startswith("/"): continue
            os.makedirs(os.path.dirname(os.path.join(d, p)), exist_ok=True); open(os.path.join(d, p), "w").write(c)
        os.makedirs(d, exist_ok=True)
    return os.path.relpath(d, ROOT)
rows = []
for grp, m in MODELS:
    p = os.path.join(H, m, "rows.jsonl")
    R = {json.loads(l)["i"]: json.loads(l) for l in open(p)} if os.path.exists(p) else {}
    hc = HC.get(m, {})
    for r in R.values():
        fp = r["first_pass_round"]; last = fp if fp is not None else len(r["rounds"]) - 1; fin = r["rounds"][last]
        h = hc.get(str(r["i"]), {})
        hf = h.get("first", "") if fp == 0 else ""; hl = h.get("final", "") if fp is not None else ""
        if fp == 0 and hf == "accept": cat = "works right away"
        elif fp is not None and hl == "accept": cat = "fixed by Checker" if fp > 0 else "works right away"
        elif fp is not None and (hl == "" if fp else hf == ""): cat = "unchecked"
        elif fp is None and (set(fin.get("categories") or []) & LOAD_FAIL or not fin.get("files")): cat = "fully broken"
        else: cat = "still buggy"
        rows.append(dict(group=grp, model=m, prompt_id=r["i"], task=r["task"], category=cat,
                         checker_first="pass" if r["rounds"][0]["pass"] else "fail", checker_final="pass" if fp is not None else "fail",
                         passing_attempt="" if fp is None else fp, attempts=len(r["rounds"]), final_finish=fin["finish"], final_loop=fin["loop"],
                         final_checker_categories=";".join(fin.get("categories") or []),
                         hand_first=hf, hand_final=hl, hand_note=h.get("note", ""), fix_cost_usd=round(r["cost"], 5),
                         first_answer_path=dump(m, r["i"], 0, r["rounds"][0]["output"]), final_answer_path=dump(m, r["i"], last, fin["output"])))
rows.sort(key=lambda x: (x["group"], x["model"], x["prompt_id"]))
with open(os.path.join(H, "results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
import collections
for grp, m in MODELS:
    c = collections.Counter(x["category"] for x in rows if x["model"] == m)
    print(f"{m:20} n={sum(c.values()):2}", dict(c))
