"""Shim, NOT a copy: the canonical renderer is usuba_checker.code_blob in usuba-checker-scripts (pinned in requirements-checker.txt).
`import code_blob` here returns that very module object, so train/eval/builders cannot drift (one-way dependency models -> scripts;
the scripts repo never imports this file). Parity: tests/test_code_blob_parity.py."""
import importlib
import os
import sys

try:
    _real = importlib.import_module("usuba_checker.code_blob")
except ImportError:   # not pip-installed: use the sibling checkout (same resolution as paths.checker_root())
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import paths
    _root = paths.checker_root()
    if _root not in sys.path:
        sys.path.insert(0, _root)
    _real = importlib.import_module("usuba_checker.code_blob")
sys.modules[__name__] = _real
