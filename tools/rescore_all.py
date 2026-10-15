#!/usr/bin/env python3
"""Re-score every committed result JSON that has a raw generations file, with the CURRENT shared scorer (three-way verdict, n_invalid, bootstrap CIs).
No API calls. Raw files are private and not committed; pass the directories that hold them.

    python3 tools/rescore_all.py --scripts ../usuba-checker-scripts --raw /workspace/usuba-runs/56016890/exam/results [--raw DIR ...]

Writes eval/hancore_holdout/results/NAME.rescored.json next to the original (the original is never changed). Results without a raw file are listed."""
import argparse
import glob
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), "eval", "hancore_holdout", "results")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scripts", required=True)
    ap.add_argument("--raw", action="append", required=True)
    a = ap.parse_args()
    eh = os.path.join(a.scripts, "eval", "hancore_holdout")
    sys.path.insert(0, eh)
    spec = importlib.util.spec_from_file_location("hh_rescore", os.path.join(eh, "rescore.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    done, missing = [], []
    for p in sorted(glob.glob(os.path.join(RES, "*.json"))):
        name = os.path.basename(p)[:-5]
        if name.endswith(".rescored"):
            continue
        raws = [f for d in a.raw for f in glob.glob(os.path.join(d, "**", name + ".raw.jsonl"), recursive=True)]
        if not raws:
            missing.append(name)
            continue
        with tempfile.TemporaryDirectory() as t:
            shutil.copy(raws[0], os.path.join(t, name + ".raw.jsonl"))
            shutil.copy(p, os.path.join(t, name + ".json"))
            try:
                res, out = m.rescore(name, results_dir=t)
            except ValueError as e:
                missing.append(name + " (" + str(e) + ")")
                continue
            shutil.copy(out, os.path.join(RES, name + ".rescored.json"))
            done.append((name, res["n_invalid"], res["verdict_accuracy"]))
    for d in done:
        print("rescored %s n_invalid=%s acc=%s" % d)
    print("no raw file / mismatch (not re-scoreable here):", missing)


if __name__ == "__main__":
    main()
