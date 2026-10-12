import json,sys
from vllm import LLM,SamplingParams
from vllm.lora.request import LoRARequest
def main():
  ad,name=sys.argv[1],sys.argv[2]
  rows=[json.loads(l) for l in open("holdout.jsonl")]
  llm=LLM("Qwen/Qwen2.5-Coder-7B-Instruct",max_model_len=32768,enable_lora=True,max_lora_rank=16,gpu_memory_utilization=0.75)
  tok=llm.get_tokenizer()
  ps=[tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True) for r in rows]
  outs=llm.generate(ps,SamplingParams(temperature=0,max_tokens=16000,stop_token_ids=[151645,151643]),lora_request=LoRARequest("a",1,ad))
  with open(f"gen_{name}.jsonl","w") as f:
    for r,o in zip(rows,outs): f.write(json.dumps({"task":r["task"],"output":o.outputs[0].text,"finish":o.outputs[0].finish_reason})+"\n")
  print("GEN_DONE",flush=True)
if __name__=="__main__": main()
