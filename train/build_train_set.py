#!/usr/bin/env python3
"""Build the Usuba 9B fine-tune set (chat JSONL) with per-example provenance.

Sources
  A. HANCORE reviewer examples (data/hancore_reviewer/examples.jsonl.gz): code + Checker report -> HANCORE findings.
     weak_label rows (closed_no_fix / stale / not_planned only) are dropped.
  B. Dell in-use examples (dell/sweep/results.jsonl + dell_ext.jsonl): toggle opened nothing, missing binary on the Dell,
     memory growth >150 MB/20 s, and panels whose close path throws the read-only centerHoverRevealSuppressed TypeError
     (in-use: panel cannot close; confirmed independently by GitHub issues, see DELL_LEARNINGS.md section 2b).
  C. Grader-verified load examples: Dell label and box Checker verdict AGREE (broken+FAIL or works+PASS).
Exclusions
  - every repo / plugin id / near-duplicate code tree of eval/hancore_holdout (strict, checked three ways)
  - the Dell answer key plugins (functest/dell_ground_truth.jsonl), kept as the regression set
  - exact duplicate code trees inside the training set
Output: train/data/{train,val}.jsonl, train/data/manifest.json. Deterministic (seed 1337).
Usage: python3 train/build_train_set.py [--limit N] [--workers 8]"""
import argparse, gzip, hashlib, io, json, os, random, re, sys, tarfile, collections, ast
from concurrent.futures import ProcessPoolExecutor
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(H)
sys.path[:0] = [H, os.path.join(ROOT, "functest"), os.path.join(ROOT, "hancore")]
import prompt
SW = os.path.join(ROOT, "dell", "sweep"); OUT = os.path.join(H, "data")
CODE_CAP, FILE_CAP = 24000, 8000
CAPS = dict(dell_inuse_missing_binary=450, dell_inuse_close=120, dell_broken_verified=450, dell_works_verified=550)
FIND_CAP = 1200

def norm_repo(s): return s.lower().rstrip("/").removesuffix(".git").split("github.com/")[-1]
def file_hashes(files):
    out = set()
    for p, c in files.items():
        if p.lower().startswith(("readme", "license")) or not c.strip(): continue
        out.add(hashlib.sha1(re.sub(r"\s+", "", c).encode()).hexdigest())
    return out
def manifest_id(files):
    try: return (json.loads(files.get("manifest.json", "{}")) or {}).get("id")
    except Exception: return None

# ---------- holdout fingerprint ----------
def holdout_fingerprint():
    hd = os.path.join(ROOT, "eval", "hancore_holdout"); repos, ids, trees = set(), set(), []
    for l in open(os.path.join(hd, "manifest.jsonl")):
        m = json.loads(l); repos.add(norm_repo(m["repo"]))
        files = {}
        with tarfile.open(os.path.join(hd, m["code_archive"])) as t:
            for mem in t.getmembers():
                if not mem.isfile() or mem.size > 2_000_000: continue
                p = mem.name.split("/", 1)[-1]
                try: files[p] = t.extractfile(mem).read().decode("utf-8")
                except Exception: pass
        i = manifest_id(files)
        if i: ids.add(i.lower())
        fh = file_hashes(files)
        if fh: trees.append(fh)
    for l in open(os.path.join(hd, "plugin_ids.txt")): repos.add(norm_repo(l.strip()))
    return repos, ids, trees
def near_dup(fh, trees, thr=0.5):
    if not fh: return False
    for t in trees:
        inter = len(fh & t)
        if inter and inter / min(len(fh), len(t)) >= thr: return True
    return False

# ---------- helpers ----------
def scrub(s):
    from build_reviewer_scrub import scrub as sc
    return sc(s)
def code_blob(files):
    order = lambda p: (0 if p == "manifest.json" else 1 if p.endswith((".qml", ".js", ".sh", ".py", ".lua", ".bash")) else 2 if p.lower().startswith("readme") else 3, p)
    out, n = [], 0
    for p in sorted(files, key=order):
        c = files[p][:FILE_CAP]
        if n + len(c) > CODE_CAP: out.append(f"### {p}\n(omitted: {len(files[p])} chars)"); continue
        out.append(f"### {p}\n```\n{c}\n```"); n += len(c)
    return "\n\n".join(out)
def lit(v):
    if isinstance(v, str):
        try: return ast.literal_eval(v)
        except Exception:
            try: return json.loads(v)
            except Exception: return v
    return v

# ---------- A. HANCORE ----------
def hancore_examples(st):
    rows = []
    for l in gzip.open(os.path.join(ROOT, "data", "hancore_reviewer", "examples.jsonl.gz"), "rt"):
        e = json.loads(l)
        if str(e["weak_label"]) == "True": st["hancore_dropped_weak_label"] += 1; continue
        inp, tgt = lit(e["input"]), lit(e["target"])
        fl = []
        for f in tgt["findings"]:
            if f["strength"] in ("closed_no_fix", "stale", "not_planned"): continue
            cats = [c for c in f["categories"] if c != "clean-review-no-blocker"] or ["other"]
            sev = "blocker" if f["strength"] in ("strong", "likely") else "warning"
            fl.append(dict(category=cats[0], also=cats[1:] or None, severity=sev, file=None, finding=f["finding"][:FIND_CAP]))
        fl = [{k: v for k, v in f.items() if v is not None} for f in fl]
        verdict = "changes_requested" if any(f["severity"] == "blocker" for f in fl) else "approve"
        rows.append(dict(source="hancore", repo=norm_repo(e["repo"]), plugin_id=None, weight=float(e["weight"]),
                         code=inp["code"], checker_report=inp.get("checker_report"),
                         target=dict(verdict=verdict, load=None, findings=fl),
                         provenance=dict(kind="hancore-review", commit=e["commit"], strength=e["strength"], threads=lit(e["threads"]),
                                         comment_urls=[f["provenance"]["comment_url"] for f in tgt["findings"]][:5])))
    return rows

# ---------- B/C. Dell ----------
CLOSE = "centerHoverRevealSuppressed"
def dell_candidates(key_ids, st):
    EX = {}
    for l in open(SW + "/dell_ext.jsonl"): e = json.loads(l); EX[(e["run"], e["job"])] = e
    C = {json.loads(l)["key"]: json.loads(l) for l in open(SW + "/corpus.jsonl")}
    bugs = collections.defaultdict(list)
    for l in open(SW + "/issue_bugs.jsonl"): b = json.loads(l); bugs[norm_repo(b["repo"])].append(b)
    out = collections.defaultdict(list)
    for l in open(SW + "/results.jsonl"):
        r = json.loads(l); d = r.get("dell") or {}; c = C.get(r["key"]) or {}
        if r["label"] not in ("works", "broken", "unsure") or not d or not c.get("local_dir") or not os.path.isdir(c["local_dir"]): continue
        if r.get("plugin_id") in key_ids: st["dell_excluded_answer_key"] += 1; continue
        e = EX.get((d.get("run"), d.get("job"))) or {}; ck = r.get("checker") or {}
        reasons = r["reasons"]; qml = d.get("qml_errors") or []
        f = []
        if any(w.startswith("usage:") for w in reasons):
            f.append(("in-use:toggle-opens-nothing", "blocker", None, "On a real Omarchy 4.0.4 session the IPC toggle succeeded but no new surface appeared; the panel/overlay opens nothing for the user."))
        mb = sorted(set(d.get("missing_bins") or []))
        if mb or any(w.startswith("dependency:") for w in reasons):
            what = ", ".join(mb[:4]) if mb else "a binary listed in the code"
            f.append(("in-use:missing-binary", "blocker" if r["label"] != "works" else "warning", None,
                      f"Runs {what} at runtime, which is not installed on a stock Omarchy system and is not shipped or declared as a dependency."))
        g = e.get("rss_growth_mb") or 0
        if g > 150:
            f.append(("in-use:memory-growth", "blocker" if g > 300 else "warning", None, f"Shell memory grew {int(g)} MB within 20 s of loading (peak {e.get('rss_max_mb')} MB); something keeps allocating."))
        close_q = [q for q in qml if CLOSE in q]
        close_iss = [b for b in bugs.get(norm_repo(r["key"]), []) if CLOSE in b["title"] or "close" in b["title"].lower()]
        if close_q:
            fn = close_q[0].split("/")[-1].split("[")[0]
            f.append(("in-use:panel-cannot-close", "blocker", fn, "close() assigns the shell's read-only centerHoverRevealSuppressed property, which throws a TypeError on Omarchy 4.0.3+; the panel cannot be dismissed with Esc/outside click and can trap keyboard focus."))
        fat = [q for q in qml if re.search(r"is not a type|is not installed|Failed to load|SyntaxError|Expected token|Type \S+ unavailable|Cannot create delegate", q)]
        if fat: f.append(("load:component-not-created", "blocker", fat[0].split("/")[-1].split("[")[0], "QML component is not created: " + fat[0][-220:]))
        verified = (r["label"] == "broken" and ck.get("pass_") is False) or (r["label"] == "works" and ck.get("pass_") is True)
        if r["label"] == "broken" and ck.get("pass_") is False:
            for txt in (ck.get("static_fails") or [])[:4]:
                txt = txt if isinstance(txt, str) else ": ".join(map(str, txt))
                m = re.match(r"\[([\w-]+)\]\s*", txt)
                f.append(("checker:" + (m.group(1) if m else "static"), "blocker", None, txt[m.end() if m else 0:][:400]))
            for txt in (ck.get("runtime_errors") or [])[:3]:
                f.append(("load:checker-runtime", "blocker", None, str(txt)[:400]))
        # bucket (an example goes to its most specific bucket)
        cats = [x[0] for x in f]
        if "in-use:toggle-opens-nothing" in cats or "in-use:memory-growth" in cats: b = "dell_inuse_usage_memory"
        elif "in-use:panel-cannot-close" in cats: b = "dell_inuse_close"
        elif "in-use:missing-binary" in cats: b = "dell_inuse_missing_binary"
        elif verified and r["label"] == "broken": b = "dell_broken_verified"
        elif verified and r["label"] == "works" and not f: b = "dell_works_verified"
        else: st["dell_skipped_unverified"] += 1; continue
        seen = set(); fl = []
        for cat, sev, fn, txt in f:
            if (cat, txt[:60]) in seen: continue
            seen.add((cat, txt[:60])); fl.append({k: v for k, v in dict(category=cat, severity=sev, file=fn, finding=txt).items() if v is not None})
        load = r["label"]
        verdict = "changes_requested" if any(x["severity"] == "blocker" for x in fl) else "approve"
        rep = [(t if isinstance(t, str) else ": ".join(map(str, t)))[:300] for t in (ck.get("static_fails") or [])] + [f"[runtime] {str(t)[:300]}" for t in (ck.get("runtime_errors") or [])]
        out[b].append(dict(source=b, repo=norm_repo(r["key"]), plugin_id=r.get("plugin_id"), weight=1.0, local_dir=c["local_dir"], tree_hash=c.get("tree_hash"),
                           checker_report=rep, target=dict(verdict=verdict, load=load, findings=fl),
                           provenance=dict(kind="dell-sweep" + ("+checker-agree" if verified else ""), commit=r.get("commit"), dell_run=d.get("run"), dell_job=d.get("job"),
                                           dell_label=r["label"], checker_pass=ck.get("pass_"), issue_urls=[x["url"] for x in close_iss][:3] or None)))
    return out

def load_code(row):
    import functest
    from build_reviewer_scrub import scrub
    files = functest.read_dir(row["local_dir"])
    return scrub(code_blob(files)), sorted(file_hashes(files)), manifest_id(files)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=OUT); a = ap.parse_args()
    rnd = random.Random(1337); st = collections.Counter(); os.makedirs(a.out, exist_ok=True)
    h_repos, h_ids, h_trees = holdout_fingerprint(); st["holdout_repos"] = len(h_repos); st["holdout_manifest_ids"] = len(h_ids)
    key_ids = {json.loads(l)["id"] for l in open(os.path.join(ROOT, "functest", "dell_ground_truth.jsonl"))}
    rows = hancore_examples(st)
    dc = dell_candidates(key_ids, st)
    for b, L in sorted(dc.items()):
        rnd.shuffle(L); st[f"candidates:{b}"] = len(L)
        rows += L[:CAPS.get(b, len(L))]
    if a.limit: rnd.shuffle(rows); rows = rows[:a.limit]
    need = [r for r in rows if "local_dir" in r]
    with ProcessPoolExecutor(a.workers) as ex:
        for r, (code, fh, mid) in zip(need, ex.map(load_code, need, chunksize=16)): r["code"], r["_fh"], r["_mid"] = code, set(fh), mid
    kept, seen_code = [], set()
    for r in rows:
        if r["repo"] in h_repos: st["excluded_holdout_repo:" + r["source"]] += 1; continue
        mid = r.get("_mid") or (manifest_id({"manifest.json": m.group(1)}) if (m := re.search(r"### manifest.json\n```\n(.*?)\n```", r["code"], re.S)) else None)
        if mid and mid.lower() in h_ids: st["excluded_holdout_manifest_id:" + r["source"]] += 1; continue
        fh = r.get("_fh") or {hashlib.sha1(re.sub(r"\s+", "", blk).encode()).hexdigest() for blk in re.findall(r"### (?!README|LICENSE)[^\n]+\n```\n(.*?)\n```", r["code"], re.S) if blk.strip()}
        if near_dup(fh, h_trees): st["excluded_holdout_near_dup:" + r["source"]] += 1; continue
        ch = hashlib.sha1(r["code"].encode()).hexdigest()
        if ch in seen_code: st["excluded_dup_in_train:" + r["source"]] += 1; continue
        seen_code.add(ch); kept.append(r)
    rnd.shuffle(kept)
    by_repo = collections.defaultdict(list)
    for r in kept: by_repo[r["repo"]].append(r)
    repos = sorted(by_repo); rnd.shuffle(repos); nval = max(1, int(len(repos) * 0.03))
    val_repos = set(repos[:nval])
    with open(os.path.join(a.out, "train.jsonl"), "w") as ft, open(os.path.join(a.out, "val.jsonl"), "w") as fv:
        for r in kept:
            rec = dict(id=f"{r['source']}:{r['repo']}", source=r["source"], weight=r["weight"], provenance=r["provenance"],
                       messages=prompt.messages(r["code"], r["checker_report"], r["target"]))
            (fv if r["repo"] in val_repos else ft).write(json.dumps(rec, ensure_ascii=False) + "\n")
            st[("val:" if r["repo"] in val_repos else "train:") + r["source"]] += 1
    st["train_total"] = sum(v for k, v in st.items() if k.startswith("train:")); st["val_total"] = sum(v for k, v in st.items() if k.startswith("val:"))
    cats = collections.Counter(f["category"] for r in kept for f in r["target"]["findings"])
    man = dict(stats=dict(sorted(st.items())), finding_categories=dict(cats.most_common()), caps=CAPS, seed=1337,
               exclusions=["eval/hancore_holdout: repo, manifest id, near-dup code tree (>=50% shared file hashes)", "functest/dell_ground_truth.jsonl plugin ids", "exact duplicate code"])
    man["sha256"] = {f: hashlib.sha256(open(os.path.join(a.out, f), "rb").read()).hexdigest() for f in ("train.jsonl", "val.jsonl")}
    json.dump(man, open(os.path.join(a.out, "manifest.json"), "w"), indent=1); print(json.dumps(man, indent=1))
if __name__ == "__main__": main()
