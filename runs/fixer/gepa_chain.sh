#!/bin/bash
# GEPA (base-prompt seed, 4 iters, 24 train) -> best prompt + fixer loop on 49 holdout -> gepa_result.json. Hand-check still required afterwards.
cd "$(dirname "$0")"
python3 gepa.py 4 24 > gepa.log 2>&1
python3 loop.py gepa sys_gepa.txt 3 > gepa_holdout.log 2>&1
python3 - <<'PY'
import json
R=[json.loads(l) for l in open('gepa/rows.jsonl')]
L=[json.loads(l) for l in open('gepa/log.jsonl')]
out={"train_iters":[{k:x.get(k) for k in ("it","score","partial","accepted")} for x in L],
 "holdout_pass_by_round":[sum(r['first_pass_round'] is not None and r['first_pass_round']<=k for r in R) for k in range(4)],
 "holdout_cost":sum(r['cost'] for r in R),"passes":[[r['i'],r['task'],r['first_pass_round']] for r in R if r['first_pass_round'] is not None],
 "hand_check":"PENDING"}
json.dump(out,open('gepa_result.json','w'),indent=1)
open('STATUS.txt','a').write("gepa holdout done: "+json.dumps(out['holdout_pass_by_round'])+" (grader; hand-check pending)\n")
PY
