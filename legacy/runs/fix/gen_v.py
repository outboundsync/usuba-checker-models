import json,sys
from vllm import LLM,SamplingParams
from vllm.lora.request import LoRARequest
def main():
  # usage: gen_v.py file.jsonl n name:adapter_dir [name:adapter_dir ...]  (adapter 'none' = stock)
  rows=[json.loads(l) for l in open(sys.argv[1])][:int(sys.argv[2])]
  llm=LLM("Qwen/Qwen2.5-Coder-7B-Instruct",max_model_len=32768,enable_lora=True,max_lora_rank=16,gpu_memory_utilization=0.9)
  tok=llm.get_tokenizer()
  ps=[tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True) for r in rows]
  sp=SamplingParams(temperature=0,max_tokens=16000)
  for k,spec in enumerate(sys.argv[3:]):
    name,ad=spec.split(":")
    outs=llm.generate(ps,sp,lora_request=None if ad=="none" else LoRARequest(name,k+1,ad))
    with open(f"gen_{name}.jsonl","w") as f:
      for r,o in zip(rows,outs): f.write(json.dumps({"task":r["task"],"output":o.outputs[0].text,"finish":o.outputs[0].finish_reason})+"\n")
    print("GEN_DONE",name,flush=True)
if __name__=="__main__": main()
