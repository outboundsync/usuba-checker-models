# phase stock: train samples (T0.7 n6, as gen_train.py) + holdout greedy (as gen_v.py). phase tuned: holdout greedy from merged dir
import json,sys
from vllm import LLM,SamplingParams
def main():
  ph,model=sys.argv[1],sys.argv[2]
  llm=LLM(model,max_model_len=32768,gpu_memory_utilization=0.9)
  tok=llm.get_tokenizer()
  P=lambda rows:[tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True) for r in rows]
  H=[json.loads(l) for l in open("holdout.jsonl")]
  outs=llm.generate(P(H),SamplingParams(temperature=0,max_tokens=16000))
  with open(f"gen_{ph}14b.jsonl","w") as f:
    for r,o in zip(H,outs): f.write(json.dumps({"task":r["task"],"output":o.outputs[0].text,"finish":o.outputs[0].finish_reason})+"\n")
  print("GEN_DONE",ph,flush=True)
  if ph=="stock":
    T=[json.loads(l) for l in open("train.jsonl")]
    outs=llm.generate(P(T),SamplingParams(temperature=0.7,top_p=0.9,n=6,max_tokens=12000,seed=0))
    with open("gen_train_samples14b.jsonl","w") as f:
      for o in outs: f.write(json.dumps([{"output":c.text,"finish":c.finish_reason} for c in o.outputs])+"\n")
    print("TRAIN_GEN_DONE",flush=True)
if __name__=="__main__": main()
