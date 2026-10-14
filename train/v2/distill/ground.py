"""Deterministic grounding checks for teacher blockers: the cited line (±5) in the cited file must contain a token (backticked or identifier-like, len>=4) from the finding;
and when the verified failure carries a line (`[316:`, `line 316`), the matching review blocker must cite a line within 15 of it."""
import re
from assemble import file_lines
def files_text(c):
    u = c["messages"][-1]["content"]; return {m.group(1): m.group(2).split("\n") for m in re.finditer(r"^### (.+?)\n```\n(.*?)\n```$", u, re.S | re.M)}
STOP = {"this", "that", "with", "which", "when", "will", "from", "were", "does", "have", "script", "plugin", "stock", "omarchy", "ship", "shipped", "file", "line", "declared", "dependency", "dependencies", "missing", "error", "causing", "fails", "users"}
def toks(s):
    t = re.findall(r"`([^`]{3,80})`", s)
    out = set()
    for x in t: out.add(x); out.update(w for w in re.split(r"[^\w.-]+", x) if len(w) >= 4)
    return {x for x in out if x.lower() not in STOP}
def grounded(c, f):
    """None if no line to check, else bool"""
    ln, fn = f.get("line"), f.get("file")
    if not isinstance(ln, int) or not fn: return None
    FT = files_text(c); hit = [p for p in FT if p == fn or p.endswith("/" + fn)]
    if not hit: return False
    L = FT[hit[0]]; win = "\n".join(L[max(0, ln - 6): ln + 5]); T = toks(f.get("finding", ""))
    if not T: T = {w for w in re.findall(r"\b[A-Za-z_][\w.]{5,}\b", f.get("finding", "")) if w.lower() not in STOP and re.search(r"[A-Z_.]", w)}
    if not T: return None
    return any(t in win for t in T)
def gold_lines(vis):
    out = []
    for g in vis:
        m = re.search(r"\[(\d+):-?\d+\]|line (\d+)", g["finding"])
        if m: out.append((g.get("file") or (re.search(r"([\w./-]+\.(?:qml|js))", g["finding"]) or [None, None])[1], int(m.group(1) or m.group(2))))
    return out
def line_ok(vis, out):
    GL = gold_lines(vis)
    if not GL: return True
    for fn, ln in GL:
        for f in out.get("findings") or []:
            if not isinstance(f, dict) or str(f.get("severity")).lower() != "blocker": continue
            if isinstance(f.get("line"), int) and abs(f["line"] - ln) <= 15 and (not fn or not f.get("file") or fn.lower().endswith(str(f["file"]).lower()) or str(f["file"]).lower().endswith(fn.lower())): return True
    return False

def repair(c, out):
    """Deterministic fix-up of cited line numbers (teachers often cite a wrong line): move each blocker's line to the nearest line in the cited file that contains a
    token from the finding. A blocker whose backticked tokens appear nowhere in the cited file is ungrounded -> reason string. Edits `out` in place."""
    FT = files_text(c)
    for f in out.get("findings") or []:
        if not isinstance(f, dict) or str(f.get("severity")).lower() != "blocker" or not f.get("file"): continue
        hit = [p for p in FT if p == f["file"] or p.endswith("/" + f["file"])]
        if not hit: return "ungrounded_blocker"
        L = FT[hit[0]]; bt = toks(f.get("finding", ""))
        T = bt or {w for w in re.findall(r"\b[A-Za-z_][\w.]{5,}\b", f.get("finding", "")) if w.lower() not in STOP and re.search(r"[A-Z_.]", w)}
        occ = [i + 1 for i, s in enumerate(L) if any(t in s for t in T)]
        if not occ:
            if bt: return "ungrounded_blocker"
            continue
        if isinstance(f.get("line"), int): f["line"] = min(occ, key=lambda n: abs(n - f["line"]))
    return None
