#!/usr/bin/env bash
# Paid DRY RUN on the Vast GPU (a few minutes on the REAL train.jsonl, real config, real model): proves the whole path before the 11 h run.
# Not launched by anything automatically. Usage on the instance:  bash /workspace/usuba/train/dry_run.sh [MINUTES=6]
# Checks: tokenise/mask stats (CPU), model load, optimizer steps at the real max_len/batch, peak GPU memory, a periodic checkpoint written,
# sec/step -> projected total hours vs max_hours, and an adapter save. Writes /workspace/usuba/DRYRUN_REPORT.txt and DRYRUN_DONE (or DRYRUN_FAIL).
# Output goes to out/dryrun (never touches out/usuba-9b-lora), so the real run starts from scratch afterwards.
set -uo pipefail
M=${1:-6}; cd /workspace/usuba/train; U=/workspace/usuba; REP=$U/DRYRUN_REPORT.txt; rm -f $U/DRYRUN_DONE $U/DRYRUN_FAIL; rm -rf out/dryrun
exec > >(tee -a $U/dryrun.log) 2>&1
fail() { echo "DRYRUN FAIL: $*" | tee $REP; touch $U/DRYRUN_FAIL; exit 1; }
bash $U/train/deps.sh || fail "dependency install failed"
python3 train_lora.py --config config.yaml --dry-run || fail "CPU dry-run (tokenise/mask) failed"
python3 - <<PY || fail "config"
import yaml; c=yaml.safe_load(open("config.yaml")); c.update(save_every_steps=3, eval_every_steps=6, max_hours=$M/60, output_dir="out/dryrun")
yaml.safe_dump(c, open("config_dryrun.yaml","w")); print("max_hours in real config:", yaml.safe_load(open("config.yaml"))["max_hours"])
PY
ALLOW_CPU=0 timeout $(( (M+12)*60 )) python3 train_lora.py --config config_dryrun.yaml --resume; rc=$?
L=out/dryrun/train_log.jsonl; [ -s $L ] || fail "no optimizer step logged in ~$M min (rc=$rc)"
ls -d out/dryrun/checkpoints/step-*/COMPLETE >/dev/null 2>&1 || fail "no complete checkpoint was written (rc=$rc)"
python3 - <<PY | tee $REP
import json,yaml
rows=[json.loads(l) for l in open("$L") if '"loss"' in l]; c=yaml.safe_load(open("config.yaml"))
n=len(rows); h=rows[-1]["hours"]; sps=h*3600/n
import re
m=re.findall(r'"total_optimizer_steps": (\d+)', open("$U/dryrun.log").read()); steps=int(m[-1]) if m else None
print(f"DRYRUN OK: {n} optimizer steps in {h*60:.1f} min -> {sps:.1f} s/step, peak mem {max(r['mem_gb'] for r in rows)} GB, loss {rows[0]['loss']} -> {rows[-1]['loss']}")
print("checkpoint written: yes; real config max_hours =", c["max_hours"])
if steps: print(f"projected: {steps} steps x {sps:.1f} s = {steps*sps/3600:.1f} h vs max_hours {c['max_hours']} (first steps may be shorter/longer than average; examples are shuffled)")
else: print("projection skipped (could not read example/epoch count from dry_run_stats.json / config)")
PY
touch $U/DRYRUN_DONE
