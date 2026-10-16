#!/usr/bin/env python3
"""Export parity check (audit H): the quantised GGUF must agree with the HF base+adapter on held-out VAL rows (never the sealed holdout).
  python3 export_parity.py <gguf> <adapter_dir> [--n 12] [--min-agree 0.75]
Greedy decoding on both sides, same chat-template prompt. Compares the parsed verdict and the (file,line) set; exits 1 below --min-agree."""
import argparse, os, sys, re, subprocess, yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # repo root: scope.schema
import paths, train_utils
p = argparse.ArgumentParser(); p.add_argument("gguf"); p.add_argument("adapter"); p.add_argument("--n", type=int, default=12); p.add_argument("--min-agree", type=float, default=0.75)
p.add_argument("--max-new", type=int, default=768); p.add_argument("--ctx", type=int, default=40960, help="llama-cli context (default 4096 would truncate 12k+ token prompts)"); a = p.parse_args()
C = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")))
HERE = os.path.dirname(os.path.abspath(__file__))
rows = train_utils.read_rows(C["val_file"] if os.path.isabs(C["val_file"]) else os.path.join(HERE, C["val_file"]))[: a.n]
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
tok = AutoTokenizer.from_pretrained(C["base_model"], revision=paths.BASE_REVISION)
m = PeftModel.from_pretrained(AutoModelForCausalLM.from_pretrained(C["base_model"], revision=paths.BASE_REVISION, dtype=torch.bfloat16, device_map={"": 0}), a.adapter).eval()


def sig(txt):
    """scope-v4 schema: (verdict, triage decisions by (rule,file,line), added findings by (category,file,line)); regex fallback if the JSON does not parse"""
    from scope import schema
    o = schema.extract_json(txt)
    if o:
        tri = tuple(sorted((str(t.get("rule")), str(t.get("file")), str(t.get("line")), str(t.get("decision"))) for t in o.get("scripts_triage") or [] if isinstance(t, dict)))
        add = tuple(sorted((str(t.get("category")), str(t.get("file")), str(t.get("line"))) for t in o.get("added_findings") or [] if isinstance(t, dict)))
        return (o.get("verdict"), tri, add)
    v = re.search(r'"verdict"\s*:\s*"(\w+)"', txt)
    return (v.group(1) if v else None, ("unparsed", txt[:80]), ())


agree = 0
for r in rows:
    msgs = r["messages"][:-1]; prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)   # same as train_lora.encode / eval
    ids = tok(prompt, return_tensors="pt").to(0)
    with torch.no_grad(): out = m.generate(**ids, max_new_tokens=a.max_new, do_sample=False)
    hf = tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
    open("/tmp/parity_prompt.txt", "w").write(prompt)
    g = subprocess.run([os.path.join(paths.llama_cpp_dir(), "build", "bin", "llama-cli"), "-m", a.gguf, "-f", "/tmp/parity_prompt.txt", "-n", str(a.max_new), "--temp", "0", "-c", str(a.ctx), "-no-cnv", "--no-display-prompt", "-ngl", "99"], capture_output=True, text=True, timeout=900).stdout
    ok = sig(hf) == sig(g) and sig(hf)[0] is not None; agree += ok
    print(("AGREE " if ok else "DIFFER"), sig(hf)[0], sig(g)[0], flush=True)
rate = agree / max(1, len(rows)); print(f"parity {agree}/{len(rows)} = {rate:.2f}")
sys.exit(0 if rate >= a.min_agree else 1)
