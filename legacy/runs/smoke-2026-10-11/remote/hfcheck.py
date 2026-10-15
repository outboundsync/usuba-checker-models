from unsloth import FastLanguageModel
import json
m,tok=FastLanguageModel.from_pretrained("adapter",max_seq_length=24576,load_in_4bit=True)
FastLanguageModel.for_inference(m)
rows=[json.loads(l) for l in open("holdout.jsonl")]
out=[]
for i in [0,1,2]:
  ids=tok.apply_chat_template(rows[i]["messages"][:-1],add_generation_prompt=True,return_tensors="pt").to("cuda")
  g=m.generate(input_ids=ids,max_new_tokens=6000,do_sample=False)
  t=tok.decode(g[0][ids.shape[1]:],skip_special_tokens=True); out.append({"i":i,"output":t,"ntok":int(g.shape[1]-ids.shape[1])}); print("HF",i,out[-1]["ntok"],flush=True)
json.dump(out,open("hfcheck.json","w"),indent=1)
