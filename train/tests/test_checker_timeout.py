"""A7: the Checker timeout works inside a ThreadPoolExecutor and inside daemonic multiprocessing workers (signal.alarm did not)."""
import os, sys, time, multiprocessing
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
cr = pytest.importorskip("checker_report")


def _sleepy(x): time.sleep(x); return x
def _boom(x): raise RuntimeError("no")


def test_timeout_kills_runaway_in_thread_pool():
    def job(secs): t = time.time(); r = cr.run_with_timeout(_sleepy, (secs,), 2); return r, time.time() - t
    with ThreadPoolExecutor(4) as ex: res = list(ex.map(job, [30, 30, 0, 0]))
    assert all(r == (False, None) and dt < 25 for r, dt in res[:2]), res
    assert all(r == (True, 0) for r, dt in res[2:]), res


def test_crash_and_value_roundtrip():
    assert cr.run_with_timeout(_boom, (1,), 5) == (False, None)
    assert cr.run_with_timeout(_sleepy, (0,), 5) == (True, 0)
    assert cr.run_with_timeout(_sleepy, (0,), 0) == (True, 0)


def _in_daemon(q): q.put(cr.run_with_timeout(_sleepy, (60,), 3))
def test_works_inside_daemonic_pool_worker():
    q = multiprocessing.get_context("fork").Queue(); p = multiprocessing.get_context("fork").Process(target=_in_daemon, args=(q,), daemon=True); p.start(); p.join(50)
    assert q.get(timeout=20) == (False, None)


def test_report_still_produced_and_none_on_timeout(monkeypatch):
    files = {"manifest.json": '{"id":"example.x","schemaVersion":1}', "A.qml": "import QtQuick\nItem {}\n"}
    rep, w = cr.report_and_warn_rules(files, timeout=60); assert isinstance(rep, list)
    monkeypatch.setattr(cr, "_core", lambda f: time.sleep(60))
    t = time.time(); rep, w = cr.report_and_warn_rules(files, timeout=2); assert rep is None and time.time() - t < 40
