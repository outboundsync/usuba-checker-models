"""Shared paths + helpers for the v2 distillation data build (Sonnet 5.5 low effort via Anthropic Message Batches)."""
import json, os, re, sys
H = os.path.dirname(os.path.abspath(__file__)); V2 = os.path.dirname(H); TR = os.path.dirname(V2); ROOT = os.path.dirname(TR)
sys.path[:0] = [TR, V2, os.path.join(ROOT, "functest"), os.path.join(ROOT, "hancore"), os.path.join(ROOT, "eval", "hancore_holdout")]
WORK = os.environ.get("DISTILL_WORK", "/workspace/v2distill")
MODEL = "claude-sonnet-5-5"; EFFORT = "low"; MAX_TOKENS = 16000
PRICE_IN, PRICE_OUT = 1.0, 5.0          # USD per 1M tokens, Message Batches rate (50% of $2/$10)
ROW_TOKEN_CAP = 32768
SPEND_CAP = float(os.environ.get("DISTILL_SPEND_CAP", "110"))   # Harris raised $60 -> $110 on 2026-10-14
def jl(p): return [json.loads(l) for l in open(p) if l.strip()]
def wjl(p, rows):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, p)
def wjson(p, o):
    tmp = p + ".tmp"; json.dump(o, open(tmp, "w"), indent=1); os.replace(tmp, p)
