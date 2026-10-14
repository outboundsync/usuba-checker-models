#!/usr/bin/env python3
"""Merge the LoRA into the bf16 base, then export GGUF and quantize to Q4_K_M (~5.5 GB) for a 32 GB laptop (llama.cpp, CPU/iGPU).
  python3 export_gguf.py --adapter out/usuba-9b-lora/best --out out/export"""
import argparse, os, shutil, subprocess, yaml, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
p = argparse.ArgumentParser(); p.add_argument("--adapter", required=True); p.add_argument("--out", required=True); p.add_argument("--quant", default="Q4_K_M"); a = p.parse_args()
C = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")))
# big intermediates (merged bf16 ~18 GB, bf16 GGUF ~18 GB) go to RAM-backed /dev/shm when it has room: Vast container disks can be small
TMP = "/dev/shm/usuba_export" if os.path.isdir("/dev/shm") and shutil.disk_usage("/dev/shm").free > 60e9 else a.out
os.makedirs(a.out, exist_ok=True); merged = os.path.join(TMP, "merged-bf16"); os.makedirs(merged, exist_ok=True)
m = AutoModelForCausalLM.from_pretrained(C["base_model"], dtype=torch.bfloat16, device_map={"": 0})
m = PeftModel.from_pretrained(m, a.adapter).merge_and_unload(); m.save_pretrained(merged, safe_serialization=True)
AutoTokenizer.from_pretrained(C["base_model"]).save_pretrained(merged); del m; torch.cuda.empty_cache()
sh = lambda c: (print("+", c, flush=True), subprocess.run(c, shell=True, check=True))
if not os.path.isdir("/workspace/llama.cpp"):
    sh("git clone --depth 1 https://github.com/ggml-org/llama.cpp /workspace/llama.cpp")
# NOT llama.cpp's requirements file: it pins transformers 4.x and a CPU torch, which breaks Qwen 3.5 and the training env
sh("pip install -q --no-deps /workspace/llama.cpp/gguf-py && pip install -q sentencepiece numpy protobuf")
sh("cmake -S /workspace/llama.cpp -B /workspace/llama.cpp/build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF >/dev/null && cmake --build /workspace/llama.cpp/build -j --target llama-quantize llama-cli >/dev/null")
f16 = os.path.join(TMP, "usuba-9b-bf16.gguf"); q = os.path.join(a.out, f"usuba-9b-{a.quant}.gguf")
sh(f"python3 /workspace/llama.cpp/convert_hf_to_gguf.py {merged} --outtype bf16 --outfile {f16}")
shutil.rmtree(merged, ignore_errors=True)
sh(f"/workspace/llama.cpp/build/bin/llama-quantize {f16} {q} {a.quant}")
os.remove(f16)
sh(f"ls -la {a.out}"); sh(f"sha256sum {q} > {q}.sha256")
