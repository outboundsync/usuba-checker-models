import json,torch,sys,time
from transformers import AutoTokenizer,AutoModelForCausalLM
def main():
  path,out=sys.argv[1],sys.argv[2]; B=int(sys.argv[3]) if len(sys.argv)>3 else 14
  tok=AutoTokenizer.from_pretrained(path); tok.padding_side="left"
  m=AutoModelForCausalLM.from_pretrained(path,torch_dtype=torch.bfloat16,attn_implementation="sdpa").cuda().eval()
  rows=[json.loads(l) for l in open("holdout.jsonl")]
  ps=[tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True) for r in rows]
  eos=tok.convert_tokens_to_ids("<|im_end|>"); order=sorted(range(len(ps)),key=lambda i:len(ps[i])); res={}
  for b in range(0,len(order),B):
    idx=order[b:b+B]; enc=tok([ps[i] for i in idx],return_tensors="pt",padding=True,add_special_tokens=False).to("cuda")
    with torch.no_grad(): g=m.generate(**enc,max_new_tokens=16000,do_sample=False,eos_token_id=eos,pad_token_id=tok.pad_token_id)
    for j,i in enumerate(idx):
      o=g[j][enc.input_ids.shape[1]:].tolist()
      res[i]={"task":rows[i]["task"],"output":tok.decode(o,skip_special_tokens=True),"finish":"stop" if eos in o else "length"}
    print("BATCH",b,time.strftime("%T"),flush=True)
  open(out,"w").write("".join(json.dumps(res[i])+"\n" for i in range(len(rows)))); print("GEN_DONE")
if __name__=="__main__": main()
