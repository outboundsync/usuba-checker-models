#!/usr/bin/env python3
"""bf16 LoRA SFT for Usuba on Qwen 3.5 9B. Loss on assistant tokens only, optional per-example weights.
  python3 train_lora.py --config config.yaml            # real run (GPU)
  python3 train_lora.py --config config.yaml --dry-run  # CPU: tokenize, mask, length stats; no model weights loaded"""
import argparse, glob, hashlib, json, os, random, shutil, signal, sys, time
import yaml
p = argparse.ArgumentParser(); p.add_argument("--config", default="config.yaml"); p.add_argument("--dry-run", action="store_true")
p.add_argument("--limit", type=int, default=0, help="only for the CPU smoke test; skips the row-count assertion")
p.add_argument("--max-steps", type=int, default=0, help="stop after N optimizer steps (CPU smoke test)")
p.add_argument("--resume", action="store_true", help="continue from the newest complete checkpoint in <output_dir>/checkpoints")
p.add_argument("--midcheck", default="", help="OPTIONAL: `auto` = at every eval step, or comma-separated optimizer steps (e.g. 100 or 100,300) at which to score held-out plugins for 'names the real bug at the right file:line' with the in-memory model; also runs once at the end. Failure never stops training.")
p.add_argument("--midcheck-n", type=int, default=30, help="plugins per midcheck"); p.add_argument("--midcheck-pool", default="", help="pool jsonl(.gz) (default: config val_file); Dell-key/holdout rows are always excluded")
p.add_argument("--midcheck-max-new", type=int, default=2048, help="at least the eval's max_tokens (audit A10)"); p.add_argument("--midcheck-max-secs", type=int, default=1200)
a = p.parse_args()
C = yaml.safe_load(open(a.config)); H = os.path.dirname(os.path.abspath(a.config))
path = lambda x: x if os.path.isabs(x) else os.path.join(H, x)
from transformers import AutoTokenizer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import loss_utils, train_utils as TU, paths as PATHS
VW = float(C.get("verdict_token_weight", 1.0))
FAP = float(C.get("false_alarm_penalty", 1.0))   # >1 upweights approve rows (false-alarm penalty); 1.0 = off. Never set it from the test sets: tune on val only (docs/TRAINING_PLAN.md)
# A9: the base model revision is pinned; builders, trainer and export use the same snapshot
REV = C.get("base_revision") or sys.exit("config.yaml needs base_revision (pin the base model snapshot)")
assert REV == PATHS.BASE_REVISION, f"config base_revision {REV} != paths.BASE_REVISION {PATHS.BASE_REVISION}"
tok = AutoTokenizer.from_pretrained(C["base_model"], revision=REV)

def encode(rec):
    msgs = rec["messages"]
    prompt_ids = tok.apply_chat_template(msgs[:-1], tokenize=True, add_generation_prompt=True, enable_thinking=False)
    full_ids = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=False, enable_thinking=False)
    if hasattr(prompt_ids, "input_ids"): prompt_ids, full_ids = prompt_ids["input_ids"], full_ids["input_ids"]
    if full_ids[:len(prompt_ids)] != prompt_ids: raise ValueError("chat template prefix mismatch")
    labels = [-100] * len(prompt_ids) + full_ids[len(prompt_ids):]
    return dict(input_ids=full_ids, labels=labels, tokw=loss_utils.token_weights(tok, labels, VW), weight=TU.example_weight(rec, C.get("use_example_weight"), FAP), source=rec.get("source"))

def load(fn):
    """A6: reads .jsonl or .jsonl.gz; A12: every row passes the content/provenance holdout guard; empty targets and over-length rows are dropped AND counted"""
    raw = TU.read_rows(path(fn))
    if a.limit: raw = raw[:a.limit]
    bad = GUARD.check(raw)
    if bad: sys.exit(f"HOLDOUT GUARD at load ({fn}): {len(bad)} row(s) rejected, e.g. {list(bad.items())[:5]}")
    rows, dropped, lens, empty = [], 0, [], 0
    for r in raw:
        e = encode(r); lens.append(len(e["input_ids"]))
        if not any(y != -100 for y in e["labels"]): empty += 1; continue
        if len(e["input_ids"]) > C["max_len"]: dropped += 1; continue
        rows.append(e)
    TU.drop_check(dropped + empty, len(raw), C.get("max_drop_rate", 0.02))
    return rows, dropped + empty, lens, len(raw)

# A6: no silent fallback. The data files named in the config must exist, verify against SHA256SUMS, and have the expected row counts.
import holdout_guard; GUARD = holdout_guard.Guard()
TF, VF = path(C["train_file"]), path(C["val_file"])
DATA_SHA = TU.verify_sums(path(C["dataset_sums"]), [TF, VF])
t0 = time.time(); train, dtr, ltr, ntr_raw = load(C["train_file"]); val, dva, lva, nva_raw = load(C["val_file"])
if not a.limit: TU.check_row_counts({"train": ntr_raw, "val": nva_raw}, C["expected_rows"])
SCHED = TU.schedule(len(train), C["per_device_batch"], C["grad_accum"], C["epochs"], C["warmup_ratio"], C.get("eval_every_steps"), C.get("eval_every_epochs"), bool(C.get("allow_no_midrun_eval")))
s = sorted(ltr); tot = sum(min(x, C["max_len"]) for x in ltr)
stats = dict(train=len(train), train_dropped_overlength=dtr, val=len(val), val_dropped=dva, tok_median=s[len(s)//2], tok_p95=s[int(len(s)*.95)], tok_max=s[-1],
             train_tokens=tot, assistant_tokens=sum(sum(1 for y in r["labels"] if y != -100) for r in train),
             verdict_token_weight=VW, rows_with_weighted_verdict=sum(1 for r in train if VW != 1.0 and max(r["tokw"]) == VW),
             steps_per_epoch=SCHED["steps_per_epoch"], tokenize_secs=round(time.time() - t0, 1), rows_raw=dict(train=ntr_raw, val=nva_raw), dataset_sha256=DATA_SHA,
             holdout_guard_fingerprints_sha256=GUARD.fp_sha)
print(json.dumps(stats, indent=1)); print("SCHEDULE " + json.dumps(SCHED))
if a.dry_run:
    r = train[0]; lab = [t for t in r["labels"] if t != -100]
    print("--- sample target (decoded from labels) ---\n" + tok.decode(lab)[:600])
    print("--- verdict tokens (weight %.1f) ---\n%r" % (VW, tok.decode([t for t, w in zip(r["input_ids"], r["tokw"]) if w == VW])))
    json.dump(stats, open(path("dry_run_stats.json"), "w"), indent=1); sys.exit(0)

import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, get_scheduler
from peft import LoraConfig, get_peft_model
torch.manual_seed(C["seed"]); random.seed(C["seed"])
dev = "cuda" if torch.cuda.is_available() else "cpu"
assert dev == "cuda" or os.environ.get("ALLOW_CPU") == "1", "GPU required for the real run (ALLOW_CPU=1 only for the tiny-model smoke test)"
model = AutoModelForCausalLM.from_pretrained(C["base_model"], revision=REV, dtype=torch.bfloat16, device_map={"": 0} if dev == "cuda" else None, attn_implementation="sdpa")
model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False}); model.config.use_cache = False
suf = tuple(C["lora_target_suffixes"])
targets = sorted({n for n, m in model.named_modules() if isinstance(m, torch.nn.Linear) and n.split(".")[-1] in suf and "visual" not in n and "vision" not in n})
print(f"LoRA on {len(targets)} linear modules", flush=True)
model = get_peft_model(model, LoraConfig(r=C["lora"]["r"], lora_alpha=C["lora"]["alpha"], lora_dropout=C["lora"]["dropout"], target_modules=targets, task_type="CAUSAL_LM"))
for prm in model.parameters():
    if prm.requires_grad: prm.data = prm.data.float()   # LoRA weights + Adam state in fp32 (base stays bf16)
model.enable_input_require_grads(); model.print_trainable_parameters()

def collate(b):
    n = max(len(x["input_ids"]) for x in b); pad = tok.pad_token_id or 0
    ids = torch.tensor([x["input_ids"] + [pad] * (n - len(x["input_ids"])) for x in b])
    lab = torch.tensor([x["labels"] + [-100] * (n - len(x["labels"])) for x in b])
    att = torch.tensor([[1] * len(x["input_ids"]) + [0] * (n - len(x["input_ids"])) for x in b])
    tw = torch.tensor([x["tokw"] + [0.0] * (n - len(x["tokw"])) for x in b])
    return ids, lab, att, torch.tensor([x["weight"] for x in b]), tw
def fwd_loss(ids, lab, att, w, tw=None):
    """Only the assistant span (always the sequence tail) goes through lm_head: logits for a 7k-token prompt x 248k vocab
    would cost ~7 GB in fp32 for nothing, since prompt tokens carry no loss."""
    ids, lab, att = ids.to(dev), lab.to(dev), att.to(dev); n = ids.size(1)
    first = min(int((row != -100).nonzero()[0]) for row in lab)
    k = n - first + 1
    logits = model(input_ids=ids, attention_mask=att, logits_to_keep=k).logits      # positions n-k .. n-1
    lg = logits[:, :-1].float(); lb = lab[:, n - k + 1:]
    tl = torch.nn.functional.cross_entropy(lg.reshape(-1, lg.size(-1)), lb.reshape(-1), ignore_index=-100, reduction="none").view(lb.shape)
    m = (lb != -100).float()
    if tw is None: per = (tl * m).sum(1) / m.sum(1).clamp(min=1)              # plain masked mean (val loss, comparable to v1)
    else: per = loss_utils.weighted_seq_loss(tl, tw.to(dev)[:, n - k + 1:] * m)   # verdict value tokens x verdict_token_weight
    return per      # [B] per-example loss; weighting happens in the loop (A4: train_utils.weighted_micro_loss)
out = path(C["output_dir"]); CK = os.path.join(out, "checkpoints"); os.makedirs(CK, exist_ok=True)
LOGP = os.path.join(out, "train_log.jsonl")
vdl = DataLoader(val, batch_size=1, collate_fn=collate)
opt = torch.optim.AdamW([q for q in model.parameters() if q.requires_grad], lr=C["lr"], weight_decay=C["weight_decay"])
total = SCHED["total_steps"]      # exact: every epoch flushes its short last window (H)
sch = get_scheduler(C["scheduler"], opt, num_warmup_steps=int(total * C["warmup_ratio"]), num_training_steps=total)

def sha(fn):
    h = hashlib.sha256()
    with open(fn, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def write_sums(d):
    fs = sorted(os.path.relpath(os.path.join(r, f), d) for r, _, ff in os.walk(d) for f in ff if f != "SHA256SUMS")
    open(os.path.join(d, "SHA256SUMS"), "w").write("".join(f"{sha(os.path.join(d, f))}  {f}\n" for f in fs))
def save_adapter(tag):
    d = os.path.join(out, tag); tmp = d + ".tmp"; shutil.rmtree(tmp, ignore_errors=True)
    model.save_pretrained(tmp); tok.save_pretrained(tmp); write_sums(tmp)
    shutil.rmtree(d, ignore_errors=True); os.replace(tmp, d); print("saved", d, flush=True)
state = dict(step=0, epoch=0, micro=0, best=1e9)
def save_ckpt(reason):
    """Full resumable checkpoint (adapter + optimizer + scheduler + data position + RNG). Written to a temp dir, then
    renamed, so a crash mid-save never leaves a half checkpoint marked complete. Keeps the newest C['keep_checkpoints']."""
    d = os.path.join(CK, f"step-{state['step']:06d}"); tmp = d + ".tmp"; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    model.save_pretrained(os.path.join(tmp, "adapter"))
    torch.save(dict(opt=opt.state_dict(), sch=sch.state_dict(), state=state, reason=reason, py_rng=random.getstate(), torch_rng=torch.get_rng_state(),
                    cuda_rng=torch.cuda.get_rng_state_all() if dev == "cuda" else None), os.path.join(tmp, "trainer_state.pt"))
    json.dump(dict(state, reason=reason, time=time.time()), open(os.path.join(tmp, "meta.json"), "w"))
    write_sums(tmp); open(os.path.join(tmp, "COMPLETE"), "w").write(reason)
    shutil.rmtree(d, ignore_errors=True); os.replace(tmp, d)
    for old in sorted(glob.glob(os.path.join(CK, "step-*[0-9]")))[:-C.get("keep_checkpoints", 3)]: shutil.rmtree(old, ignore_errors=True)
    print(f"checkpoint {d} ({reason})", flush=True)
def latest_ckpt():
    c = [d for d in sorted(glob.glob(os.path.join(CK, "step-*[0-9]"))) if os.path.exists(os.path.join(d, "COMPLETE"))]
    return c[-1] if c else None
if a.resume and (ck := latest_ckpt()):
    from peft import set_peft_model_state_dict
    from safetensors.torch import load_file
    set_peft_model_state_dict(model, load_file(os.path.join(ck, "adapter", "adapter_model.safetensors")))
    for prm in model.parameters():
        if prm.requires_grad: prm.data = prm.data.float()
    ts = torch.load(os.path.join(ck, "trainer_state.pt"), weights_only=False)
    opt.load_state_dict(ts["opt"]); sch.load_state_dict(ts["sch"]); state.update(ts["state"])
    random.setstate(ts["py_rng"]); torch.set_rng_state(ts["torch_rng"])
    if ts.get("cuda_rng") and dev == "cuda": torch.cuda.set_rng_state_all(ts["cuda_rng"])
    print(f"resumed from {ck}: step {state['step']} epoch {state['epoch']} micro {state['micro']}", flush=True)
    print(f"train_log.jsonl: dropped {TU.truncate_log(LOGP, state['step'])} duplicate record(s) beyond step {state['step']}", flush=True)
elif a.resume: print("--resume: no complete checkpoint found, starting fresh", flush=True)
log = open(LOGP, "a")
# H: record every input of the run (both repos' SHAs, resolved config, data hashes, base revision, pip freeze, prompt hash, GPU/driver, determinism flags)
def write_run_meta():
    import subprocess, platform
    def cmd(c):
        try: return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=120).stdout.strip()
        except (OSError, subprocess.SubprocessError): return None
    pv = None
    try: import prompt_v4; pv = prompt_v4.PROMPT_SHA256
    except ImportError: pass
    try: ckr = PATHS.checker_root()
    except FileNotFoundError: ckr = None   # run meta records checker_repo=None; the run itself already needs the Checker
    meta = dict(written=time.strftime("%Y-%m-%dT%H:%M:%S%z"), models_repo=PATHS.git_info(PATHS.REPO), checker_repo=PATHS.git_info(ckr) if ckr else None,
                rules_hash=PATHS.rules_hash(ckr) if ckr else None, config=C, base_revision=REV, data_sha256=DATA_SHA, schedule=SCHED, prompt_sha256=pv,
                holdout_guard_fingerprints_sha256=GUARD.fp_sha, pip_freeze=cmd("pip freeze"), python=platform.python_version(), torch=torch.__version__,
                gpu=cmd("nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader") if dev == "cuda" else "cpu",
                determinism=dict(seed=C["seed"], cudnn_deterministic=torch.backends.cudnn.deterministic, cudnn_benchmark=torch.backends.cudnn.benchmark,
                                 use_deterministic_algorithms=torch.are_deterministic_algorithms_enabled(), sdpa="default", note="dataloader order seeded per epoch; no deterministic-kernel flag set"))
    json.dump(meta, open(os.path.join(out, "run_meta.json"), "w"), indent=1, default=str)
write_run_meta()

# ---- optional mid-training check (train/midcheck.py); every failure is swallowed ----
MID = {"steps": set(), "rows": [], "done": set()}
if a.midcheck:
    try:
        import midcheck
        MID["steps"] = set(SCHED["eval_steps"]) if a.midcheck == "auto" else {int(x) for x in a.midcheck.split(",") if x.strip()}
        MID["rows"], _sk = midcheck.build_pool(path(a.midcheck_pool or C["val_file"]), a.midcheck_n, seed=C["seed"], allow_dell_sources=True)
        print(f"midcheck on at steps {sorted(MID['steps'])} + end: {len(MID['rows'])} plugins (skipped {_sk})", flush=True)
        if os.path.exists(os.path.join(out, "midcheck.jsonl")):
            MID["done"] = {json.loads(l).get("tag") for l in open(os.path.join(out, "midcheck.jsonl")) if l.strip()}
    except Exception as e:     # A10: a requested midcheck that cannot be set up is fatal, never silently off
        sys.exit(f"[midcheck] requested but setup failed: {type(e).__name__}: {e}")
def run_mid(tag):
    if not a.midcheck or not MID["rows"] or tag in MID["done"]: return
    try:
        was_training = model.training; model.eval(); model.config.use_cache = True
        try:
            ms = midcheck.run_midcheck(state["step"], MID["rows"], midcheck.hf_generator(model, tok, a.midcheck_max_new), out, log=log, max_secs=a.midcheck_max_secs, tag=tag)
            if ms and ms.get("selection_score") is not None and ms["selection_score"] > state.get("best_task", -1):   # H: checkpoint choice on a task metric that includes negatives
                state["best_task"] = ms["selection_score"]; save_adapter("best-task")
        finally:
            model.config.use_cache = False
            if was_training: model.train()
            if dev == "cuda": torch.cuda.empty_cache()
        MID["done"].add(tag)
    except BaseException as e:
        if isinstance(e, (KeyboardInterrupt, SystemExit)): raise
        print(f"[midcheck] failed (ignored): {type(e).__name__}", flush=True)

STOP = {"sig": None}
def on_signal(sig, _): STOP["sig"] = signal.Signals(sig).name; print(f"got {STOP['sig']}: will checkpoint and exit after this step", flush=True)
signal.signal(signal.SIGTERM, on_signal); signal.signal(signal.SIGINT, on_signal)
def evaluate():
    model.eval(); L = []
    with torch.no_grad():
        for ids, lab, att, w, tw in vdl: L.append(fwd_loss(ids, lab, att, w).mean().item())
    model.train(); return sum(L) / len(L)
hours0 = state.get("hours", 0.0); model.train(); acc = 0.0
_t0 = time.time()
if state["step"] == 0 and os.environ.get("SKIP_INITIAL_EVAL") == "1": print(json.dumps(dict(total_optimizer_steps=total, val_loss_start=None)), flush=True)
elif state["step"] == 0: print(json.dumps(dict(total_optimizer_steps=total, val_loss_start=evaluate(), eval_secs=round(time.time() - _t0, 1))), flush=True)
start = time.time()   # FIX: max_hours clock starts after the initial eval (it took ~5 min and ate the whole 6-min dry-run budget)
def stop_and_exit(reason, code):
    save_ckpt(reason); save_adapter("last"); open(os.path.join(out, "STOPPED"), "w").write(reason); sys.exit(code)
for ep in range(state["epoch"], C["epochs"]):
    g = torch.Generator().manual_seed(C["seed"] + ep)        # same order on resume
    order = torch.randperm(len(train), generator=g).tolist()
    dl = DataLoader([train[i] for i in order], batch_size=C["per_device_batch"], shuffle=False, collate_fn=collate)
    n_micro = len(dl)
    for i, (ids, lab, att, w, tw) in enumerate(dl):
        if i < state["micro"]: continue                       # already trained before the checkpoint
        per = fwd_loss(ids, lab, att, w, tw)
        loss = TU.weighted_micro_loss(per, w.to(per.device), TU.window_size(i, n_micro, C["grad_accum"]))   # A4 + H: real weights, short last window divided by its true size
        loss.backward(); acc += loss.item(); state["micro"] = i + 1
        if (i + 1) % C["grad_accum"] and i + 1 != n_micro: continue
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sch.step(); opt.zero_grad(); state["step"] += 1
        state["hours"] = hours0 + (time.time() - start) / 3600
        rec = dict(step=state["step"], epoch=ep, loss=round(acc, 4), lr=sch.get_last_lr()[0], hours=round(state["hours"], 3), t=round(time.time(), 1),
                   mem_gb=round((torch.cuda.max_memory_allocated() / 2**30 if dev == "cuda" else 0), 1)); acc = 0.0
        if state["step"] in SCHED["eval_steps"]:
            rec["val_loss"] = evaluate()
            if rec["val_loss"] < state["best"]: state["best"] = rec["val_loss"]; save_adapter("best")
        log.write(json.dumps(rec) + "\n"); log.flush(); print(json.dumps(rec), flush=True)
        if state["step"] in MID["steps"]: run_mid(f"step-{state['step']}")
        if state["step"] % C["save_every_steps"] == 0: save_ckpt("periodic"); save_adapter("last")
        if state["hours"] > C["max_hours"]: print("max_hours reached: checkpointing before exit", flush=True); stop_and_exit("max_hours", 0)
        if STOP["sig"]: stop_and_exit("signal " + STOP["sig"], 143)
        if a.max_steps and state["step"] >= a.max_steps: print(f"--max-steps {a.max_steps} reached", flush=True); stop_and_exit("max_steps", 0)
    state["epoch"] = ep + 1; state["micro"] = 0
rec = dict(step=state["step"], final_val_loss=evaluate()); print(json.dumps(rec)); log.write(json.dumps(rec) + "\n")
if rec["final_val_loss"] < state["best"]: state["best"] = rec["final_val_loss"]; save_adapter("best")
save_ckpt("final"); save_adapter("last"); run_mid("final"); open(os.path.join(out, "DONE"), "w").write(json.dumps(rec))
