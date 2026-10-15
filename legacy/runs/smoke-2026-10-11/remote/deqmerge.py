import torch,sys,bitsandbytes as bnb
from transformers import AutoModelForCausalLM,AutoTokenizer
from peft import PeftModel
ads=sys.argv[1:]
q=AutoModelForCausalLM.from_pretrained("unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",device_map="cuda",torch_dtype=torch.bfloat16)
deq={}
for n,mod in q.named_modules():
  if isinstance(mod,bnb.nn.Linear4bit):
    deq[n+".weight"]=bnb.functional.dequantize_4bit(mod.weight.data,mod.weight.quant_state).to(torch.bfloat16).cpu()
print("dequantized",len(deq),flush=True); del q; torch.cuda.empty_cache()
tok=AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-7B-Instruct")
def base():
  b=AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-Coder-7B-Instruct",torch_dtype=torch.bfloat16)
  sd=b.state_dict(); miss=0
  for k,v in deq.items():
    assert sd[k].shape==v.shape,k; sd[k].copy_(v)
  return b
b=base(); b.save_pretrained("deq_stock"); tok.save_pretrained("deq_stock"); print("SAVED deq_stock",flush=True)
for ad in ads:
  b=base(); pm=PeftModel.from_pretrained(b,ad); mm=pm.merge_and_unload(); mm.save_pretrained("deq_"+ad); tok.save_pretrained("deq_"+ad); print("SAVED","deq_"+ad,flush=True)
