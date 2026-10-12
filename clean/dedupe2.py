import json, re
R="/workspace/omarchy-specialist/"
tr=[json.loads(l) for l in open(R+"data/train.jsonl")]; ho=[json.loads(l) for l in open(R+"data/holdout.jsonl")]
def L(s): return {re.sub(r"\s+"," ",x).strip() for x in s.splitlines() if len(x.strip())>8}
def W(s,k=8):
    w=re.findall(r"\w+",s.lower()); return {" ".join(w[i:i+k]) for i in range(0,max(1,len(w)-k+1))}
TA=[L(t["messages"][2]["content"]) for t in tr]; TP=[W(t["messages"][1]["content"]) for t in tr]
res=[]
for i,h in enumerate(ho):
    a=L(h["messages"][2]["content"]); p=W(h["messages"][1]["content"])
    best=max(range(len(tr)), key=lambda j: len(a&TA[j])/max(1,min(len(a),len(TA[j]))))
    j=best; ov=len(a&TA[j])/max(1,min(len(a),len(TA[j]))); jac=len(a&TA[j])/max(1,len(a|TA[j]))
    pj=max(len(p&q)/max(1,len(p|q)) for q in TP)
    res.append(dict(holdout_i=i,task=h["task"],plugin=h["meta"]["plugin_path"],repo=h["meta"]["repo"],train_i=j,train_task=tr[j]["task"],train_repo=tr[j]["meta"]["repo"],train_plugin=tr[j]["meta"]["plugin_path"],answer_line_overlap=round(ov,3),answer_line_jaccard=round(jac,3),max_prompt_jaccard8=round(pj,3)))
json.dump(res,open("holdout_dupes_all.json","w"),indent=1)
for r in sorted(res,key=lambda r:-r["answer_line_jaccard"])[:22]: print(r["holdout_i"],r["task"][:40],r["plugin"],"<->",r["train_i"],r["train_task"][:40],r["train_plugin"],r["answer_line_jaccard"],r["answer_line_overlap"],r["max_prompt_jaccard8"])
