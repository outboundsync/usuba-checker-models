import json,torch,sys
from transformers import AutoTokenizer,AutoModelForCausalLM
from peft import PeftModel
B="Qwen/Qwen2.5-Coder-7B-Instruct"
tok=AutoTokenizer.from_pretrained(B)
m=AutoModelForCausalLM.from_pretrained(B,torch_dtype=torch.bfloat16).cuda()
m=PeftModel.from_pretrained(m,sys.argv[1]); m.eval()
r=[json.loads(l) for l in open("holdout.jsonl")][0]
p=tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True)
x=tok(p,return_tensors="pt",add_special_tokens=False).to("cuda")
g=m.generate(**x,max_new_tokens=int(sys.argv[2]),do_sample=False)
print("OUT>>",tok.decode(g[0][x.input_ids.shape[1]:])[-1500:])
