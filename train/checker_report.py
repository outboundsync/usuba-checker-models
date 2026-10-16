"""One Checker report for training rows and every eval backend (train and eval must see the same text).
report(files) -> list[str] | None: Usuba Checker findings (checks.fmt) + HANCORE-rule `warn` / `warn experimental` lines.
None means the Checker crashed or timed out (prompt shows "(Checker report unavailable)").
Before 2026-10-14 the v1 Dell training rows used the sweep's static_fails + [runtime] lines instead, which omitted the warn lines
the eval prompt shows; that mismatch is what this module removes."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
CHECKER_ROOT = paths.checker_root()
os.environ["FT_OMARCHY"] = os.environ.get("FT_OMARCHY") or paths.reference_tree()     # D2: the reference tree is part of the Checker; never run without it
_F = os.path.join(CHECKER_ROOT, "functest")
if _F not in sys.path: sys.path.insert(0, _F)
from usuba import checks, hancore_rules as HR, lifecycle_rules as LR, hancore_rules_v2 as HV2
import dell_checks as _DC
if not (_DC.API.get("Color") and _DC.API.get("bar")): raise RuntimeError(f"Checker reference tree gave an empty API table (FT_OMARCHY={os.environ['FT_OMARCHY']}): refusing to build reports")
CHECKER_TIMEOUT = 60   # one value for training rows and every eval backend (audit A7: train used 20 s, eval 0 s)
def checker_meta():
    """what produced a report: recorded in every row's meta and every result json"""
    gi = paths.git_info(CHECKER_ROOT)
    return dict(checker_git_sha=gi["sha"], checker_dirty=gi["dirty"], rules_hash=paths.rules_hash(CHECKER_ROOT), reference_tree=os.environ["FT_OMARCHY"],
                api_members={k: len(v) for k, v in _DC.API.items()}, timeout=CHECKER_TIMEOUT)
# Test-harness notes that live next to some plugins (generator + functest verdict). Never part of a prompt, train or eval.
HARNESS_FILES = {"SOURCE.txt", "checklist.md"}
import threading as _th
_FORK_LOCK = _th.Lock()


def run_with_timeout(fn, args, timeout):
    """fn(*args) with a hard wall-clock limit that works from ANY thread and inside daemonic pool workers (audit A7: signal.alarm only worked on the main
    thread, so the eval's thread pool had no timeout at all). POSIX: fork a child, result over a pipe, SIGKILL on timeout. Elsewhere: worker thread + join.
    Returns (ok, value). A crash, a timeout or an unpicklable result is (False, None) - never an exception."""
    if not timeout: 
        try: return True, fn(*args)
        except Exception as e:   # documented contract: a crashing fn is (False, None); say why instead of hiding it
            print(f"[checker_report] {getattr(fn, '__name__', fn)} crashed: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr); return False, None
    if hasattr(os, "fork"):
        import pickle, select, time
        with _FORK_LOCK:     # pipe+fork+close(w) atomically: otherwise a sibling's child inherits this write end and our read never sees EOF
            r, w = os.pipe(); pid = os.fork()
            if pid != 0: os.close(w)
        if pid == 0:    # child
            code = 1
            try:
                os.close(r); data = pickle.dumps(fn(*args)); 
                with os.fdopen(w, "wb") as f: f.write(data)
                code = 0
            except BaseException: pass
            finally: os._exit(code)
        chunks = []; end = time.time() + timeout; ok = False
        try:
            while True:
                left = end - time.time()
                if left <= 0: break
                if not select.select([r], [], [], left)[0]: break
                b = os.read(r, 1 << 20)
                if not b: ok = True; break
                chunks.append(b)
        finally:
            os.close(r)
            if not ok:
                try: os.kill(pid, 9)
                except OSError: pass
            _, status = os.waitpid(pid, 0)
        if ok and os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0 and chunks:
            try: return True, pickle.loads(b"".join(chunks))
            except (pickle.UnpicklingError, EOFError, AttributeError, ImportError, ValueError, IndexError): return False, None
        return False, None
    import threading; box = []
    t = threading.Thread(target=lambda: box.append(fn(*args)), daemon=True); t.start(); t.join(timeout)
    return (True, box[0]) if box else (False, None)


def _core(files): return [checks.fmt(f) for f in checks.check(files)]
def report_and_warn_rules(files, timeout=CHECKER_TIMEOUT):
    ok, rep = run_with_timeout(_core, (files,), timeout); rep = rep if ok else None
    w = HR.check(files, experimental=True)
    rep2 = [f"[{f['rule']} warn{' experimental' if f['rule'] in HR.EXPERIMENTAL else ''}] {f['file']}: {f['reason']}" for f in w if f["rule"] in HR.EXPERIMENTAL]
    # v3-fixes: manifest/lifecycle rules. Enabled high-severity ones read like load errors ("heuristic/high", usually real); L02 is a `warn`; L01 stays `warn experimental`.
    lc = LR.check(files, enabled={"USB-N01", "USB-N02", "USB-L01", "USB-L02", "USB-L03"})   # a crashing rule is an error, not an empty report
    rep3 = []
    for f in lc:
        if f["rule"] == "USB-L01": rep3.append(f"[USB-L01 warn experimental] {f['file']}: {f['reason']}")
        elif f["rule"] not in LR.ENABLED: continue
        elif f["severity"] == "high": rep3.append(f"[{f['rule']} heuristic/high] {f['file']}: {f['reason']}. Fix: {f['hint']}")
        else: rep3.append(f"[{f['rule']} warn] {f['file']}: {f['reason']}")
    # audit A7: the USB-HC rules (hancore_rules_v2, advisory) belong in the report too (TRAINING_PLAN planned them); formatted as warn leads with file:line
    hc = HV2.check(files)   # same: never fall back to an incomplete report
    rep4 = [f"[{f['rule']} warn] {f['file']}:{f['line']}: {f['reason']}" for f in hc]
    return ((rep or []) + rep2 + rep3 + rep4 if rep is not None else None), w + lc + hc
def report(files, timeout=CHECKER_TIMEOUT): return report_and_warn_rules(files, timeout)[0]
