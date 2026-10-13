# one vLLM load: greedy 49 holdout (16k) + best-of-16 on 32 full-plugin prompts (T0.8 rp1.05 top_p .95, 16k). no-think template.
import json,os,sys
from vllm import LLM,SamplingParams
def main():
  M=sys.argv[1]
  NH,NP=int(os.environ.get("NH",49)),int(os.environ.get("NP",32)); H=[json.loads(l) for l in open("holdout_clean.jsonl")][:NH]; P=[json.loads(l) for l in open("probe_bfs32.jsonl")][:NP]
  llm=LLM(M,max_model_len=24576,gpu_memory_utilization=float(os.environ.get("GMU",0.88)),max_num_seqs=int(os.environ.get("MAXSEQS",128)),enable_prefix_caching=os.environ.get("PC","0")=="1",seed=0,enforce_eager=os.environ.get("EAGER","1")=="1",limit_mm_per_prompt={"image":0,"video":0})
  tok=llm.get_tokenizer()
  pr=lambda r: tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True,enable_thinking=False)
  print("PROMPT_TAIL",repr(pr(H[0])[-60:]),flush=True)
  g=SamplingParams(temperature=0,max_tokens=int(os.environ.get("MT",16000)),repetition_penalty=1.05)
  b=SamplingParams(temperature=0.8,top_p=0.95,max_tokens=int(os.environ.get("MT",16000)),repetition_penalty=1.05,n=16,seed=0)
  outs=llm.generate([pr(r) for r in H]+[pr(r) for r in P],[g]*len(H)+[b]*len(P))
  for fn,rows,oo,t in [("gen_q27.jsonl",H,outs[:NH],0),("gen_bo16q27_t0.8_rp1.05_n16.jsonl",P,outs[NH:],0.8)]:
    with open(fn,"w") as fo:
      for r,o in zip(rows,oo):
        for c in o.outputs: fo.write(json.dumps({"task":r["task"],"output":c.text,"finish":c.finish_reason,"ntok":len(c.token_ids),"temp":t,"rp":1.05})+"\n")
    print("GEN_DONE",fn,flush=True)
if __name__=="__main__": main()
