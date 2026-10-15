#!/usr/bin/env python3
"""Dump the Checker report lines a given source tree (train/checker_report.py + functest) produces for the VISIBLE files of every row in a pool.
usage: dump_reports.py TREE ROWS.jsonl.gz OUT.json   (run once with the r2 tree [git archive v3-data-r2] and once with the current repo)"""
import sys, os, json, gzip, importlib.util
TREE, ROWS, OUT = sys.argv[1:4]
H = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("exactline", os.path.join(H, "exactline.py")); X = importlib.util.module_from_spec(sp); sp.loader.exec_module(X)
sys.path[:0] = [os.path.join(TREE, "train"), os.path.join(TREE, "functest")]
import checker_report as CR
from build_reviewer_scrub import scrub
from multiprocessing import Pool
def job(r):
    u = r["messages"][-2]["content"]
    files = {p: c for p, c in X.parse_files(u).items() if p not in CR.HARNESS_FILES}
    rep = CR.report(files)
    return r["id"], (None if rep is None else [scrub(x) for x in rep])
if __name__ == "__main__":
    rows = [json.loads(l) for l in gzip.open(ROWS, "rt")]
    with Pool(8) as p: res = dict(p.map(job, rows, chunksize=8))
    json.dump(res, open(OUT, "w"))
    print("rows", len(res), "unavailable", sum(v is None for v in res.values()))
