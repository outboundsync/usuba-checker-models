#!/usr/bin/env python3
"""bf16 LoRA SFT for Usuba on Qwen 3.5 9B. Loss on assistant tokens only, optional per-example weights.
  python3 train_lora.py --config config.yaml            # real run (GPU)
  python3 train_lora.py --config config.yaml --dry-run  # CPU: tokenize, mask, length stats; no model weights loaded"""
import argparse, json, math, os, random, sys, time
import yaml
p = argparse.ArgumentParser(); p.add_argument("--config", default="config.yaml"); p.add_argument("--dry-run", action="store_true")
p.add_argument("--limit", type=int, default=0); a = p.parse_args()
C = yaml.safe_load(open(a.config)); H = os.path.dirname(os.path.abspath(a.config))
path = lambda x: x if os.path.isabs(x) else os.path.join(H, x)
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained(C["base_model"])

def encode(rec):
    msgs = rec["messages"]
    prompt_ids = tok.apply_chat_template(msgs[:-1], tokenize=True, add_generation_prompt=True, enable_thinking=False)
    full_ids = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=False, enable_thinking=False)
    if hasattr(prompt_ids, "input_ids"): prompt_ids, full_ids = prompt_ids["input_ids"], full_ids["input_ids"]
    if full_ids[:len(prompt_ids)] != prompt_ids: raise ValueError("chat template prefix mismatch")
    labels = [-100] * len(prompt_ids) + full_ids[len(prompt_ids):]
    return dict(input_ids=full_ids, labels=labels, weight=float(rec.get("weight", 1.0)) if C.get("use_example_weight") else 1.0, source=rec.get("source"))

def load(fn):
    rows, dropped, lens = [], 0, []
    for i, l in enumerate(open(path(fn))):
        if a.limit and i >= a.limit: break
        e = encode(json.loads(l)); lens.append(len(e["input_ids"]))
        if len(e["input_ids"]) > C["max_len"]: dropped += 1; continue
        rows.append(e)
    return rows, dropped, lens

t0 = time.time(); train, dtr, ltr = load(C["train_file"]); val, dva, lva = load(C["val_file"])
s = sorted(ltr); tot = sum(min(x, C["max_len"]) for x in ltr)
stats = dict(train=len(train), train_dropped_overlength=dtr, val=len(val), val_dropped=dva, tok_median=s[len(s)//2], tok_p95=s[int(len(s)*.95)], tok_max=s[-1],
             train_tokens=tot, assistant_tokens=sum(sum(1 for y in r["labels"] if y != -100) for r in train),
             steps_per_epoch=math.ceil(len(train) / (C["per_device_batch"] * C["grad_accum"])), tokenize_secs=round(time.time() - t0, 1))
print(json.dumps(stats, indent=1))
if a.dry_run:
    r = train[0]; lab = [t for t in r["labels"] if t != -100]
    print("--- sample target (decoded from labels) ---\n" + tok.decode(lab)[:600])
    json.dump(stats, open(path("dry_run_stats.json"), "w"), indent=1); sys.exit(0)

import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, get_scheduler
from peft import LoraConfig, get_peft_model
torch.manual_seed(C["seed"]); random.seed(C["seed"])
dev = "cuda" if torch.cuda.is_available() else "cpu"
assert dev == "cuda" or os.environ.get("ALLOW_CPU") == "1", "GPU required for the real run (ALLOW_CPU=1 only for the tiny-model smoke test)"
model = AutoModelForCausalLM.from_pretrained(C["base_model"], dtype=torch.bfloat16, device_map={"": 0} if dev == "cuda" else None, attn_implementation="sdpa")
model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False}); model.config.use_cache = False
suf = tuple(C["lora_target_suffixes"])
targets = sorted({n for n, m in model.named_modules() if isinstance(m, torch.nn.Linear) and n.split(".")[-1] in suf and "visual" not in n and "vision" not in n})
print(f"LoRA on {len(targets)} linear modules", flush=True)
model = get_peft_model(model, LoraConfig(r=C["lora"]["r"], lora_alpha=C["lora"]["alpha"], lora_dropout=C["lora"]["dropout"], target_modules=targets, task_type="CAUSAL_LM"))
model.enable_input_require_grads(); model.print_trainable_parameters()

def collate(b):
    n = max(len(x["input_ids"]) for x in b); pad = tok.pad_token_id or 0
    ids = torch.tensor([x["input_ids"] + [pad] * (n - len(x["input_ids"])) for x in b])
    lab = torch.tensor([x["labels"] + [-100] * (n - len(x["labels"])) for x in b])
    att = torch.tensor([[1] * len(x["input_ids"]) + [0] * (n - len(x["input_ids"])) for x in b])
    return ids, lab, att, torch.tensor([x["weight"] for x in b])
def fwd_loss(ids, lab, att, w):
    """Only the assistant span (always the sequence tail) goes through lm_head: logits for a 7k-token prompt x 248k vocab
    would cost ~7 GB in fp32 for nothing, since prompt tokens carry no loss."""
    ids, lab, att = ids.to(dev), lab.to(dev), att.to(dev); n = ids.size(1)
    first = min(int((row != -100).nonzero()[0]) for row in lab)
    k = n - first + 1
    logits = model(input_ids=ids, attention_mask=att, logits_to_keep=k).logits      # positions n-k .. n-1
    lg = logits[:, :-1].float(); lb = lab[:, n - k + 1:]
    tl = torch.nn.functional.cross_entropy(lg.reshape(-1, lg.size(-1)), lb.reshape(-1), ignore_index=-100, reduction="none").view(lb.shape)
    m = (lb != -100).float(); per = (tl * m).sum(1) / m.sum(1).clamp(min=1)
    w = w.to(per.device); return (per * w).sum() / w.sum().clamp(min=1e-6)
dl = DataLoader(train, batch_size=C["per_device_batch"], shuffle=True, collate_fn=collate)
vdl = DataLoader(val, batch_size=1, collate_fn=collate)
opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=C["lr"], weight_decay=C["weight_decay"])
total = math.ceil(len(dl) * C["epochs"] / C["grad_accum"])
sch = get_scheduler(C["scheduler"], opt, num_warmup_steps=int(total * C["warmup_ratio"]), num_training_steps=total)
out = path(C["output_dir"]); os.makedirs(out, exist_ok=True); log = open(os.path.join(out, "train_log.jsonl"), "a")
def evaluate():
    model.eval(); L = []
    with torch.no_grad():
        for ids, lab, att, w in vdl:
            L.append(fwd_loss(ids, lab, att, torch.ones(1)).item())
    model.train(); return sum(L) / len(L)
def save(tag):
    d = os.path.join(out, tag); model.save_pretrained(d); tok.save_pretrained(d); print("saved", d, flush=True)
start = time.time(); step = 0; best = 1e9; model.train(); acc = 0.0
print(json.dumps(dict(total_optimizer_steps=total, val_loss_start=evaluate())), flush=True)
for ep in range(C["epochs"]):
    for i, (ids, lab, att, w) in enumerate(dl):
        loss = fwd_loss(ids, lab, att, w) / C["grad_accum"]
        loss.backward(); acc += loss.item()
        if (i + 1) % C["grad_accum"]: continue
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sch.step(); opt.zero_grad(); step += 1
        rec = dict(step=step, epoch=ep, loss=round(acc, 4), lr=sch.get_last_lr()[0], hours=round((time.time() - start) / 3600, 3),
                   mem_gb=round((torch.cuda.max_memory_allocated() / 2**30 if dev == "cuda" else 0), 1)); acc = 0.0
        if step % C["eval_every_steps"] == 0:
            rec["val_loss"] = evaluate()
            if rec["val_loss"] < best: best = rec["val_loss"]; save("best")
        if step % C["save_every_steps"] == 0: save("last")
        log.write(json.dumps(rec) + "\n"); log.flush(); print(json.dumps(rec), flush=True)
        if (time.time() - start) / 3600 > C["max_hours"]: print("max_hours reached, stopping"); save("last"); sys.exit(0)
rec = dict(step=step, final_val_loss=evaluate()); print(json.dumps(rec)); log.write(json.dumps(rec) + "\n")
if rec["final_val_loss"] < best: save("best")
save("last"); open(os.path.join(out, "DONE"), "w").write(json.dumps(rec))
