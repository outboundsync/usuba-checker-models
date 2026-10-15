"""One Checker report for training rows and every eval backend (train and eval must see the same text).
report(files) -> list[str] | None: Usuba Checker findings (checks.fmt) + HANCORE-rule `warn` / `warn experimental` lines.
None means the Checker crashed or timed out (prompt shows "(Checker report unavailable)").
Before 2026-10-14 the v1 Dell training rows used the sweep's static_fails + [runtime] lines instead, which omitted the warn lines
the eval prompt shows; that mismatch is what this module removes."""
import os, sys, signal
_F = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "functest")
if _F not in sys.path: sys.path.insert(0, _F)
from usuba import checks, hancore_rules as HR, lifecycle_rules as LR
# Test-harness notes that live next to some plugins (generator + functest verdict). Never part of a prompt, train or eval.
HARNESS_FILES = {"SOURCE.txt", "checklist.md"}
class _TO(Exception): pass
def _alarm(*a): raise _TO()
def report_and_warn_rules(files, timeout=20):
    use_alarm = timeout and hasattr(signal, "SIGALRM")
    try:
        if use_alarm:
            try: old = signal.signal(signal.SIGALRM, _alarm); signal.alarm(timeout)
            except ValueError: use_alarm = False   # not main thread
        rep = [checks.fmt(f) for f in checks.check(files)]
    except Exception: rep = None
    finally:
        if use_alarm: signal.alarm(0); signal.signal(signal.SIGALRM, old)
    w = HR.check(files, experimental=True)
    rep2 = [f"[{f['rule']} warn{' experimental' if f['rule'] in HR.EXPERIMENTAL else ''}] {f['file']}: {f['reason']}" for f in w if f["rule"] in HR.EXPERIMENTAL]
    # v3-fixes: manifest/lifecycle rules. Enabled high-severity ones read like load errors ("heuristic/high", usually real); L02 is a `warn`; L01 stays `warn experimental`.
    try: lc = LR.check(files, enabled={"USB-N01", "USB-N02", "USB-L01", "USB-L02", "USB-L03"})
    except Exception: lc = []
    rep3 = []
    for f in lc:
        if f["rule"] == "USB-L01": rep3.append(f"[USB-L01 warn experimental] {f['file']}: {f['reason']}")
        elif f["rule"] not in LR.ENABLED: continue
        elif f["severity"] == "high": rep3.append(f"[{f['rule']} heuristic/high] {f['file']}: {f['reason']}. Fix: {f['hint']}")
        else: rep3.append(f"[{f['rule']} warn] {f['file']}: {f['reason']}")
    return ((rep or []) + rep2 + rep3 if rep is not None else None), w + lc
def report(files, timeout=20): return report_and_warn_rules(files, timeout)[0]
