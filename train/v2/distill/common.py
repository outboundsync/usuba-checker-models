"""Shared paths + helpers for the v2 distillation data build (open-weights teacher via OpenRouter; see TEACHER.md)."""
import json, os, re, sys
H = os.path.dirname(os.path.abspath(__file__)); V2 = os.path.dirname(H); TR = os.path.dirname(V2); ROOT = os.path.dirname(TR)
sys.path[:0] = [TR, V2, os.path.join(ROOT, "functest"), os.path.join(ROOT, "hancore"), os.path.join(ROOT, "eval", "hancore_holdout")]
WORK = os.environ.get("DISTILL_WORK", "/workspace/v2distill")
MAX_TOKENS = 16000
ROW_TOKEN_CAP = 32768
def jl(p): return [json.loads(l) for l in open(p) if l.strip()]
def wjl(p, rows):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, p)
def wjson(p, o):
    tmp = p + ".tmp"; json.dump(o, open(tmp, "w"), indent=1); os.replace(tmp, p)
