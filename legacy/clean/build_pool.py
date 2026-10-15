"""Turn license-OK functest-passing registry plugins into build_from_spec examples; exclude holdout dupes."""
import json, os, re, collections, hashlib, subprocess
R="/workspace/omarchy-specialist/"; src=open(R+"build_dataset.py").read()
exec(src[src.index("CAP=90000"):src.index("EX=[]")].replace("from transformers","#"))
exec(src[src.index("INSTR=["):src.index("# ---- sources")])
SEL=set(json.load(open("registry/selected_ids.json")))
rows=[r for r in (json.loads(l) for l in open("registry/scan.jsonl")) if r["id"] in SEL]
ho=[json.loads(l) for l in open(R+"data/holdout.jsonl")]
hrepos={h["meta"]["repo"].rstrip("/").lower() for h in ho}
def L(s): return {re.sub(r"\s+"," ",x).strip() for x in s.splitlines() if len(x.strip())>8}
HA=[L(h["messages"][2]["content"]) for h in ho]
HP=[h["messages"][1]["content"].lower() for h in ho]
TA=[L(json.loads(l)["messages"][2]["content"]) for l in open(R+"data/train.jsonl")]; SEEN=[]
trrepos={json.loads(l)["meta"]["repo"].rstrip("/").lower() for l in open(R+"data/train.jsonl")}
out=[];man=[];C=collections.Counter()
for r in rows:
    d="/workspace/registry_repos/"+re.sub(r"[^\w.-]","_",r["id"])
    if not (r.get("pass_") and r.get("license_ok")): continue
    why=None
    if r["repo"].rstrip("/").lower() in hrepos: why="holdout repo"
    files=bundle(d) if os.path.isdir(d) else {}
    try: m=json.loads(files["manifest.json"])
    except Exception: why=why or "no manifest"; m={}
    if not why:
        a=L(render(files)); j=max(len(a&h)/max(1,len(a|h)) for h in HA)
        if j>=0.5: why=f"near-dup of holdout answer (line jaccard {j:.2f})"
        elif any(("`"+m.get("id","")+"`") in p for p in HP): why="id appears in holdout prompt"
    if not why:
        jt=max([len(a&t)/max(1,len(a|t)) for t in TA+SEEN] or [0])
        if jt>=0.8: why="near-dup of train/pool example (line jaccard>=0.8)"
    if not why and m.get("id","").startswith("omarchy."): why="reserved id"
    code=sum(len(c) for p,c in files.items() if p!="manifest.json")
    if not why and (code<2500 or re.search(r"lorem ipsum|TODO: implement|placeholder data",render(files),re.I)): why="trivial/placeholder (<2.5k chars code or placeholder text)"
    if not why and sum(len(c) for c in files.values())>CAP: why="too large (>90k chars)"
    C[why or "kept"]+=1
    prov=f"registry plugins.omarchy.org id={r['id']} verified; repo {r['repo']} @ {r.get('head')}; license {r['license']} ({'; '.join(r['copyright'])})"
    man.append(dict(id=r["id"],repo=r["repo"],commit=r.get("head"),license=r["license"],copyright=r["copyright"],kept=not why,reason=why,already_in_train_repo=r["repo"].rstrip("/").lower() in trrepos))
    if why: continue
    SEEN.append(a)
    u=INSTR[int(hashlib.md5(r["id"].encode()).hexdigest(),16)%3].format(id=m["id"],name=m.get("name",m["id"]),kinds=", ".join(m.get("kinds",[])),desc=describe(m) if m.get("name") else m["id"])
    out.append(dict(messages=[{"role":"system","content":SYS},{"role":"user","content":u},{"role":"assistant","content":render(files)}],task="build_from_spec",
        meta=dict(origin="registry",repo=r["repo"],commit=r.get("head"),license=r["license"],plugin_path=".",kinds=m.get("kinds")),provenance=prov))
with open("pool_registry.jsonl","w") as f:
    for x in out: f.write(json.dumps(x)+"\n")
json.dump(man,open("pool_registry_manifest.json","w"),indent=1)
print(len(out),C)
