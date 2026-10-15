#!/usr/bin/env python3
"""Generate train/RUN_PLAN.md from config.yaml (audit A8): every number in the run plan comes from the config and the exact schedule, never typed by hand.
  python3 gen_train_docs.py          # rewrite RUN_PLAN.md
  python3 gen_train_docs.py --check  # exit 1 if RUN_PLAN.md is stale (tests/test_config.py runs this)"""
import os, sys, yaml
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import train_utils as TU

OUT = os.path.join(HERE, "RUN_PLAN.md")


def render(cfg_path=os.path.join(HERE, "config.yaml")):
    C = yaml.safe_load(open(cfg_path)); n = C["expected_rows"]["train"]
    S = TU.schedule(max(n, 1), C["per_device_batch"], C["grad_accum"], C["epochs"], C["warmup_ratio"], C.get("eval_every_steps"), C.get("eval_every_epochs"))
    return f"""# Run plan (generated from config.yaml by gen_train_docs.py; do not edit)

- base: `{C['base_model']}` @ `{C['base_revision']}`; LoRA r={C['lora']['r']} alpha={C['lora']['alpha']} dropout={C['lora']['dropout']}
- data: `{C['train_file']}` ({n} rows), `{C['val_file']}` ({C['expected_rows']['val']} rows), checked against `{C['dataset_sums']}`; output `{C['output_dir']}`
- optimiser: lr {C['lr']}, {C['scheduler']}, warmup {C['warmup_ratio']}, batch {C['per_device_batch']} x grad_accum {C['grad_accum']} = {C['per_device_batch'] * C['grad_accum']} sequences/step, {C['epochs']} epochs
- schedule: {S['steps_per_epoch']} steps/epoch (last window {S['last_window']} micro-batches), {S['total_steps']} total, warmup {S['warmup_steps']} steps
- mid-run evals (and midcheck) at steps {S['eval_steps']} plus the end; checkpoint every {C['save_every_steps']} steps, keep {C['keep_checkpoints']}; hard stop after {C['max_hours']} h
- example weights: {'ON' if C.get('use_example_weight') else 'OFF'}
"""


if __name__ == "__main__":
    t = render()
    if "--check" in sys.argv: sys.exit(0 if os.path.exists(OUT) and open(OUT).read() == t else 1)
    open(OUT, "w").write(t); print(t)
