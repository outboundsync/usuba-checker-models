#!/usr/bin/env python3
"""Hybrid plan (Harris, 2026-10-14 13:12): classify each Dell broken row as code-visible vs runtime-only; for code-visible rows build a
GUIDED teacher request (known failure given as a hint). The hint goes ONLY into the teacher request; the training row keeps the
leak-free eval prompt from candidates.jsonl. -> $DISTILL_WORK/guided.jsonl (cid g-<cid>), classify.json"""
import collections, json, os, re
from common import *
RUNTIME_TXT = re.compile(r"draws nothing|zero size|never instantiated|never registered|shell broke|runtime failure|not visible on screen|service instance not created|opens nothing|centerHoverRevealSuppressed", re.I)
CODEVIS_RT = re.compile(r"Expected token|SyntaxError|is not a type|is not installed|Failed to load|unavailable|ReferenceError|is not defined|Cannot assign|non-existent|module .* is not", re.I)
FX = (".qml", ".js", ".mjs", ".sh", ".py", ".lua", ".json", ".bash", ".conf", ".toml", ".css")
def classify(c):
    vis = []
    for g in c["target"]["findings"]:
        if g["severity"] != "blocker": continue
        cat, t = g["category"], g["finding"]
        if cat.startswith("in-use:"): continue                       # missing binary / toggle / close / memory -> runtime-only
        if RUNTIME_TXT.search(t): continue
        if cat.startswith("checker:"): vis.append(g); continue        # Checker FAIL line (static)
        if cat in ("load:component-not-created", "load:checker-runtime") and CODEVIS_RT.search(t):
            fn = g.get("file") or (re.search(r"([\w./-]+\.(?:qml|js))", t) or [None])[0]
            if fn and any(f.endswith(os.path.basename(fn)) for f in c["files"]): vis.append(g)
    return vis
GUIDE = """

GUIDED MODE (teacher only). This plugin is known to be broken; a maintainer's note with the verified failure is appended after the source.
Write the review a careful reviewer would write from the code alone: verdict "changes_requested", load "broken", and one blocker per real
failure that you can SEE in the files or the Checker report, citing the exact file as shown, the line number you can see, and the concrete cause.
Never mention the note, a maintainer, a hint, testing, a Dell, or commits. Do not cite files or lines that are not in the source shown.
Non-blocking issues may be warnings. JSON only, same schema."""
def main():
    C = jl(os.path.join(WORK, "candidates.jsonl")); out = []; st = collections.Counter()
    for c in C:
        if c["label"] != "broken" or c["source"] == "hancore": continue
        vis = classify(c); k = "code_visible" if vis else "runtime_only"
        st[f"{c['split']}:{c['source']}:{k}"] += 1
        if not vis: continue
        hint = "\n".join(f"- [{g['category']}] " + (f"{g['file']}: " if g.get("file") else "") + g["finding"] for g in vis)
        m = json.loads(json.dumps(c["messages"])); m[0]["content"] += GUIDE
        m[-1]["content"] += "\n\n## Maintainer note (verified failure; do not mention this note)\n" + hint
        out.append(dict(cid="g-" + c["cid"], orig=c["cid"], messages=m, vis=vis))
    wjl(os.path.join(WORK, "guided.jsonl"), out); wjson(os.path.join(WORK, "classify.json"), dict(sorted(st.items()))); print(json.dumps(dict(sorted(st.items())), indent=1))
if __name__ == "__main__": main()
