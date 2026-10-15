"""Audit 8: train/code_blob.py is a shim over the pinned scripts package (no copy), and renders byte-identically to the scripts-side golden."""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "train"))
import code_blob  # noqa: E402

FILES = {"manifest.json": "{}", "A.qml": "\n".join(f"line {i}" for i in range(3000)), "R.md": "x"}
GOLDEN = "550fdf939cbc2de91376956c5feed36da9c51235e70af6b0ed829f08a4f868bd"   # same constant as usuba-checker-scripts tests/test_eval_train_parity.py


def test_shim_is_the_package_module():
    import usuba_checker.code_blob as real
    assert code_blob is real
    assert "usuba-checker-scripts" in real.__file__ or "site-packages" in real.__file__ or os.path.basename(os.path.dirname(real.__file__)) == "usuba_checker"


def test_no_second_implementation_in_models():
    src = open(os.path.join(ROOT, "train", "code_blob.py")).read()
    assert "def render" not in src and "FILE_CAP =" not in src


def test_golden_parity_with_scripts_repo():
    assert hashlib.sha256(code_blob.code_blob(FILES).encode()).hexdigest() == GOLDEN
