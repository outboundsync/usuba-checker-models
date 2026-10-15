#!/usr/bin/env python3
"""New-Checker report for HANCORE rows computed on the FULL plugin source tree (as the original build did: report on all files, then shown over the possibly truncated/omitted prompt files).
usage: dump_reports_full.py ROWS.jsonl.gz OUT.json"""
import sys, os, json, gzip
H = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(H); ROOT = os.path.dirname(T)
sys.path[:0] = [T, os.path.join(ROOT, "functest"), os.path.join(ROOT, "hancore"), H]
import functest, checker_report as CR
from build_reviewer_scrub import scrub
import build_v3_data as BV
from multiprocessing import Pool
def job(r):
    key = (r["id"].split(":", 1)[1].rsplit(":", 1)[0] + "@" + r["provenance"]["commit"]).lower().replace("/", "__", 1) if False else None
    repo = r["id"].split(":", 1)[1].rsplit(":", 1)[0]
    d = BV.SRC.get((repo.replace("/", "__") + "@" + r["provenance"]["commit"]).lower())
    if not d: return r["id"], None
    files = {p: c for p, c in functest.read_dir(d).items() if p not in CR.HARNESS_FILES}
    rep = CR.report(files)
    return r["id"], (None if rep is None else [scrub(x) for x in rep])
if __name__ == "__main__":
    rows = [r for r in (json.loads(l) for l in gzip.open(sys.argv[1], "rt")) if r["source"] == "hancore_concrete"]
    with Pool(8) as p: res = dict(p.map(job, rows, chunksize=4))
    json.dump(res, open(sys.argv[2], "w")); print("hancore rows", len(res), "no_src_or_unavailable", sum(v is None for v in res.values()))
