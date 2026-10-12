"""Chunk the large (>90k chars) curated registry plugins that pass functest, exactly like build_dataset.chunk_tasks (community limits)."""
import json, os, re, collections, subprocess, hashlib, sys
PERM={"MIT","Apache-2.0","BSD-2-Clause","BSD-3-Clause","ISC","MPL-2.0"}
R="/workspace/omarchy-specialist/"; sys.path.insert(0,R+"validator")
from validate import KIND_EP
src=open(R+"build_dataset.py").read()
exec(src[src.index("CAP=90000"):src.index("INSTR=[")].replace("from transformers","#"))
scan={json.loads(l)["id"]:json.loads(l) for l in open("registry/scan.jsonl")}
big=[m for m in json.load(open("pool_registry_manifest.json")) if m["reason"]=="too large (>90k chars)"]
ho=[json.loads(l) for l in open(R+"data/holdout.jsonl")]
hrepos={h["meta"]["repo"].rstrip("/").lower() for h in ho}
def L(s): return {re.sub(r"\s+"," ",x).strip() for x in s.splitlines() if len(x.strip())>8}
HA=[L(h["messages"][2]["content"]) for h in ho]
man=[]; rows=[]; C=collections.Counter()
for b in big:
    r=scan[b["id"]]; d="/workspace/registry_repos/"+re.sub(r"[^\w.-]","_",b["id"])
    why=None
    if not (r.get("license_ok") and r["license"] in PERM): why=f"license {r.get('license')}"
    elif r["repo"].rstrip("/").lower() in hrepos: why="holdout repo"
    files=bundle(d) if not why else {}
    try: m=json.loads(files["manifest.json"]) if not why else None
    except Exception: why="no manifest"
    if not why and not isinstance(m.get("entryPoints"),dict): why="no entryPoints"
    EX.clear()
    if not why:
        prov=f"registry plugins.omarchy.org id={r['id']} verified; repo {r['repo']} @ {r.get('head')}; license {r['license']} ({'; '.join(r['copyright'])})"
        meta=dict(origin="registry",repo=r["repo"],commit=r.get("head"),license=r["license"],plugin_path=".",kinds=m.get("kinds"),group=hashlib.md5(r["repo"].encode()).hexdigest()[:8])
        try: chunk_tasks(dict(origin="community"),m,files,meta)
        except Exception as e: why="chunk error "+repr(e)[:80]
    kept=0
    for e in EX if not why else []:
        ans=render(e["files"]); a=L(ans)
        if len(ans)+len(e["user"])>MAXEX: C["row too long"]+=1; continue
        j=max(len(a&h)/max(1,min(len(a),len(h))) for h in HA)
        if j>=0.5: C["holdout overlap"]+=1; continue
        rows.append(dict(messages=[{"role":"system","content":SYS},{"role":"user","content":e["user"]},{"role":"assistant","content":ans}],task=e["task"],meta=e["meta"],provenance=prov)); kept+=1
    C[why or "plugin ok"]+=1
    man.append(dict(id=b["id"],repo=r["repo"],commit=r.get("head"),license=r.get("license"),copyright=r.get("copyright"),excluded=why,rows=kept))
with open("pool_chunked.jsonl","w") as f:
    for x in rows: f.write(json.dumps(x)+"\n")
json.dump(man,open("pool_chunked_manifest.json","w"),indent=1)
print(len(big),"plugins",len(rows),"rows",C,collections.Counter(x["task"].split(":")[0] for x in rows))
