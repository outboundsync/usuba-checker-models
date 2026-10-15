"""Pure-python helpers of train_lora.py (testable on CPU): dataset loading/verification, schedule, loss weighting, log hygiene (audit A4, A6, A8, H)."""
import gzip, hashlib, json, math, os


def open_text(path):
    return gzip.open(path, "rt", encoding="utf-8") if str(path).endswith(".gz") else open(path, "rt", encoding="utf-8")


def read_rows(path):
    with open_text(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def sha256_file(fn):
    h = hashlib.sha256()
    with open(fn, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def verify_sums(sums_path, files):
    """SHA256SUMS ('<hex>  <name>' lines, names relative to the SUMS file) must list every file in `files` and match. Raises SystemExit otherwise."""
    d = os.path.dirname(os.path.abspath(sums_path))
    if not os.path.exists(sums_path): raise SystemExit(f"DATASET: {sums_path} missing; refusing to train on unverified data")
    want = {}
    for l in open(sums_path):
        if l.strip():
            h, n = l.split(None, 1); want[n.strip().lstrip("*")] = h
    out = {}
    for f in files:
        n = os.path.relpath(os.path.abspath(f), d)
        if n not in want: raise SystemExit(f"DATASET: {n} is not listed in {sums_path}")
        got = sha256_file(f)
        if got != want[n]: raise SystemExit(f"DATASET: sha256 mismatch for {n}: file {got[:12]} != SHA256SUMS {want[n][:12]}")
        out[n] = got
    return out


def check_row_counts(counts, expected):
    for k, v in expected.items():
        if counts.get(k) != v: raise SystemExit(f"DATASET: {k} has {counts.get(k)} rows, config expects {v}")


def schedule(n_train, per_device_batch, grad_accum, epochs, warmup_ratio, eval_every_steps=None, eval_every_epochs=None, allow_no_midrun_eval=False):
    """Exact optimizer-step schedule. Every epoch flushes a partial accumulation window, so steps = epochs * ceil(micro/GA) with
    micro = ceil(n/B). Eval cadence is given in epochs (preferred) or steps; zero mid-run evals is an error."""
    micro = math.ceil(n_train / per_device_batch); spe = math.ceil(micro / grad_accum); total = spe * epochs
    if eval_every_epochs: every = max(1, round(spe * eval_every_epochs))
    elif eval_every_steps: every = int(eval_every_steps)
    else: raise SystemExit("config needs eval_every_epochs or eval_every_steps")
    evals = [s for s in range(every, total, every)]            # strictly before the final step (the end eval always runs)
    if not evals and not allow_no_midrun_eval: raise SystemExit(f"SCHEDULE: no mid-training eval: total steps {total}, eval every {every}")
    warm = int(total * warmup_ratio)
    return dict(micro_per_epoch=micro, steps_per_epoch=spe, total_steps=total, warmup_steps=warm, eval_every_steps=every, eval_steps=evals, last_window=micro - (spe - 1) * grad_accum)


def window_size(i, n_micro, grad_accum):
    """number of micro-batches in the accumulation window that contains micro-batch index i (the last window of an epoch can be short)"""
    start = (i // grad_accum) * grad_accum
    return min(grad_accum, n_micro - start)


def weighted_micro_loss(per_example_loss, weights, n_window):
    """Loss of one micro-batch. Divides by the window size (constant), NOT by the sum of the batch's weights: with per_device_batch=1 the old
    (per*w).sum()/w.sum() was always `per`, so example weights never had any effect (audit A4). A weight-2 example now gets twice the gradient."""
    return (per_example_loss * weights).sum() / (per_example_loss.numel() * n_window)


def truncate_log(path, last_step):
    """After a resume: drop log records beyond the restored step so train_log.jsonl has no duplicated steps."""
    if not os.path.exists(path): return 0
    keep, dropped = [], 0
    for l in open(path):
        try: r = json.loads(l)
        except Exception: continue
        if isinstance(r.get("step"), int) and r["step"] > last_step and "midcheck" not in r: dropped += 1; continue
        keep.append(l if l.endswith("\n") else l + "\n")
    open(path, "w").writelines(keep); return dropped


def drop_check(dropped, total, max_rate):
    if total and dropped / total > max_rate:
        raise SystemExit(f"DATASET: {dropped}/{total} rows ({dropped / total:.1%}) dropped (over-length or empty target); limit {max_rate:.1%}")


def verify_cli(config_path, data_dir):
    """python3 train_utils.py verify config.yaml DATA_DIR : SHA256SUMS + row counts of the files named in the config (used by launch_vast.sh bundle)"""
    import yaml
    C = yaml.safe_load(open(config_path)); tr, va = (os.path.join(data_dir, os.path.basename(C[k])) for k in ("train_file", "val_file"))
    sums = os.path.join(data_dir, "SHA256SUMS")
    verify_sums(sums, [tr, va])
    n = dict(train=len(read_rows(tr)), val=len(read_rows(va)))
    exp = C.get("expected_rows") or {}
    if not exp or not all(exp.get(k) for k in ("train", "val")): raise SystemExit(f"DATASET: config expected_rows not filled in ({exp}); finalize the build first")
    check_row_counts(n, exp)
    print(f"dataset OK: {n}, sha256 verified against {sums}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 4 and sys.argv[1] == "verify": verify_cli(sys.argv[2], sys.argv[3])
    else: raise SystemExit(__doc__)


def example_weight(rec, use_example_weight=False, false_alarm_penalty=1.0):
    """Per-example loss weight. false_alarm_penalty (default 1.0 = off) multiplies the weight of every APPROVE-target row: a model that answers
    "changes requested" on a clean plugin pays that factor more, which pushes the false-alarm rate down at some cost in recall (r5 baseline: 0.93 false alarms).
    The val-tuned threshold plan in docs/TRAINING_PLAN.md says how the factor is chosen. The target verdict is read from the row's final assistant message."""
    import json
    w = float(rec.get("weight", 1.0)) if use_example_weight else 1.0
    if false_alarm_penalty != 1.0:
        try: v = json.loads(rec["messages"][-1]["content"]).get("verdict")
        except (ValueError, KeyError, IndexError, AttributeError): v = None
        if v == "approve": w *= float(false_alarm_penalty)
    return w
