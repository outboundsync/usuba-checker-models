"""A11/A6: launcher behaviour with stub vastai/ssh (no network, no instance): a failed rent destroys the instance; an unverified dataset is never bundled."""
import os, sys, json, gzip, shutil, hashlib, subprocess, pathlib, site
import pytest
pytest.importorskip("yaml", reason="launch_vast.sh verifies the dataset with train_utils, which needs pyyaml")
T = pathlib.Path(__file__).resolve().parent.parent


def _setup(tmp, rows_cfg):
    t = tmp / "repo" / "train"; t.mkdir(parents=True)
    for f in ("launch_vast.sh", "train_utils.py"): shutil.copy(T / f, t / f)
    (tmp / "repo" / "eval" / "hancore_holdout").mkdir(parents=True); (tmp / "repo/eval/hancore_holdout/plugin_ids.txt").write_text("x\n")
    (tmp / "repo" / "scope").mkdir(); [(tmp / "repo/scope" / n).write_text("") for n in ("__init__.py", "schema.py")]
    d = tmp / "data"; d.mkdir()
    for n, k in (("train.jsonl.gz", 3), ("val.jsonl.gz", 2)):
        with gzip.open(d / n, "wt") as f:
            for i in range(k): f.write(json.dumps({"messages": []}) + "\n")
    (d / "SHA256SUMS").write_text("".join(f"{hashlib.sha256((d/n).read_bytes()).hexdigest()}  {n}\n" for n in ("train.jsonl.gz", "val.jsonl.gz")))
    (t / "config.yaml").write_text(f"train_file: data/r5/train.jsonl.gz\nval_file: data/r5/val.jsonl.gz\noutput_dir: out/x\nmax_hours: 1\nexpected_rows: {{train: {rows_cfg[0]}, val: {rows_cfg[1]}}}\n")
    b = tmp / "bin"; b.mkdir(); log = tmp / "vast.log"
    (b / "vastai").write_text(f'''#!/bin/bash
echo "$@" >> {log}
case "$1 $2" in
 "show ssh-keys") echo '[1]';; "search offers") echo '[{{"id":7,"dph_total":2.5,"gpu_name":"H100 SXM"}}]';;
 "create instance") echo '{{"new_contract": 4242}}';; "ssh-url "*|"ssh-url 4242") echo ssh://root@h:22;; esac
exit 0
''')
    (b / "ssh").write_text("#!/bin/bash\nexit 255\n"); (b / "scp").write_text("#!/bin/bash\nexit 255\n")
    for p in b.iterdir(): p.chmod(0o755)
    return t, d, b, log


def _run(t, d, b, tmp):
    env = dict(os.environ, PATH=f"{b}:{os.path.dirname(sys.executable)}:{os.environ['PATH']}", R5_DATA=str(d), USUBA_RUNS=str(tmp / "runs"), SSH_WAIT_TRIES="2", SSH_WAIT_SLEEP="0", BUNDLE=str(tmp / "b.tgz"), VAST_SSH_KEY=str(tmp / "k"), HOME=str(tmp), PYTHONUSERBASE=site.getuserbase())   # HOME is faked: keep the user site so the same pyyaml is importable
    (tmp / "k.pub").write_text("pub")
    return subprocess.run(["bash", str(t / "launch_vast.sh"), "up", "--yes"], env=env, capture_output=True, text=True, timeout=120)


def test_failed_rent_destroys_instance(tmp_path):
    t, d, b, log = _setup(tmp_path, (3, 2))
    r = _run(t, d, b, tmp_path)
    L = log.read_text()
    assert "create instance" in L and "destroy instance -y 4242" in L, (r.stdout, r.stderr, L)
    assert not (t / ".vast_instance").exists()


def test_unverified_dataset_is_never_bundled(tmp_path):
    t, d, b, log = _setup(tmp_path, (99, 2))      # wrong expected row count
    r = _run(t, d, b, tmp_path)
    assert r.returncode == 5 and "create instance" not in (log.read_text() if log.exists() else ""), (r.stdout, r.stderr)
    assert not (tmp_path / "b.tgz").exists()
