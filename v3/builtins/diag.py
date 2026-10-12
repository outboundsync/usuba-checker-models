"""Diagnose Omarchy built-in plugins under the functest: build each as an installable plugin (same as build_v3.py) and dump failures."""
import json, os, sys, re
R = "/workspace/omarchy-specialist/"; sys.path[:0] = [R + "functest", R + "validator"]
import functest
src = open(R + "build_dataset.py").read(); exec(src[src.index("SYS=("):src.index("def kinds_of")])
OMD = os.environ.get("OMD", "/opt/ft/omarchy")
cat = [v for v in json.load(open(R + "clean/registry/catalog_live.json")).values() if isinstance(v, list)][0]
def build(x):
    mp = x["manifestPath"]; d = os.path.dirname(mp)
    if mp.endswith("/manifest.json"): files = {}; base = os.path.join(OMD, d)
    for root, _, fs in (os.walk(os.path.join(OMD, d)) if mp.endswith("/manifest.json") else []):
        for f in fs:
            p = os.path.relpath(os.path.join(root, f), base)
            if p.endswith(EXT) and (p == "manifest.json" or not p.endswith("manifest.json")): files[p] = open(os.path.join(root, f)).read()
    if not mp.endswith("/manifest.json"):
        m0 = json.load(open(os.path.join(OMD, mp))); files = {"manifest.json": open(os.path.join(OMD, mp)).read()}
        for v in m0["entryPoints"].values(): files[v] = open(os.path.join(OMD, d, v)).read()
        for cp in (m0.get("omarchy") or {}).get("clonePaths", []):
            s = os.path.normpath(os.path.join(OMD, d, cp["source"]))
            if os.path.isdir(s):
                for f in sorted(os.listdir(s)):
                    if f.endswith(EXT): files[cp["target"] + "/" + f] = open(os.path.join(s, f)).read()
            else: files[cp["target"]] = open(s).read()
    m = json.loads(files["manifest.json"]); m["id"] = "acme." + m["id"].split(".", 1)[1]
    if isinstance(m.get("omarchy"), dict):
        m["omarchy"].pop("clonePaths", None)
        if not m["omarchy"]: m.pop("omarchy")
    files["manifest.json"] = json.dumps(m, indent=2); return files
if __name__ == "__main__":
    only = sys.argv[1:]
    out = {}
    for x in cat:
        if not x.get("builtIn") or (only and x["id"] not in only): continue
        try: f = build(x)
        except (KeyError, FileNotFoundError) as e: out[x["id"]] = dict(missing=str(e)); print(x["id"], "MISSING in tree", flush=True); continue
        r = functest.test(files=f)
        rt = r.get("runtime") or {}
        out[x["id"]] = dict(pass_=r["pass"], cats=r["categories"], static=r["static_fails"], rt=rt.get("errors", []), soft=rt.get("soft", [])[:5])
        print(x["id"], r["pass"], r["categories"], flush=True)
    json.dump(out, open(R + "v3/builtins/diag_" + os.environ.get("TAG", "base") + ".json", "w"), indent=1)
