import json, re, hashlib, collections
def L(s): return frozenset(re.sub(r"\s+"," ",x).strip() for x in s.splitlines() if len(x.strip())>8)
src=[("train_clean",l) for l in open("train_clean.jsonl")]+[("pool_registry",l) for l in open("pool_registry.jsonl")]+[("pool_chunked",l) for l in open("pool_chunked.jsonl")]
seen=set(); kept=[]; man=[]; C=collections.Counter(); by_task=collections.defaultdict(list)
for s,l in src:
    x=json.loads(l); u=x["messages"][1]["content"]; a=x["messages"][2]["content"]
    k=hashlib.sha1((u+"\0"+a).encode()).hexdigest()
    why=None
    if k in seen: why="exact dup"
    else:
        A=L(a); t=x["task"].split(":")[0]
        for B in by_task[t]:
            if len(A)>20 and len(A&B)/max(1,len(A|B))>=0.9: why="near-dup answer (>=0.9, same task type)"; break
    C[(s,why or "kept")]+=1
    m=x["meta"]; man.append(dict(n=len(kept) if not why else None,source_file=s,task=x["task"],origin=m["origin"],repo=m["repo"],commit=m["commit"],license=m["license"],plugin_path=m.get("plugin_path"),kinds=m.get("kinds"),provenance=x["provenance"],excluded=why))
    if why: continue
    seen.add(k); by_task[x["task"].split(":")[0]].append(A); kept.append(x)
with open("train_final.jsonl","w") as f:
    for x in kept: f.write(json.dumps(x)+"\n")
json.dump(man,open("train_final_manifest.json","w"),indent=1)
print(len(kept),C)
kc=collections.Counter(); 
for x in kept:
    for k in (x["meta"].get("kinds") or []): kc[k]+=1
print("kinds (row may have several):",kc); print(collections.Counter(x["task"].split(":")[0] for x in kept)); print(collections.Counter(x["meta"]["origin"] for x in kept))
print("chars total",sum(len(json.dumps(x["messages"])) for x in kept), "max", max(len(json.dumps(x["messages"])) for x in kept))
