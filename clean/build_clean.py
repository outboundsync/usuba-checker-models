import json, collections
R="/workspace/omarchy-specialist/"
tr=[json.loads(l) for l in open(R+"data/train.jsonl")]; ho=[json.loads(l) for l in open(R+"data/holdout.jsonl")]
sc=json.load(open("score_train.json"))
cat={p["repo"].rstrip("/").lower():p for p in json.load(open("registry/catalog_live.json"))["plugins"]}
dup=[d for d in json.load(open("holdout_dupes_all.json")) if d["answer_line_jaccard"]>=0.7]
dupH={d["holdout_i"] for d in dup}
FP="first-party: basecamp/omarchy (now omacom/omarchy) commit 9480d1b = merge commit of PR #15065 on main"
keep=[];man=[];C=collections.Counter()
for i,(x,s) in enumerate(zip(tr,sc)):
    m=x["meta"]; t=x["task"].split(":")[0]; p=cat.get(m["repo"].rstrip("/").lower())
    if m["origin"]=="first-party": prov,pok=FP,True
    elif p and p.get("verificationStatus")=="verified": prov,pok=f"registry plugins.omarchy.org id={p['id']} verified ({p.get('verificationCoverage')}), listed {p.get('addedAt')}, listingValidatedCommit={p.get('listingValidatedCommit')}",True
    elif p: prov,pok=f"registry id={p['id']} UNVERIFIED",False
    else: prov,pok="not in registry",False
    synth = t=="fix_manifest"
    reason=[]
    if not s["pass_"]: reason.append("functest-fail")
    if not pok: reason.append("provenance")
    if synth: reason.append("synthetic-prompt(fix_manifest corruption)")
    C[(s["pass_"],pok,synth)]+=1
    man.append(dict(train_i=i,task=x["task"],origin=m["origin"],repo=m["repo"],commit=m["commit"],plugin_path=m["plugin_path"],license=m["license"],provenance=prov,functest_pass=s["pass_"],functest_categories=s["categories"],kept=not reason,drop_reasons=reason))
    if not reason: keep.append(dict(x,provenance=prov))
with open("train_clean.jsonl","w") as f:
    for k in keep: f.write(json.dumps(k)+"\n")
json.dump(man,open("train_clean_manifest.json","w"),indent=1)
with open("holdout_clean.jsonl","w") as f:
    for i,h in enumerate(ho):
        if i not in dupH: f.write(json.dumps(dict(h,holdout_i=i))+"\n")
json.dump(dict(threshold="answer line-set jaccard >= 0.7",removed=sorted(dupH),pairs=dup),open("holdout_dupes.json","w"),indent=1)
print("kept",len(keep),"holdout clean",56-len(dupH),C)
print(collections.Counter(c for s in sc if not s["pass_"] for c in s["categories"]).most_common())
print(collections.Counter((m["origin"],m["task"].split(":")[0]) for m in man if not m["functest_pass"]).most_common())
print(collections.Counter(tuple(m["drop_reasons"]) for m in man))
