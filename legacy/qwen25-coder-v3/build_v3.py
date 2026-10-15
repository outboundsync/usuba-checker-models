"""v3 7B SFT set (2026-10-12). Input: clean/train_w2.jsonl (merged/reviewed code only: first-party omarchy + verified
registry listings, license-checked, functest-pass, no model-written answers, no fix_manifest synthetic rows, no forks).
Changes vs w2:
 - answer token cap 8192 (was 12000); see v3/README.md for the justification
 - every manifest (in answer or prompt) must have a top-level non-empty entryPoints object; nested forms are lifted
 - adds Omarchy built-in plugins (catalog sourceType=builtin, omacom/omarchy @ defbf90, MIT) that are not in the eval and
   not already in training; ids re-namespaced omarchy.* -> acme.* (reserved namespace), omarchy.clonePaths files inlined
 - global holdout dedupe: holdout plugin paths/repos, ids in holdout prompts, prompt near-dups, answer line-jaccard >= 0.5
out: v3/train_v3.jsonl, v3/train_v3_manifest.json (one provenance record per input row, kept or excluded)"""
import json, os, re, sys, hashlib, collections, subprocess
R = "/workspace/omarchy-specialist/"; sys.path[:0] = [R + "functest", R + "validator"]
from validate import KIND_EP
src = open(R + "build_dataset.py").read()
exec(src[src.index("SYS=("):src.index("def kinds_of")])
exec(src[src.index("def describe"):src.index("EX=[]")])
exec(src[src.index("INSTR=["):src.index("# ---- sources")])
from tokenizers import Tokenizer
TOK = Tokenizer.from_file(R + "runs/clean_b/tokenizer.json"); MAXTOK = 8192
ntok = lambda s: len(TOK.encode(s).ids)
def L(s): return {re.sub(r"\s+", " ", x).strip() for x in s.splitlines() if len(x.strip()) > 8}
def jac(a, b): return len(a & b) / max(1, len(a | b))
# built-ins come from the Dell's own Omarchy 4.0.4-1 tree (shell/ == basecamp/omarchy@c668141); the newer defbf90 tree used ShellIpc/UntypedInput/OverlayWindow that 4.0.4 lacks
OMC = os.environ.get("OMC", "c668141e9c42b13c80c9ca4ea108e11708c5e8a5"); OMD = os.environ.get("OMD", "/tmp/om-c668141")   # git worktree of c668141 (bundle() needs git ls-files); shell/ verified == Dell 4.0.4-1
ho = [json.loads(l) for l in open(R + "data/holdout.jsonl")]
hm = [h["meta"] if isinstance(h["meta"], dict) else eval(h["meta"]) for h in ho]
HPATH = {m["plugin_path"].rstrip("/") for m in hm if m["origin"] == "first-party"}
HREPO = {m["repo"].rstrip("/").lower() for m in hm if m["origin"] != "first-party"}
HA = [L(h["messages"][2]["content"]) for h in ho]; HP = [h["messages"][1]["content"] for h in ho]; HPL = [L(p) for p in HP]
def fix_ep(m):
    """ensure top-level entryPoints; lift nested <kind>.entryPoint(s) if present. returns (manifest, changed)"""
    if isinstance(m.get("entryPoints"), dict) and m["entryPoints"]: return m, False
    ep = {}
    for k, key in KIND_EP.items():
        sub = m.get(key) if isinstance(m.get(key), dict) else {}
        v = sub.pop("entryPoint", None) or sub.pop("entry", None)
        if v: ep[key] = v
    if isinstance(m.get("entryPoint"), str) and m.get("kinds"): ep.setdefault(KIND_EP.get(m["kinds"][0], "main"), m.pop("entryPoint"))
    m["entryPoints"] = ep; return m, True
def fix_text(text):
    n = 0
    def sub(mt):
        nonlocal n
        try: m = json.loads(mt.group(3))
        except Exception: return mt.group(0)
        m, ch = fix_ep(m)
        if not ch: return mt.group(0)
        n += 1; return mt.group(1) + mt.group(2) + "\n" + json.dumps(m, indent=2) + "\n```"
    return re.sub(r"(### \S*manifest\.json\n|```json)(\n?)(\{.*?\})\n```", lambda mt: sub(mt) if '"kinds"' in mt.group(3) else mt.group(0), text, flags=re.S), n
out, man, C = [], [], collections.Counter()
def gate(r, source):
    a = r["messages"][2]["content"]; u = r["messages"][1]["content"]; meta = r["meta"] if isinstance(r["meta"], dict) else eval(r["meta"])
    a, na = fix_text(a); u, nu = fix_text(u); r["messages"][2]["content"] = a; r["messages"][1]["content"] = u
    C["entryPoints_fixed"] += na + nu
    why = None; t = ntok(a); La = L(a); Lu = L(u)
    bad = [p for p, c in parse(a).items() if p.endswith("manifest.json") and not (lambda m: isinstance(m.get("entryPoints"), dict) and m["entryPoints"])(json.loads(c))]
    if bad: why = "manifest without entryPoints after fix"
    elif t > MAXTOK: why = f">{MAXTOK} answer tokens"
    elif meta.get("origin") == "first-party" and meta.get("plugin_path", "").rstrip("/") in HPATH: why = "holdout plugin (first-party path)"
    elif meta.get("origin") != "first-party" and meta.get("repo", "").rstrip("/").lower() in HREPO: why = "holdout repo"
    elif any(p.strip() == u.strip() for p in HP): why = "exact holdout prompt"
    elif max(jac(Lu, h) for h in HPL) >= 0.8 and max(jac(La, h) for h in HA) >= 0.3: why = "near-dup holdout prompt"
    elif max(jac(La, h) for h in HA) >= 0.5: why = "near-dup holdout answer"
    C[(source, r["task"].split(":")[0], why or "kept")] += 1
    man.append(dict(source=source, task=r["task"], provenance=r["provenance"], repo=meta.get("repo"), commit=meta.get("commit"),
                    license=meta.get("license"), plugin_path=meta.get("plugin_path"), answer_tokens=t, entrypoints_fixed=na + nu, excluded=why))
    if not why: out.append(r)
for l in open(R + "clean/train_w2.jsonl"): gate(json.loads(l), "train_w2")
# ---- Omarchy built-ins
have = {(m["meta"] if isinstance(m["meta"], dict) else eval(m["meta"])).get("plugin_path", "").rstrip("/") for m in out if m["task"] == "build_from_spec"}
cat = [v for v in json.load(open(R + "clean/registry/catalog_live.json")).values() if isinstance(v, list)][0]
lic = open(OMD + "/LICENSE").read(); assert lic.startswith("MIT") or "Permission is hereby granted, free of charge" in lic
BI = []
for x in cat:
    if not x.get("builtIn"): continue
    mp = x["manifestPath"]; d = os.path.dirname(mp)
    if not os.path.exists(os.path.join(OMD, mp)): C[("omarchy_builtin", "not in the 4.0.4 tree")] += 1; continue
    if mp.endswith("/manifest.json"):
        pp = d; files = bundle(os.path.join(OMD, d))
    else:  # shared-folder bar widget: <Name>.manifest.json + entry + clonePaths
        m0 = json.load(open(os.path.join(OMD, mp))); pp = mp[:-len(".manifest.json")]
        files = {"manifest.json": open(os.path.join(OMD, mp)).read()}
        for v in m0["entryPoints"].values(): files[v] = open(os.path.join(OMD, d, v)).read()
        for cp in (m0.get("omarchy") or {}).get("clonePaths", []):
            s = os.path.normpath(os.path.join(OMD, d, cp["source"]))
            if os.path.isdir(s):
                for f in sorted(os.listdir(s)):
                    if f.endswith(EXT): files[cp["target"] + "/" + f] = open(os.path.join(s, f)).read()
            else: files[cp["target"]] = open(s).read()
    m = json.loads(files["manifest.json"])
    if m["id"].startswith("omarchy."): m["id"] = "acme." + m["id"].split(".", 1)[1]
    if isinstance(m.get("omarchy"), dict):
        m["omarchy"].pop("clonePaths", None)
        if not m["omarchy"]: m.pop("omarchy")
    m, _ = fix_ep(m); files["manifest.json"] = json.dumps(m, indent=2) + "\n"
    rec = dict(source="omarchy_builtin", task="build_from_spec", repo="https://github.com/basecamp/omarchy", commit=OMC, license="MIT",
               plugin_path=pp, provenance=f"first-party built-in plugin {x['id']} (plugins.omarchy.org sourceType=builtin); basecamp/omarchy @ {OMC[:7]} (= Omarchy 4.0.4-1 package on the Dell) {mp}; MIT, Copyright (c) David Heinemeier Hansson; id re-namespaced to {m['id']}")
    why = None
    if pp in HPATH or d in HPATH: why = "holdout plugin (first-party path)"
    elif pp in have: why = "already in training (9480d1b snapshot)"
    elif m.get("id") in {"acme.dev-gallery"}: why = "dev-only"
    if why:
        man.append(dict(rec, excluded=why)); C[("omarchy_builtin", why)] += 1; continue
    BI.append((x, m, files, rec))
# functest each new builtin as a standalone plugin
import functest
def ft(item):
    x, m, files, rec = item
    try: r = functest.test(files=files)
    except Exception as e: r = {"pass": False, "categories": [f"error {e}"]}
    return item, r
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(6) as ex: res = list(ex.map(ft, BI))
for (x, m, files, rec), r in res:
    a = render(files); t = ntok(a)
    meta = dict(origin="first-party", repo=rec["repo"], commit=OMC, license="MIT", plugin_path=rec["plugin_path"], kinds=m.get("kinds"), builtin=True)
    why = None if r.get("pass") else "functest fail: " + ",".join(map(str, r.get("categories", [])))[:200]
    if not why and t > MAXTOK: why = f">{MAXTOK} answer tokens"
    if not why and max(jac(L(a), h) for h in HA) >= 0.5: why = "near-dup holdout answer"
    man.append(dict(rec, answer_tokens=t, functest=bool(r.get("pass")), excluded=why)); C[("omarchy_builtin", why or "kept")] += 1
    if why: continue
    for i in range(2):  # two phrasings, as for first-party in v2
        u = INSTR[(int(hashlib.md5(m["id"].encode()).hexdigest(), 16) + i) % 3].format(id=m["id"], name=m.get("name", m["id"]), kinds=", ".join(m["kinds"]), desc=describe(m))
        out.append(dict(messages=[{"role": "system", "content": SYS}, {"role": "user", "content": u}, {"role": "assistant", "content": a}], task="build_from_spec", meta=meta, provenance=rec["provenance"]))
os.chdir(R + "v3")
with open("train_v3.jsonl", "w") as f:
    for x in out: f.write(json.dumps(x) + "\n")
json.dump(man, open("train_v3_manifest.json", "w"), indent=1)
for k, v in sorted(C.items(), key=str): print(k, v)
T = sorted(ntok(r["messages"][2]["content"]) for r in out)
print("TOTAL", len(out), collections.Counter(r["task"].split(":")[0] for r in out), "answer tok p50", T[len(T)//2], "p95", T[int(.95*len(T))], "max", T[-1])
