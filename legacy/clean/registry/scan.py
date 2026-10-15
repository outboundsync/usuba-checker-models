#!/usr/bin/env python3
"""Clone every verified registry plugin at its listing-validated commit, classify license, run functest. Resumable."""
import json, os, re, sys, subprocess, shutil, time
from concurrent.futures import ThreadPoolExecutor
R="/workspace/omarchy-specialist"; sys.path[:0]=[R+"/functest", R]
import functest
src=open(R+"/tools_analyze.py").read(); exec(src[src.index("def lic_text"):src.index("rows=[]")])
H=os.path.dirname(os.path.abspath(__file__)); REPOS="/workspace/registry_repos"; os.makedirs(REPOS,exist_ok=True)
OUT=H+"/scan.jsonl"; done={json.loads(l)["id"] for l in open(OUT)} if os.path.exists(OUT) else set()
SEL=set(json.load(open(H+"/selected_ids.json"))); cat=[p for p in json.load(open(H+"/catalog_live.json"))["plugins"] if p["id"] in SEL]
def sh(*a,cwd=None,t=180): return subprocess.run(a,cwd=cwd,capture_output=True,text=True,timeout=t)
def one(p):
    pid=p["id"]; d=os.path.join(REPOS,re.sub(r"[^\w.-]","_",pid)); c=p.get("listingValidatedCommit") or p.get("upstreamValidatedCommit")
    row=dict(id=pid,repo=p["repo"],commit=c,catalog_license=p.get("license"),addedAt=p.get("addedAt"),verificationCoverage=p.get("verificationCoverage"),status=p.get("status"))
    try:
        if not os.path.isdir(d+"/.git"):
            os.makedirs(d,exist_ok=True); sh("git","init","-q",cwd=d); sh("git","remote","add","origin",p["repo"],cwd=d)
            r=sh("git","fetch","-q","--depth","1","origin",c or "HEAD",cwd=d)
            if r.returncode: row["clone"]="fallback-HEAD"; r=sh("git","fetch","-q","--depth","1","origin","HEAD",cwd=d)
            if r.returncode: row.update(clone="failed"); shutil.rmtree(d,True); return row
            sh("git","checkout","-q","FETCH_HEAD",cwd=d)
        row["head"]=sh("git","rev-parse","HEAD",cwd=d).stdout.strip()
        lf=[f for f in os.listdir(d) if re.match(r"(LICEN[SC]E|COPYING)(\.|$)",f,re.I)]
        lt=open(os.path.join(d,lf[0]),errors="ignore").read() if lf else ""
        lic=lic_text(lt) if lf else "NONE"
        cr=[l.strip() for l in lt.splitlines() if re.match(r"\s*(copyright|\(c\))",l,re.I) and not re.search(r"copyright (notice|holder|owner)",l,re.I)][:2]
        dhh_only = bool(cr) and all(re.search(r"heinemeier|dhh|basecamp|37signals",x,re.I) for x in cr)
        row.update(license=lic,copyright=cr,license_ok= lic in PERM and bool(cr) and not dhh_only, dhh_only_fork=dhh_only)
        t0=time.time(); r=functest.test(src_dir=d)
        rt=r.get("runtime") or {}
        row.update(pass_=bool(r["pass"]),categories=r["categories"],static_fails=[f"{a}: {b}"[:160] for a,b in r["static_fails"]][:5],runtime_errors=[e[:160] for e in rt.get("errors",[])][:5],secs=round(time.time()-t0))
        if not (row["pass_"] and row["license_ok"]): shutil.rmtree(d,True)
    except Exception as e: row["error"]=repr(e)[:200]; shutil.rmtree(d,True)
    return row
todo=[p for p in cat if p["id"] not in done]
print(len(cat),"verified;",len(todo),"todo",flush=True)
with open(OUT,"a") as f, ThreadPoolExecutor(int(os.environ.get("J","8"))) as ex:
    for row in ex.map(one,todo): f.write(json.dumps(row)+"\n"); f.flush()
