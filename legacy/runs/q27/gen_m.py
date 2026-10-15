"""Generate on a jsonl of chat rows with vLLM, for one or more models and a decode grid.
usage: gen_m.py FILE N name:model_dir[:adapter_dir] [name:model_dir ...]
  env: MAXTOK (default 28000), GRID "temp/rp,temp/rp" (default "0/1.05"), NSAMP (default 1), SEED (0), MAXLEN (32768)
  out: gen_{name}.jsonl if GRID has one setting and NSAMP=1, else gen_{name}_t{temp}_rp{rp}[_n{N}].jsonl
  Each distinct model_dir is run in its own subprocess, so every spec really uses its own model (the old version reused spec #1's model)."""
import json, os, sys, subprocess
def run_one(f, n, spec):
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest
    parts = spec.split(":"); name, mdir = parts[0], parts[1]; ad = parts[2] if len(parts) > 2 and parts[2] not in ("", "none") else None
    rows = [json.loads(l) for l in open(f)][:n]
    llm = LLM(mdir, max_model_len=int(os.environ.get("MAXLEN", 32768)), gpu_memory_utilization=0.92, max_num_seqs=int(os.environ.get("MAXSEQS",256)), enable_lora=bool(ad), max_lora_rank=64, seed=int(os.environ.get("SEED", 0)))
    tok = llm.get_tokenizer()
    ps = [tok.apply_chat_template(r["messages"][:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False) for r in rows]
    grid = [tuple(map(float, g.split("/"))) for g in os.environ.get("GRID", "0/1.05").split(",")]
    k = int(os.environ.get("NSAMP", 1)); mt = int(os.environ.get("MAXTOK", 28000))
    sps = [SamplingParams(temperature=t, top_p=0.95 if t > 0 else 1.0, max_tokens=mt, repetition_penalty=rp, n=k, seed=int(os.environ.get("SEED", 0)) if t > 0 else None) for t, rp in grid]
    # one generate call over the whole grid so vLLM batches all settings together
    outs = llm.generate([p for _ in grid for p in ps], [sp for sp in sps for _ in ps], lora_request=LoRARequest(name, 1, ad) if ad else None)
    for gi, (t, rp) in enumerate(grid):
        fn = f"gen_{name}.jsonl" if len(grid) == 1 and k == 1 else f"gen_{name}_t{t:g}_rp{rp:g}" + (f"_n{k}" if k > 1 else "") + ".jsonl"
        with open(fn, "w") as fo:
            for r, o in zip(rows, outs[gi * len(ps):(gi + 1) * len(ps)]):
                for c in o.outputs:
                    fo.write(json.dumps({"task": r["task"], "output": c.text, "finish": c.finish_reason, "ntok": len(c.token_ids), "temp": t, "rp": rp}) + "\n")
        print("GEN_DONE", fn, flush=True)
if __name__ == "__main__":
    f, n, specs = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
    if len(specs) == 1: run_one(f, n, specs[0])
    else:
        for s in specs:  # fresh process per model: vLLM does not reliably free GPU memory in-process
            subprocess.run([sys.executable, __file__, f, str(n), s], check=True)
