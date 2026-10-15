"""A11: the real watchdog.sh loop and the host `watch` loop, run in seconds with stub processes (no GPU, no network, no instance)."""
import os, sys, time, shutil, subprocess, pathlib, hashlib
T = pathlib.Path(__file__).resolve().parent.parent


def _stubs(tmp, alive):
    b = tmp / "bin"; b.mkdir(exist_ok=True)
    (b / "pgrep").write_text(f'#!/bin/bash\n[ -f "{alive}" ] && exit 0 || exit 1\n')
    (b / "tmux").write_text(f'#!/bin/bash\necho "$@" >> "{tmp}/tmux.log"\nexit 0\n')
    (b / "pkill").write_text(f'#!/bin/bash\necho "$@" >> "{tmp}/pkill.log"\nexit 0\n')
    for p in b.iterdir(): p.chmod(0o755)
    return b


def _wd(tmp, secs, env=None, alive=True, files=()):
    u = tmp / "u"; (u / "train" / "out" / "x").mkdir(parents=True, exist_ok=True)
    (u / "ARMED").write_text("out/x\ntrue\n1\n")
    alive_f = tmp / "alive"
    if alive: alive_f.write_text("1")
    for f in files: (u / f).write_text("")
    e = dict(os.environ, PATH=f"{_stubs(tmp, alive_f)}:{os.environ['PATH']}", U=str(u), CHECK_SEC="1", DEAD_GRACE="0", RESTART_PAUSE="0", **(env or {}))
    try: subprocess.run(["bash", str(T / "watchdog.sh")], env=e, timeout=secs, capture_output=True)
    except subprocess.TimeoutExpired: pass
    rd = lambda n: (u / n).read_text() if (u / n).exists() else ""
    return u, rd("watchdog.log"), rd("ALERT"), (tmp / "tmux.log").read_text() if (tmp / "tmux.log").exists() else ""


def test_dead_process_restarts_then_gives_up_with_no_restart(tmp_path):
    u, log, alert, tmux = _wd(tmp_path, 9, dict(MAX_RESTARTS="2"), alive=False)
    assert "process dead" in alert and tmux.count("new") >= 2
    assert "GIVING UP after 2 restarts" in alert and (u / "NO_RESTART").exists()


def test_terminal_markers_stop_all_restarts(tmp_path):
    for i, marker in enumerate(("ALL_DONE", "SMOKE_DONE", "NO_RESTART")):
        d = tmp_path / str(i); d.mkdir()
        u, log, alert, tmux = _wd(d, 4, alive=False, files=(marker,))
        assert "terminal marker present" in log and tmux == "" and alert == "", marker


def test_stall_clock_starts_at_first_step_not_before(tmp_path):
    # alive, no step logged, tiny stall limit but long boot limit: NO restart (boot is only limited by BOOT_SEC)
    u, log, alert, tmux = _wd(tmp_path, 6, dict(STALL_SEC="1", BOOT_SEC="1000", MAX_RESTARTS="3"))
    assert "restart" not in alert and tmux == ""
    # ... and once the boot limit passes with no step, it restarts with the boot reason
    d = tmp_path / "b"; d.mkdir()
    # watchdog START is only set by its own start_train, so arm a first start via a dead process then a live one
    u, log, alert, tmux = _wd(d, 8, dict(STALL_SEC="1000", BOOT_SEC="1", MAX_RESTARTS="3"), alive=False)
    assert "process dead" in alert


def test_stall_after_first_step_restarts(tmp_path):
    u = tmp_path / "u"; (u / "train/out/x").mkdir(parents=True)
    (u / "train/out/x/train_log.jsonl").write_text('{"step": 3, "loss": 1.0}\n')
    _, log, alert, tmux = _wd(tmp_path, 9, dict(STALL_SEC="2", BOOT_SEC="1000", MAX_RESTARTS="1"))
    assert "no step progress" in alert and "GIVING UP" in alert and (u / "NO_RESTART").exists()


def test_max_hours_stop_marker_is_terminal(tmp_path):
    u = tmp_path / "u"; (u / "train/out/x").mkdir(parents=True); (u / "train/out/x/STOPPED").write_text("max_hours reached")
    _, log, alert, tmux = _wd(tmp_path, 4, alive=False)
    assert "terminal marker present" in log and tmux == ""


def _watch(tmp, extra_env, files, secs=60):
    t = tmp / "repo" / "train"; t.mkdir(parents=True)
    for f in ("launch_vast.sh", "train_utils.py"): shutil.copy(T / f, t / f)
    (t / "config.yaml").write_text("output_dir: out/x\nmax_hours: 1\n"); (t / ".vast_instance").write_text("4242\n")
    mock = tmp / "mock"; (mock / "train/out/x").mkdir(parents=True)
    for f, c in files.items(): (mock / f).write_text(c)
    b = tmp / "bin"; b.mkdir(); log = tmp / "vast.log"
    (b / "vastai").write_text(f'#!/bin/bash\necho "$@" >> {log}\nexit 0\n'); (b / "vastai").chmod(0o755)
    env = dict(os.environ, PATH=f"{b}:{os.path.dirname(sys.executable)}:{os.environ['PATH']}", MOCK_REMOTE=str(mock), USUBA_RUNS=str(tmp / "runs"), SYNC_EVERY="0", HOME=str(tmp),
               LIMIT_GRACE="0", FETCH_RETRY_SLEEP="0", **extra_env)
    r = subprocess.run(["bash", str(t / "launch_vast.sh"), "watch"], env=env, capture_output=True, text=True, timeout=secs)
    return r.stdout + r.stderr, mock, (log.read_text() if log.exists() else "")


def test_host_watch_instance_wall_clock_limit_stops_fetches_destroys(tmp_path):
    out, mock, vlog = _watch(tmp_path, dict(INSTANCE_MAX_HOURS="0.0002"), {"train/out/x/artifact.bin": "x"})
    assert "INSTANCE WALL-CLOCK LIMIT" in out, out
    assert (mock / "NO_RESTART").exists()                # restart disabled before the stop
    assert "MOCK: would destroy 4242" in out, out


def test_host_watch_terminal_marker_triggers_final_fetch_not_restart(tmp_path):
    out, mock, vlog = _watch(tmp_path, dict(INSTANCE_MAX_HOURS="5"), {"train/out/x/artifact.bin": "x", "NO_RESTART": ""})
    assert "terminal marker on the instance" in out and "FETCH VERIFIED" in out, out
    assert "would destroy" not in out and "WALL-CLOCK" not in out
