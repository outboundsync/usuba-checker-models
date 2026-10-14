"""Teacher request body + the approved hybrid queue (blind works/fix rows, guided code-visible broken rows). Provider-neutral."""
import hashlib, json, os
from common import *
def body(c):
    sysm = "\n\n".join(m["content"] for m in c["messages"] if m["role"] == "system")
    return dict(system=sysm, messages=[m for m in c["messages"] if m["role"] != "system"])
def queue():
    """the approved hybrid queue (used by or_teacher.py): works/fix rows (train works capped) + guided code-visible broken rows; no blind broken rows"""
    cands = {c["cid"]: c for c in jl(os.path.join(WORK, "candidates.jsonl"))}
    # hybrid plan (Harris 13:12): broken rows are not distilled blind; code-visible Dell broken rows go as guided requests (g-<cid>),
    # runtime-only rows and HANCORE are not sent. Working rows: train works capped at WORKS_QUOTA (the approve-share trim drops the rest).
    G = {g["cid"]: dict(g, split="guided", source="guided", label="broken") for g in jl(os.path.join(WORK, "guided.jsonl"))} if os.path.exists(os.path.join(WORK, "guided.jsonl")) else {}
    cands = {k: c for k, c in cands.items() if c["label"] == "works" and c["source"] != "fix_model"}   # fix_model rows were written by proprietary models: excluded
    wk = sorted((k for k, c in cands.items() if c["split"] == "train" and c["source"] == "dell_works_verified"), key=lambda k: hashlib.sha1(("order:" + k).encode()).hexdigest())
    for k in wk[int(os.environ.get("WORKS_QUOTA", "1250")):]: del cands[k]
    cands.update(G)
    # tier 0: val + every broken row + fix pairs (the teacher matters most there); tier 1: train works rows in random order
    # (spend cap: works rows the budget does not reach keep their grader-verified templated approve target). Random within a tier.
    tier = lambda c: 1 if (c["split"] == "train" and c["source"] == "dell_works_verified") else 0
    order = sorted(cands, key=lambda k: (tier(cands[k]), hashlib.sha1(("order:" + k).encode()).hexdigest()))
    return cands, order
