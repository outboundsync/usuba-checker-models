import json
from vllm import LLM,SamplingParams
from vllm.lora.request import LoRARequest
def main():
  rows=[json.loads(l) for l in open("holdout.jsonl")]
  llm=LLM("unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",quantization="bitsandbytes",max_model_len=32768,enable_lora=True,max_lora_rank=16,gpu_memory_utilization=0.9)
  tok=llm.get_tokenizer()
  ps=[tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True) for r in rows]
  for name,sp,lr in [("tuned4bit",SamplingParams(temperature=0,max_tokens=16000),LoRARequest("a",1,"adapter")),("stock4bit",SamplingParams(temperature=0,max_tokens=16000),None)]:
    outs=llm.generate(ps,sp,lora_request=lr)
    with open(f"gen_{name}.jsonl","w") as f:
      for r,o in zip(rows,outs): f.write(json.dumps({"task":r["task"],"output":o.outputs[0].text,"finish":o.outputs[0].finish_reason})+"\n")
    print("GEN_DONE",name,flush=True)
if __name__=="__main__": main()
