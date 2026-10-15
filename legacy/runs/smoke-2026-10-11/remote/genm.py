import json,sys
from vllm import LLM,SamplingParams
from vllm.lora.request import LoRARequest
def main():
  rows=[json.loads(l) for l in open("holdout.jsonl")]
  llm=LLM(sys.argv[1],max_model_len=32768,gpu_memory_utilization=0.9)
  tok=llm.get_tokenizer()
  ps=[tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True) for r in rows]
  outs=llm.generate(ps,SamplingParams(temperature=0,max_tokens=16000,stop_token_ids=[151645,151643]))
  with open("gen_"+sys.argv[2]+".jsonl","w") as f:
    for r,o in zip(rows,outs): f.write(json.dumps({"task":r["task"],"output":o.outputs[0].text,"finish":o.outputs[0].finish_reason})+"\n")
  print("GEN_DONE",flush=True)
if __name__=="__main__": main()
