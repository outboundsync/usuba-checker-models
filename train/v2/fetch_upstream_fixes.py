#!/usr/bin/env python3
"""Upstream fixes for HANCORE fixed:* findings.
For every non-holdout HANCORE example whose non-weak findings are all fixed:*, find the fix-evidence comment (latest),
take the plugin repo's default-branch commit at that time (GitHub commits?until=), download it (codeload, no API cost),
and run the Checker / Omarchy 4.0.4 grader (functest.test). Resumable. -> /workspace/v2fix/upstream.jsonl"""
import gzip, json, ast, os, re, subprocess, sys, io, tarfile, time
from concurrent.futures import ThreadPoolExecutor, as_completed
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, os.path.join(ROOT, "hancore")); from fetch import EXT
W = os.environ.get("V2FIX", "/workspace/v2fix"); OUT = W + "/upstream.jsonl"; CODE = W + "/up"
GRADE = r'''
import json,sys; sys.path.insert(0, sys.argv[1] + "/functest"); import functest
x = functest.test(src_dir=sys.argv[2]); rt = x.get("runtime") or {}
print("@@" + json.dumps(dict(pass_=bool(x["pass"]), categories=x["categories"], static_fails=[list(s)[:2] for s in x["static_fails"]][:8], runtime_errors=[e[:300] for e in rt.get("errors", [])][:8])))
'''
def grade(d):
    try:
        p = subprocess.run([sys.executable, "-c", GRADE, ROOT, d], capture_output=True, text=True, timeout=240, start_new_session=True)
        line = [l for l in p.stdout.splitlines() if l.startswith("@@")]
        return json.loads(line[-1][2:]) if line else dict(pass_=None, error=(p.stderr or p.stdout)[-300:])
    except subprocess.TimeoutExpired: return dict(pass_=None, error="grader timeout 240s")
def gh(path):
    p = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=60)
    if p.returncode: raise RuntimeError(p.stderr[-200:])
    return json.loads(p.stdout)
def download(repo, sha):
    d = os.path.join(CODE, repo.replace("/", "__") + "@" + sha)
    if os.path.exists(d + "/.ok"): return d
    b = subprocess.run(["curl", "-sfL", f"https://codeload.github.com/{repo}/tar.gz/{sha}"], capture_output=True, timeout=120).stdout
    t = tarfile.open(fileobj=io.BytesIO(b), mode="r:gz"); os.makedirs(d, exist_ok=True)
    for m in t.getmembers():
        if not m.isfile() or m.size > 256_000: continue
        rel = m.name.split("/", 1)[1] if "/" in m.name else m.name
        if not rel.endswith(EXT) or "/node_modules/" in "/" + rel or rel.startswith(".git/"): continue
        data = t.extractfile(m).read()
        try: data.decode("utf-8")
        except UnicodeDecodeError: continue
        p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(data)
    open(d + "/.ok", "w").write("1"); return d
def candidates():
    hold = {l.strip().lower().split("github.com/")[-1].rstrip("/") for l in open(ROOT + "/eval/hancore_holdout/plugin_ids.txt") if l.strip()}
    for l in open(ROOT + "/eval/hancore_holdout/manifest.jsonl"): hold.add(json.loads(l)["repo"].lower().split("github.com/")[-1].rstrip("/"))
    for l in gzip.open(ROOT + "/data/hancore_reviewer/examples.jsonl.gz", "rt"):
        e = json.loads(l); t = e["target"]; t = ast.literal_eval(t) if isinstance(t, str) else t
        fs = [f for f in t["findings"] if f["strength"] in ("strong", "likely", "open")]
        if not fs or not all(str(f["outcome"]).startswith("fixed") for f in fs): continue
        if e["repo"].lower() in hold: continue
        ev = [f["provenance"].get("fix_evidence_url") for f in fs if f["provenance"].get("fix_evidence_url")]
        if not ev: continue
        ev = max(ev, key=lambda u: int(re.search(r"issuecomment-(\d+)", u).group(1)) if "issuecomment-" in u else 0)
        yield dict(repo=e["repo"], parent_commit=e["commit"], fix_evidence_url=ev, threads=[f["provenance"]["thread"] for f in fs][:3])
def one(c):
    r = dict(c)
    try:
        m = re.search(r"github\.com/([^/]+/[^/]+)/issues/\d+#issuecomment-(\d+)", c["fix_evidence_url"])
        when = gh(f"repos/{m.group(1)}/issues/comments/{m.group(2)}")["created_at"]; r["fix_evidence_at"] = when
        cm = gh(f"repos/{c['repo']}/commits?until={when}&per_page=1")
        if not cm: r["status"] = "no-commit"; return r
        sha = cm[0]["sha"]; r["fix_commit"] = sha; r["fix_url"] = f"https://github.com/{c['repo']}/commit/{sha}"
        if sha == c["parent_commit"]: r["status"] = "same-as-parent"; return r
        r["code_dir"] = download(c["repo"], sha); r["grader"] = grade(r["code_dir"])
        r["status"] = "pass" if r["grader"].get("pass_") else "fail"
    except Exception as e: r["status"] = "error"; r["error"] = repr(e)[:300]
    return r
if __name__ == "__main__":
    os.makedirs(CODE, exist_ok=True)
    done = {(json.loads(l)["repo"], json.loads(l)["parent_commit"]) for l in open(OUT)} if os.path.exists(OUT) else set()
    todo = [c for c in candidates() if (c["repo"], c["parent_commit"]) not in done]
    print("todo", len(todo), flush=True)
    with ThreadPoolExecutor(6) as ex, open(OUT, "a") as f:
        for i, fu in enumerate(as_completed([ex.submit(one, c) for c in todo])):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
            if i % 50 == 0: print(i, time.strftime("%H:%M"), flush=True)
    print("ALLDONE", flush=True)
