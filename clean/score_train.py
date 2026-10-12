#!/usr/bin/env python3
"""Run each training example's assistant answer through functest.
Full tasks: answer files = plugin. Tree tasks: answer overlaid on the upstream tree (rescore.build_tree);
failures already present in the PRISTINE upstream tree are subtracted (abs result also kept)."""
import json, os, sys, hashlib
from concurrent.futures import ThreadPoolExecutor
ROOT = "/workspace/omarchy-specialist"; sys.path[:0] = [ROOT + "/functest", ROOT + "/validator"]
import rescore, functest
from build_parse import parse
def tree_dir(h):
    m = h["meta"]
    if m["origin"] == "house": return "/workspace/" + m["repo"].rstrip("/").split("/")[-1] + ("" if m["plugin_path"] in (".", "") else "/" + m["plugin_path"])
    return ("/opt/ft/omarchy/" if m["origin"] == "first-party" else ROOT + "/sources/repos/") + m["plugin_path"]
rescore.tree_dir = tree_dir
def cached(files):
    cp = os.path.join(rescore.CACHE, hashlib.sha1(json.dumps(files, sort_keys=True).encode()).hexdigest() + ".json")
    if os.path.exists(cp): return json.load(open(cp))
    r = functest.test(files=files); json.dump(r, open(cp, "w")); return r
_pr = {}
def pristine(h):
    d = tree_dir(h)
    if d not in _pr:
        r = cached(functest.read_dir(d))
        _pr[d] = ({tuple(x) for x in r["static_fails"]}, {rescore.norm(e) for e in (r["runtime"] or {}).get("errors", [])})
    return _pr[d]
def one(a):
    i, h = a; task = h["task"].split(":")[0]
    files = parse(h["messages"][2]["content"])
    if not files: return dict(i=i, task=h["task"], pass_=False, abs_pass=False, categories=["no-files-parsed"])
    if task in rescore.FULL:
        r = cached(files); ab = r["pass"]
    else:
        _, t = rescore.build_tree(h, files); r = json.loads(json.dumps(cached(t))); ab = r["pass"]
        bs, br = pristine(h)
        r["static_fails"] = [x for x in r["static_fails"] if tuple(x) not in bs]
        if r["runtime"]:
            r["runtime"]["errors"] = [e for e in r["runtime"]["errors"] if rescore.norm(e) not in br]
            r["runtime"]["pass"] = not r["runtime"]["errors"]
        r["categories"] = functest.categories(r["static_fails"], r["runtime"])
        r["pass"] = not r["static_fails"] and (r["runtime"] is None or r["runtime"]["pass"])
    rt = r.get("runtime") or {}
    return dict(i=i, task=h["task"], pass_=bool(r["pass"]), abs_pass=bool(ab), categories=r["categories"],
                static_fails=[f"{a}: {b}"[:200] for a, b in r["static_fails"]][:6], runtime_errors=[e[:200] for e in rt.get("errors", [])][:6])
if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    rows = [json.loads(l) for l in open(src)]
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(one, enumerate(rows)))
    json.dump(res, open(out, "w"), indent=1)
    print(src, sum(r["pass_"] for r in res), "/", len(res), "abs", sum(r["abs_pass"] for r in res))
