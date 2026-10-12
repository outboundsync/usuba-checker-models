import json, re, difflib
R="/workspace/omarchy-specialist/"
tr=[json.loads(l) for l in open(R+"data/train.jsonl")]; ho=[json.loads(l) for l in open(R+"data/holdout.jsonl")]
def toks(s): return set(re.findall(r"\w+", s.lower()))
def sh(s,k=5):
    w=re.findall(r"\w+", s.lower()); return {" ".join(w[i:i+k]) for i in range(max(1,len(w)-k+1))}
T=[(sh(t["messages"][1]["content"]), t) for t in tr]
out=[]
for i,h in enumerate(ho):
    p=h["messages"][1]["content"]; s=sh(p); best=(-1,0)
    for j,(ts,t) in enumerate(T):
        jac=len(s&ts)/max(1,len(s|ts))
        if jac>best[0]: best=(jac,j)
    j=best[1]; t=tr[j]
    same_plugin = h["meta"]["repo"]==t["meta"]["repo"] and h["meta"].get("plugin_path")==t["meta"].get("plugin_path")
    out.append(dict(holdout_i=i, task=h["task"], best_train_i=j, train_task=t["task"], shingle_jaccard=round(best[0],3), same_plugin=same_plugin,
        exact=p.strip()==t["messages"][1]["content"].strip(), plugin=h["meta"].get("plugin_path")))
json.dump(out, open("holdout_dupes_all.json","w"), indent=1)
for o in sorted(out,key=lambda o:-o["shingle_jaccard"])[:20]: print(o)
