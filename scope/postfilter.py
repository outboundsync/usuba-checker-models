"""Inference post-filter for the Checker model (release 1, advisory).

  * drop any DISMISSAL whose quote is not in the cited file  -> the finding reverts to ``confirm`` (the Checker scripts stand)
  * drop any ADDED FINDING whose quote is not in the cited file, whose file does not exist, or that repeats a Checker scripts finding (same file and line) or an earlier added finding
  * runtime-stage fails cannot be dismissed (policy): a dismissal of one reverts to ``confirm`` whatever the quote
  * the System verdict is the Checker scripts' verdict; the model verdict is kept next to it as ``model_verdict``

Quote matching is exact after CRLF normalisation and after removing a copied ``  12| `` line-number prefix; a quote needs at least MIN_QUOTE non-blank characters
so that `}` or `end` cannot ground anything. Pure functions, no I/O.
"""
import re

MIN_QUOTE = 6
_PREFIX = re.compile(r"^\s*\d+\| ?", re.M)


def norm_text(t):
    return (t or "").replace("\r\n", "\n").replace("\r", "\n")


def clean_quote(q):
    return _PREFIX.sub("", norm_text(q)).strip()


def quote_in_file(quote, text):
    q = clean_quote(quote)
    return len(re.sub(r"\s", "", q)) >= MIN_QUOTE and q in norm_text(text)


def quote_on_line(quote, text, line, slack=2):
    """Diagnostic only (not a filter): the quote's first line appears within ``slack`` lines of the cited line."""
    q = clean_quote(quote).split("\n")[0].strip()
    lines = norm_text(text).split("\n")
    if not q or not isinstance(line, int):
        return False
    lo, hi = max(0, line - 1 - slack), min(len(lines), line + slack)
    return any(q in lines[i] for i in range(lo, hi))


def norm_path(p):
    p = (p or "").strip()
    return p[2:] if p.startswith("./") else p


def lookup(files, path):
    p = norm_path(path)
    if p in files:
        return files[p]
    return None


def is_runtime_fail(f):
    return f.get("stage") == "runtime" and f.get("level", "fail") == "fail"


def checker_verdict(findings):
    """The System verdict in release 1: ``changes_requested`` iff the Checker scripts report a fail-level finding."""
    return "changes_requested" if any(f.get("level", "fail") == "fail" for f in findings or []) else "approve"


def apply(out, files, findings):
    """``out``: schema-valid answer. Returns ``(filtered, stats)``; ``out`` is not modified."""
    by_key = {(f["rule"], norm_path(f.get("file")), int(f.get("line") or 0)): f for f in findings}
    tri, add = [], []
    stats = dict(dismissals_dropped=0, runtime_dismissal_blocked=0, dismissals_kept=0, confirms_ungrounded=0,
                 added_in=len(out["added_findings"]), added_dropped_quote=0, added_dropped_file=0, added_dropped_duplicate=0, added_kept=0,
                 lines_ok=0)
    for t in out["scripts_triage"]:
        t2 = dict(t)
        f = by_key.get((t["rule"], norm_path(t["file"]), int(t["line"] or 0)), {})
        text = lookup(files, t["file"])
        grounded = text is not None and quote_in_file(t["quote"], text)
        if t["decision"] == "dismiss":
            if is_runtime_fail(f):
                t2["decision"] = "confirm"
                t2["postfilter"] = "runtime-fail-not-dismissable"
                stats["runtime_dismissal_blocked"] += 1
            elif not grounded:
                t2["decision"] = "confirm"
                t2["postfilter"] = "dismissal-quote-not-in-file"
                stats["dismissals_dropped"] += 1
            else:
                stats["dismissals_kept"] += 1
        elif not grounded:
            stats["confirms_ungrounded"] += 1
        tri.append(t2)
    seen = set()
    checker_pos = {(k[1], k[2]) for k in by_key}
    for a in out["added_findings"]:
        text = lookup(files, a["file"])
        if text is None:
            stats["added_dropped_file"] += 1
            continue
        if not quote_in_file(a["quote"], text):
            stats["added_dropped_quote"] += 1
            continue
        k = (a["category"], norm_path(a["file"]), a["line"])
        if k in seen or (norm_path(a["file"]), a["line"]) in checker_pos:
            stats["added_dropped_duplicate"] += 1
            continue
        seen.add(k)
        stats["lines_ok"] += quote_on_line(a["quote"], text, a["line"])
        add.append(a)
    stats["added_kept"] = len(add)
    flt = dict(scripts_triage=tri, added_findings=add, verdict=checker_verdict(findings), model_verdict=out["verdict"])
    return flt, stats
