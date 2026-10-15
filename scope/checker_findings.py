"""Structured Checker scripts report for a plugin: list of dicts {rule, file, line, message, stage, level}.

Same findings as ``train/checker_report.py`` (so the model sees what the System reports), but structured instead of formatted strings:
  level  fail = blocking static finding (checks.blocking); warn = everything else (heuristics, HANCORE warn rules, lifecycle, USB-HC)
  stage  static for everything produced here. Runtime-stage findings (USB-R*) need bwrap + Quickshell and are only present when the caller passes them in.
Needs a usuba-checker-scripts checkout (USUBA_CHECKER_ROOT) and its reference tree (FT_OMARCHY), exactly like the rest of this repo.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TRAIN = os.path.join(os.path.dirname(HERE), "train")
if TRAIN not in sys.path:
    sys.path.insert(0, TRAIN)
import checker_report as C  # noqa: E402  (needs TRAIN on sys.path; sets FT_OMARCHY and the functest path)
from usuba import checks  # noqa: E402
from usuba import hancore_rules as HR  # noqa: E402
from usuba import hancore_rules_v2 as HV2  # noqa: E402
from usuba import lifecycle_rules as LR  # noqa: E402

RUNTIME_PREFIX = "USB-R"
_LINE = re.compile(r"\bline (\d+)\b")


def _line(f, msg):
    """the rule's own line, else the first 'line N' the message names (static rules often report it only in prose), else 0"""
    ln = int(f.get("line") or 0)
    if ln:
        return ln
    m = _LINE.search(msg)
    return int(m.group(1)) if m else 0


def _collect(files):
    out = []
    for f in checks.check(files):
        out.append(dict(rule=f["rule"], file=f["file"], line=_line(f, f["reason"]), message="%s. Fix: %s" % (f["reason"], f["hint"]), stage="static",
                        level="fail" if checks.blocking(f) else "warn"))
    for f in HR.check(files, experimental=True):
        if f["rule"] in HR.EXPERIMENTAL:
            out.append(dict(rule=f["rule"], file=f["file"], line=_line(f, f["reason"]), message=f["reason"], stage="static", level="warn"))
    for f in LR.check(files, enabled={"USB-N01", "USB-N02", "USB-L01", "USB-L02", "USB-L03"}):
        if f["rule"] == "USB-L01" or f["rule"] in LR.ENABLED:
            out.append(dict(rule=f["rule"], file=f["file"], line=_line(f, f["reason"]), message="%s. Fix: %s" % (f["reason"], f.get("hint", "")),
                            stage="static", level="warn"))
    for f in HV2.check(files):
        out.append(dict(rule=f["rule"], file=f["file"], line=_line(f, f["reason"]), message=f["reason"], stage="static", level="warn"))
    return out


def findings_for(files, timeout=60):
    """-> list of findings, or None when the Checker scripts crashed or timed out (the prompt then says the report is unavailable)."""
    ok, val = C.run_with_timeout(_collect, (files,), timeout)
    return val if ok else None


def is_runtime(rule):
    return rule.startswith(RUNTIME_PREFIX)
