from unsloth import FastLanguageModel
import json,sys,time
ad=sys.argv[1]; out=sys.argv[2]
m,tok=FastLanguageModel.from_pretrained(ad,max_seq_length=32768,load_in_4bit=True)
FastLanguageModel.for_inference(m)
rows=[json.loads(l) for l in open("holdout.jsonl")]
idx=[i for i,r in enumerate(rows) if r["task"]=="build_from_spec"][:3]
res=[]
for i in idx:
  ids=tok.apply_chat_template(rows[i]["messages"][:-1],add_generation_prompt=True,return_tensors="pt").to("cuda")
  t0=time.time(); g=m.generate(input_ids=ids,max_new_tokens=8000,do_sample=False,eos_token_id=151645)
  o=g[0][ids.shape[1]:]; res.append({"i":i,"task":"build_from_spec","ntok":len(o),"finish":"stop" if 151645 in o.tolist() else "length","output":tok.decode(o,skip_special_tokens=True)})
  print("HF",i,len(o),res[-1]["finish"],round(time.time()-t0),flush=True)
  json.dump(res,open(out,"w"),indent=1)
