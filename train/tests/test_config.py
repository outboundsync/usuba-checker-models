"""A8/A9: docs and pins derive from config.yaml"""
import os, sys, subprocess, yaml
T = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, T)
import paths


def test_config_pins_and_run_plan_fresh():
    C = yaml.safe_load(open(os.path.join(T, "config.yaml")))
    assert C["base_revision"] == paths.BASE_REVISION and len(paths.BASE_REVISION) == 40
    assert C["train_file"].endswith(".gz") and C["expected_rows"]["train"] > 0 and C["expected_rows"]["val"] > 0
    assert subprocess.run([sys.executable, os.path.join(T, "gen_train_docs.py"), "--check"]).returncode == 0, "RUN_PLAN.md is stale: python3 train/gen_train_docs.py"


def test_llama_cpp_and_work_dirs_are_env_driven(monkeypatch, tmp_path):
    import paths
    monkeypatch.setenv("USUBA_WORK", str(tmp_path))
    monkeypatch.delenv("USUBA_RUNS", raising=False)
    monkeypatch.delenv("USUBA_LLAMA_CPP", raising=False)
    assert paths.work_dir() == str(tmp_path)
    assert paths.runs_dir() == str(tmp_path / "usuba-runs")
    assert paths.llama_cpp_dir() == str(tmp_path / "llama.cpp")
    monkeypatch.setenv("USUBA_LLAMA_CPP", "/x/y")
    assert paths.llama_cpp_dir() == "/x/y"
