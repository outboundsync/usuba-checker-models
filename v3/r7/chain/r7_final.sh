#!/bin/bash
# waits for mining to finish, then 40 hash-shards -> merge -> gate report. Fully resumable (each step skips finished output).
V=/workspace/usuba-runs/v3-data-r7; S=$V/STATUS.md
while ! grep -q "mine scale finished" $S; do sleep 120; done
N=40
for i in $(seq 0 $((N-1))); do [ -f $V/shards40/s$i/DONE ] && continue
  bash /workspace/r6/run_r7_units.sh $V/scale $i $N 2>&1 | tail -1
  # shard outputs live in shards/ (N=8 layout) -> redirect: use dedicated dir for N=40
done
cd /workspace/usuba-runs/audit-fixes-B/usuba-checker-models/train/v3data
export R6S_FLOOR=15 R6S_RELAX_TIES=2 USUBA_CHECKER_ROOT=/workspace/usuba-runs/audit-fixes-B/usuba-checker-scripts PYTHONPATH=/workspace/usuba-runs/audit-fixes-B/usuba-checker-scripts/functest:/workspace/usuba-runs/audit-fixes-B/usuba-checker-scripts/hancore:/workspace/usuba-runs/audit-fixes-B/usuba-checker-scripts
python3 r7_merge.py $V/final_merged $V/scope_r6 $V/security_w $V/shards40/s* > $V/final_merge.log 2>&1
cd ../..; python3 tools/scope_gate_report.py $V/final_merged > $V/final_merged/GATE_REPORT_R7.md 2>&1
python3 - <<'P' >> $V/final_merged/GATE_REPORT_R7.md
import json,gzip,collections
V="/workspace/usuba-runs/v3-data-r7/final_merged"; add=collections.defaultdict(lambda:[0,0,0]); tri=collections.defaultdict(lambda:[0,0]); n=collections.Counter()
for sp in ("train","val"):
    for l in gzip.open(f"{V}/{sp}.jsonl.gz","rt"):
        r=json.loads(l); t=json.loads(r["messages"][-1]["content"]); prov=r["meta"]["provisional"]
        for a in t["added_findings"]:
            c=add[a["category"]]; c[0]+=1; c[1]+= 1 if a["line"]>0 and a["file"] else 0; c[2]+=prov
        for x in t["scripts_triage"]:
            c=tri[x["rule"]]; c[0]+=1; c[1]+= 1 if x["line"]>0 else 0
        n[(r["row_type"],"prov" if prov else "ver")]+=1
print("\n## Per kind: file-and-line share (r7 addendum)\n\n| added-finding category | n | file+line | provisional rows |\n|---|---|---|---|")
for k,(a,b,p) in sorted(add.items()): print(f"| {k} | {a} | {b}/{a} ({100*b//max(1,a)}%) | {p} |")
print("\n| Checker rule (triage items) | n | with line | file-level |\n|---|---|---|---|")
for k,(a,b) in sorted(tri.items()): print(f"| {k} | {a} | {b} | {a-b} |")
print("\nrow_type x tier:",dict(n))
P
echo "- FINAL merge+report done $(date +%H:%M): $(tail -1 $V/final_merge.log|cut -c1-300)" >> $S
