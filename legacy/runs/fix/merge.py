import torch,sys
from transformers import AutoTokenizer,AutoModelForCausalLM
from peft import PeftModel
B="Qwen/Qwen2.5-Coder-7B-Instruct"
m=AutoModelForCausalLM.from_pretrained(B,torch_dtype=torch.bfloat16)
m=PeftModel.from_pretrained(m,sys.argv[1]).merge_and_unload()
m.save_pretrained(sys.argv[2],safe_serialization=True); AutoTokenizer.from_pretrained(B).save_pretrained(sys.argv[2]); print("MERGED")
