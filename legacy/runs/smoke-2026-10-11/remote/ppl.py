from unsloth import FastLanguageModel
import json,torch,sys
m,tok=FastLanguageModel.from_pretrained(sys.argv[1],max_seq_length=24576,load_in_4bit=True)
FastLanguageModel.for_inference(m)
rows=[json.loads(l) for l in open("holdout.jsonl")][:12]
def loss(model):
  L=[]
  for r in rows:
    p=tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True); full=tok.apply_chat_template(r["messages"],tokenize=False)
    pi=tok(p,add_special_tokens=False).input_ids; fi=tok(full,add_special_tokens=False,return_tensors="pt").input_ids.cuda()
    lab=fi.clone(); lab[:,:len(pi)]=-100
    with torch.no_grad(): L.append(model(input_ids=fi,labels=lab).loss.item())
  return sum(L)/len(L)
print("TUNED",loss(m),flush=True)
with m.disable_adapter(): print("BASE",loss(m),flush=True)
