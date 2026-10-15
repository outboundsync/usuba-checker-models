import json,torch,sys
from transformers import AutoTokenizer,AutoModelForCausalLM
from peft import PeftModel
B="Qwen/Qwen2.5-Coder-7B-Instruct"
tok=AutoTokenizer.from_pretrained(B)
m=AutoModelForCausalLM.from_pretrained(B,torch_dtype=torch.bfloat16).cuda()
m=PeftModel.from_pretrained(m,sys.argv[1]); m.eval()
rows=[json.loads(l) for l in open("holdout.jsonl")][:12]
def nll(r):
  p=tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True);f=tok.apply_chat_template(r["messages"],tokenize=False)
  pi=tok(p,add_special_tokens=False).input_ids;ai=tok(f[len(p):],add_special_tokens=False).input_ids[:6000]
  x=torch.tensor([pi+ai]).cuda()
  with torch.no_grad(): lg=m(x).logits[0,len(pi)-1:-1].float()
  return torch.nn.functional.cross_entropy(lg,x[0,len(pi):]).item()
for name,ctx in [("tuned",None),("base",m.disable_adapter)]:
  if ctx:
    with ctx(): print(name,[round(nll(r),3) for r in rows],flush=True)
  else: print(name,[round(nll(r),3) for r in rows],flush=True)
g=json.loads(open("gen_tuned_a.jsonl").readline())["output"]
pre=g[:g.find("import Quickshell.Wayland\n")+len("import Quickshell.Wayland")]
r=rows[0];p=tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True)+pre
x=tok(p,return_tensors="pt",add_special_tokens=False).input_ids.cuda()
with torch.no_grad(): pr=m(x).logits[0,-1].float().softmax(-1)
v,i=pr.topk(8); print("tuned next",[(tok.decode([a]),round(b.item(),3)) for a,b in zip(i,v)])
with m.disable_adapter():
  with torch.no_grad(): pr=m(x).logits[0,-1].float().softmax(-1)
v,i=pr.topk(8); print("base next",[(tok.decode([a]),round(b.item(),3)) for a,b in zip(i,v)])
