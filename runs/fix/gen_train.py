import json
from vllm import LLM,SamplingParams
def main():
  rows=[json.loads(l) for l in open("train.jsonl")]
  llm=LLM("Qwen/Qwen2.5-Coder-7B-Instruct",max_model_len=32768,gpu_memory_utilization=0.9)
  tok=llm.get_tokenizer()
  ps=[tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True) for r in rows]
  outs=llm.generate(ps,SamplingParams(temperature=0.7,top_p=0.9,n=6,max_tokens=12000,seed=0))
  with open("gen_train_samples.jsonl","w") as f:
    for o in outs: f.write(json.dumps([{"output":c.text,"finish":c.finish_reason} for c in o.outputs])+"\n")
  print("GEN_DONE",flush=True)
if __name__=="__main__": main()
