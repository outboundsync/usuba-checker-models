#!/usr/bin/env python3
"""Merge the LoRA into the bf16 base, then export GGUF and quantize to Q4_K_M (~5.5 GB) for a 32 GB laptop (llama.cpp, CPU/iGPU).
  python3 export_gguf.py --adapter out/<output_dir>/best-task --out out/export
Audit A9/H: base model pinned (paths.BASE_REVISION), llama.cpp pinned (LLAMA_CPP_COMMIT), unique output names (adapter dir name + step), sha256 written and compared on re-run, parity check script emitted."""
import argparse, os, shutil, subprocess, hashlib, yaml, torch, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import paths
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
p = argparse.ArgumentParser(); p.add_argument("--adapter", required=True); p.add_argument("--out", required=True); p.add_argument("--quant", default="Q4_K_M"); a = p.parse_args()
C = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")))
# big intermediates (merged bf16 ~18 GB, bf16 GGUF ~18 GB) go to RAM-backed /dev/shm when it has room: Vast container disks can be small
TMP = "/dev/shm/usuba_export" if os.path.isdir("/dev/shm") and shutil.disk_usage("/dev/shm").free > 60e9 else a.out
os.makedirs(a.out, exist_ok=True); merged = os.path.join(TMP, "merged-bf16"); os.makedirs(merged, exist_ok=True)
LLAMA = paths.llama_cpp_dir(); REV = paths.BASE_REVISION; LLAMA_CPP_COMMIT = os.environ.get("LLAMA_CPP_COMMIT", "")   # REQUIRED below: a moving llama.cpp HEAD changes quantisation/convert behaviour between runs
if not LLAMA_CPP_COMMIT and not os.path.isdir(os.path.join(LLAMA, ".git")): raise SystemExit("set LLAMA_CPP_COMMIT=<sha> (pin it in deps.sh; recorded in the export meta)")
m = AutoModelForCausalLM.from_pretrained(C["base_model"], revision=REV, dtype=torch.bfloat16, device_map={"": 0})
m = PeftModel.from_pretrained(m, a.adapter).merge_and_unload(); m.save_pretrained(merged, safe_serialization=True)
AutoTokenizer.from_pretrained(C["base_model"], revision=REV).save_pretrained(merged); del m; torch.cuda.empty_cache()
sh = lambda c: (print("+", c, flush=True), subprocess.run(c, shell=True, check=True))
if not os.path.isdir(LLAMA):
    sh(f"git clone https://github.com/ggml-org/llama.cpp {LLAMA}")
if LLAMA_CPP_COMMIT: sh(f"git -C {LLAMA} fetch -q origin {LLAMA_CPP_COMMIT} || true; git -C {LLAMA} checkout -q {LLAMA_CPP_COMMIT}")
LLAMA_SHA = subprocess.run(["git", "-C", LLAMA, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
# NOT llama.cpp's requirements file: it pins transformers 4.x and a CPU torch, which breaks Qwen 3.5 and the training env
sh(f"pip install -q --no-deps {LLAMA}/gguf-py && pip install -q sentencepiece numpy protobuf")
sh(f"cmake -S {LLAMA} -B {LLAMA}/build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF >/dev/null && cmake --build {LLAMA}/build -j --target llama-quantize llama-cli >/dev/null")
f16 = os.path.join(TMP, "usuba-9b-bf16.gguf"); ad = os.path.abspath(a.adapter).rstrip("/").split("/"); tag = "-".join(ad[-2:])   # unique per adapter (e.g. checkpoints-step-300, usuba-lora-best-task): never overwrites another export
q = os.path.join(a.out, f"usuba-9b-{tag}-{a.quant}.gguf")
sh(f"python3 {LLAMA}/convert_hf_to_gguf.py {merged} --outtype bf16 --outfile {f16}")
shutil.rmtree(merged, ignore_errors=True)
sh(f"{LLAMA}/build/bin/llama-quantize {f16} {q} {a.quant}")
os.remove(f16)
h = hashlib.sha256(open(q, "rb").read()).hexdigest()
if os.path.exists(q + ".sha256"):   # re-export of the same adapter: GGUF conversion is not guaranteed bit-stable, so a difference is reported, not hidden
    old = open(q + ".sha256").read().split()[0]; print("sha256 vs previous export:", "SAME" if old == h else f"DIFFERENT (old {old[:12]} new {h[:12]})")
open(q + ".sha256", "w").write(f"{h}  {os.path.basename(q)}\n")
import json; json.dump(dict(adapter=a.adapter, base_model=C["base_model"], base_revision=REV, llama_cpp=LLAMA_SHA, quant=a.quant, sha256=h, checker_git=paths.git_info()), open(q + ".meta.json", "w"), indent=1)
sh(f"ls -la {a.out}")
# parity: the quantised GGUF must reproduce the merged bf16 model's behaviour on a few prompts. Run with: python3 export_parity.py <gguf> <adapter>
print("NEXT: python3 export_parity.py", q, a.adapter)
