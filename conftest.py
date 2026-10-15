"""Collection guard: test modules that import the private sibling checker (usuba-checker-scripts) cannot even be collected without it.
CI has no token for that private repo (docs/PACKAGING.md), so those modules are ignored there, with a visible notice in the pytest header.
With a checkout (USUBA_CHECKER_ROOT or ../usuba-checker-scripts) nothing is ignored and the tests run strictly."""
import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_NEEDS_CHECKER = [
    "tests/test_code_blob_parity.py",
    "train/tests/test_checker_timeout.py",
    "train/tests/test_code_blob.py",
    "train/tests/test_holdout_guard_content.py",
]


def _checker_available():
    spec = importlib.util.spec_from_file_location("_usuba_paths", os.path.join(_HERE, "train", "paths.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        mod.checker_root()
        return True
    except FileNotFoundError:
        return importlib.util.find_spec("usuba_checker") is not None


_AVAILABLE = _checker_available()
collect_ignore = [] if _AVAILABLE else _NEEDS_CHECKER


def pytest_report_header(config):
    if not _AVAILABLE:
        return "usuba-checker sibling NOT found: not collecting " + ", ".join(_NEEDS_CHECKER)
