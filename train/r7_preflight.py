#!/usr/bin/env python3
"""r7 launch preflight: HARD checks on the final dataset before any paid step. CPU only (tokenizer download only), no GPU, no spend.
  python3 train/r7_preflight.py [DATA_DIR=/workspace/usuba-runs/v3-data-r7/final_merged] [--write-config] [--sec-per-step 70]
Exit 0 = every hard check passed; non-zero = BLOCKED (prints each failure). --write-config fills config.yaml expected_rows (only after all checks pass).
Checks: SHA256SUMS; row counts; 3-message rows; meta.prompt_sha256 == scope.prompt_scope.PROMPT_SHA256; meta.code_blob_policy == the code_blob POLICY_ID of the
checker package AND is code_blob/v2 (windows); target passes scope.schema.structure_errors; holdout/Dell guard; repo-disjoint train/val;
over-length/empty drop rate <= max_drop_rate; schedule (evals every 14 steps, >= 1 eval); projected hours/cost vs max_hours and the credit."""
import argparse, collections, json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT]
import yaml, paths, train_utils as TU
ap = argparse.ArgumentParser(); ap.add_argument("data_dir", nargs="?", default="/workspace/usuba-runs/v3-data-r7/final_merged")
ap.add_argument("--write-config", action="store_true"); ap.add_argument("--sec-per-step", type=float, default=70.0, help="measured 68.8-70 s/step on H100 NVL, v2 run (12k-token rows)")
ap.add_argument("--dph", type=float, default=2.35); ap.add_argument("--eval-secs", type=float, default=240.0); ap.add_argument("--overhead-h", type=float, default=1.2, help="setup + model load + export + parity")
a = ap.parse_args()
C = yaml.safe_load(open(os.path.join(HERE, "config.yaml"))); fails, notes = [], []
def bad(m): fails.append(m); print("FAIL:", m)
def ok(m): print("ok:  ", m)
D = a.data_dir; tr_f, va_f, sums = (os.path.join(D, n) for n in ("train.jsonl.gz", "val.jsonl.gz", "SHA256SUMS"))
if not all(os.path.exists(f) for f in (tr_f, va_f, sums)): print(f"BLOCKED: dataset not final yet ({D} lacks train.jsonl.gz/val.jsonl.gz/SHA256SUMS)"); sys.exit(2)
try: TU.verify_sums(sums, [tr_f, va_f]); ok("SHA256SUMS verified")
except SystemExit as e: bad(str(e))
tr, va = TU.read_rows(tr_f), TU.read_rows(va_f); ok(f"rows: train {len(tr)}, val {len(va)}")
from scope import prompt_scope, schema
sys.path.insert(0, os.path.join(paths.checker_root())); 
try:
    from usuba_checker import code_blob as CB; cur = getattr(CB, "POLICY_ID_V2", None)   # v2 id is additive; POLICY_ID stays v1 (render() unchanged, golden hash)
    if cur is None: bad("installed usuba_checker.code_blob has no POLICY_ID_V2 (pin scripts at >= ffc910e)")
except Exception as e: cur = None; bad(f"cannot import usuba_checker.code_blob: {e}")
pol = collections.Counter(r["meta"].get("code_blob_policy") for r in tr + va); pr = collections.Counter(r["meta"].get("prompt_sha256") for r in tr + va)
if set(pr) != {prompt_scope.PROMPT_SHA256}: bad(f"prompt_sha256 in rows {dict(pr)} != scope.prompt_scope.PROMPT_SHA256 {prompt_scope.PROMPT_SHA256[:12]}")
else: ok("all rows carry the current scope-v4 prompt sha")
if len(pol) != 1 or not next(iter(pol)).startswith("code_blob/v2"): bad(f"rows' code_blob_policy {dict(pol)}: expected exactly one code_blob/v2 policy (windows)")
elif cur != next(iter(pol)): bad(f"rows' code_blob_policy {next(iter(pol))!r} != installed usuba_checker.code_blob.POLICY_ID_V2 {cur!r}: eval/train parity would break (commit the v2 renderer + golden hash first)")
else: ok(f"code_blob policy {cur}")
n_bad = 0
for r in tr + va:
    m = r.get("messages") or []
    if len(m) != 3 or [x["role"] for x in m] != ["system", "user", "assistant"]: n_bad += 1; continue
    o = schema.extract_json(m[-1]["content"]); 
    if not o or schema.structure_errors(o): n_bad += 1
(bad if n_bad else ok)(f"{n_bad} rows with bad message shape or target schema" if n_bad else "all targets pass scope.schema.structure_errors")
rp = lambda rows: {r["meta"].get("repo") for r in rows}
(bad if rp(tr) & rp(va) else ok)(f"train/val repo overlap: {sorted(rp(tr) & rp(va))[:5]}" if rp(tr) & rp(va) else "train/val repo-disjoint")
import holdout_guard; g = holdout_guard.Guard().check(tr + va)
(bad if g else ok)(f"holdout/Dell guard rejected {len(g)} rows" if g else "holdout/Dell guard clean")
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained(C["base_model"], revision=paths.BASE_REVISION)
def ntok(r):
    ids = tok.apply_chat_template(r["messages"], tokenize=True, add_generation_prompt=False, enable_thinking=False)
    return len(ids["input_ids"] if hasattr(ids, "input_ids") else ids)
L = {k: [ntok(r) for r in rows] for k, rows in (("train", tr), ("val", va))}
for k in L:
    over = sum(x > C["max_len"] for x in L[k]); rate = over / max(1, len(L[k])); s = sorted(L[k])
    (bad if rate > C.get("max_drop_rate", 0.02) else ok)(f"{k}: tokens median {s[len(s)//2]}, max {s[-1]}, over max_len {C['max_len']}: {over} ({rate:.1%})")
try: S = TU.schedule(len(tr), C["per_device_batch"], C["grad_accum"], C["epochs"], C["warmup_ratio"], C.get("eval_every_steps"), C.get("eval_every_epochs"))
except SystemExit as e: print(f"FAIL: {e}"); print("BLOCKED: schedule"); sys.exit(1)
nev = len(S["eval_steps"]) + 1; hrs = S["total_steps"] * a.sec_per_step / 3600 + nev * a.eval_secs / 3600 + a.overhead_h
ok(f"schedule: {S['total_steps']} steps ({S['steps_per_epoch']}/epoch), eval every {S['eval_every_steps']} -> {nev} evals, warmup {S['warmup_steps']}")
tok_scale = (sum(L["train"]) / len(L["train"])) / 12000   # the 70 s/step baseline was measured at ~12k-token rows
est = S["total_steps"] * a.sec_per_step * max(1.0, tok_scale) / 3600 + nev * a.eval_secs / 3600 + a.overhead_h
print(f"ESTIMATE: {est:.1f} h (mean train row {sum(L['train'])//len(L['train'])} tokens; scale {tok_scale:.2f}) x ${a.dph}/h = ${est * a.dph:.0f}; cap: max_hours {C['max_hours']} training + 2 h = {C['max_hours']+2} h instance => worst case ${(C['max_hours']+2) * 3.6:.0f} at the $3.6/h offer ceiling")
if est > C["max_hours"]: bad(f"estimated {est:.1f} h exceeds max_hours {C['max_hours']}")
try:
    cr = json.loads(subprocess.run(["vastai", "show", "user", "--raw"], capture_output=True, text=True, timeout=60).stdout)["credit"]; print(f"vast credit ${cr:.2f}")
    if cr < (C["max_hours"] + 2) * 3.6 * 0.5: notes.append(f"credit ${cr:.2f} below half the worst case")
except Exception: notes.append("could not read vast credit")
print("NOTES:", notes or "none")
if fails: print(f"BLOCKED: {len(fails)} hard check(s) failed"); sys.exit(1)
if a.write_config:
    p = os.path.join(HERE, "config.yaml"); t = open(p).read(); t2 = re.sub(r"^expected_rows:.*$", f"expected_rows: {{train: {len(tr)}, val: {len(va)}}}   # set by r7_preflight.py", t, flags=re.M); open(p, "w").write(t2); print("config.yaml expected_rows written")
print("PREFLIGHT PASS")
