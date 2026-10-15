"""Audit G contract test: the pinned usuba-checker package (sibling repo) exposes the surface this repo relies on.

Needs the sibling checkout (../usuba-checker-scripts or ../scripts, or $SCRIPTS_REPO); skipped when it is absent (CI has no token for the private
sibling yet, see docs/PACKAGING.md). With it present the test is strict: wrong or missing pin, missing API, or an unversioned report all fail.
"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = [os.environ.get("SCRIPTS_REPO"), os.path.join(ROOT, "..", "usuba-checker-scripts"), os.path.join(ROOT, "..", "scripts")]
SIB = next((os.path.abspath(p) for p in CANDIDATES if p and os.path.isfile(os.path.join(p, "usuba_checker", "__init__.py"))), None)


def pinned_sha():
    txt = open(os.path.join(ROOT, "requirements-checker.txt")).read()
    m = re.search(r"usuba-checker-scripts@([0-9a-f]{40})\s*$", txt, re.M)
    assert m, "requirements-checker.txt must pin usuba-checker by a full 40-hex commit SHA"
    return m.group(1)


def test_pin_is_a_full_sha():
    assert len(pinned_sha()) == 40


@pytest.mark.skipif(SIB is None, reason="sibling usuba-checker-scripts checkout not found")
def test_sibling_is_at_or_after_the_pin():
    r = subprocess.run(["git", "-C", SIB, "merge-base", "--is-ancestor", pinned_sha(), "HEAD"], capture_output=True, text=True, check=False)
    assert r.returncode == 0, f"{SIB} is not at or after the pinned commit {pinned_sha()[:8]}: {r.stderr.strip()}"


@pytest.mark.skipif(SIB is None, reason="sibling usuba-checker-scripts checkout not found")
def test_public_surface_and_versioned_report():
    env = dict(os.environ, PYTHONPATH=SIB + os.pathsep + os.environ.get("PYTHONPATH", ""), PYTHONDONTWRITEBYTECODE="1")
    env.setdefault("FT_OMARCHY", os.path.join(SIB, "dell-ref", "omarchy-4.0.4"))
    code = ("import json, sys\n"
            "sys.path.insert(0, %r)\n"
            "import usuba_checker as uc\n"
            "r = uc.check_files({'manifest.json': '{\"id\": \"a.b\"}', 'W.qml': 'import QtQuick\\nItem {}'})\n"
            "m = r['meta']\n"
            "assert m['schema_version'] == 1 and len(m['rules_hash']) == 64 and m['reference_tree']['sha256'], m\n"
            "assert 'policies' in m and len(uc.holdout_ids()) >= 300 and 'SCORED' in dir(uc.scoring)\n"
            "print('ok')\n") % SIB
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, check=False, cwd=ROOT)
    assert r.returncode == 0 and "ok" in r.stdout, r.stderr[-600:]
