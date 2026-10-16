#!/usr/bin/env python3
"""r7 step (gap c): per-plugin history mining of LATER versions, resumable and streaming. Reuses the earlier mining (candidates.jsonl fix commits, verified pairs); only runs the pinned Checker over sampled
versions of those repos to get labels the earlier passes could not give. Per repo: blobless bare clone -> sample versions -> Checker at each -> mechanical labels -> per-repo json.gz -> clone deleted.
CONFIRM = Checker finding at a fix commit's parent, gone at the commit, whose cited line is among the lines the commit removed/changed.
DISMISS (provisional, warn-level static only) = rule+file+line text persists unchanged in >= N later sampled versions (the newest included).
CLEAN = version with no fail-level finding, every finding dismissable (or none), and no fix-like commit touching its code files in the next K commits.
ADDED candidates = security-like fix commits with their removed lines (the LLM stage decides category).
usage: build_r7_mine.py OUTDIR [--n 300] [--seed 7] [--workers 6]"""
import sys, os, re, json, gzip, io, tarfile, subprocess, shutil, random, difflib, argparse, time, hashlib, collections
H = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(H); M = os.path.dirname(T)
sys.path[:0] = [M, T, H]
from scope import checker_findings as CF

CLONES = os.environ.get("R7_CLONES", "/workspace/r7_clones"); VH = "/workspace/usuba-runs/version-history/data/"
FIX = re.compile(r"\b(fix(es|ed|ing)?|bug(fix)?|crash(es|ed)?|error|broken|break(s|ing)?|regress(ion)?|hang(s)?|fail(s|ed|ure|ing)?|wrong|incorrect|exception|leak|race|null|undefined|invalid|stuck|corrupt\w*)\b", re.I)
SKIP = re.compile(r"^(docs?|chore|style|refactor|feat|test|ci|build|release|bump)(\(.*\))?[:!]|^merge |^bump |^release |^v?\d+\.\d+|\b(readme|changelog|license|screenshot)\b", re.I)
SEC = re.compile(r"secret|credential|token|password|passwd|api.?key|inject|sanitiz|escap|\bpin(ned|ning)?\b|checksum|sha-?256|signature|verify|\bhttps?\b|\btls\b|ssl|certificate|permission|chmod|symlink|xss|vuln|security|cve|untrusted|overwrit|clobber|manifest|metadata|licen[cs]e|duplicate|markup|rich.?text|html", re.I)
EXT = (".qml", ".js", ".mjs", ".sh", ".bash", ".py", ".lua", ".json", ".toml", ".md", ".txt", ".service", ".desktop", ".conf", ".rs", ".yaml", ".yml")
CODE = EXT[:10]
OK_LIC = (("MIT", r"permission is hereby granted, free of charge"), ("Apache-2.0", r"apache license"), ("BSD", r"redistribution and use in source and binary forms"), ("ISC", r"permission to use, copy, modify, and/or distribute"))
N_DISMISS = int(os.environ.get("R7_N_DISMISS", "3")); MAX_FIX = int(os.environ.get("R7_MAX_FIX", "8")); MAX_V = int(os.environ.get("R7_MAX_V", "18")); NEXT_K = 10
MAX_FILE = 200_000; MAX_TREE = 700_000
PRIOR = collections.defaultdict(set); VERIFIED = set()


def git(d, *a, timeout=120):
    r = subprocess.run(["git", "-C", d] + list(a), capture_output=True, timeout=timeout)
    if r.returncode: raise RuntimeError(r.stderr.decode(errors="replace")[-200:])
    return r.stdout


def tree(d, rev):
    p = subprocess.run(["git", "-C", d, "archive", rev], capture_output=True, timeout=180)
    if p.returncode: return None
    out = {}; tot = 0
    with tarfile.open(fileobj=io.BytesIO(p.stdout), mode="r:") as tf:
        for m in tf:
            if not m.isfile() or m.size > MAX_FILE: continue
            n = m.name
            if not (n.lower().endswith(EXT) or re.match(r"(?i)(licen[cs]e|copying)", os.path.basename(n)) or n.startswith("bin/") or "/bin/" in n): continue
            if n.startswith((".git/", "node_modules/", "vendor/")) or "/node_modules/" in n: continue
            b = tf.extractfile(m).read()
            if b"\0" in b[:2000]: continue
            tot += len(b)
            if tot > MAX_TREE: break
            out[n] = b.decode("utf-8", "replace")
    return out


def license_of(files):
    for k, v in files.items():
        if re.match(r"(?i)(licen[cs]e|copying)", os.path.basename(k)) and "/" not in k:
            for name, rx in OK_LIC:
                if re.search(rx, v, re.I): return name
    return None


def log(d):
    raw = git(d, "log", "--first-parent", "-n", "500", "--name-only", "--format=\x1e%H\x1f%P\x1f%aI\x1f%ae\x1f%s\x1f%b\x1f").decode("utf-8", "replace")
    cs = []
    for blk in raw.split("\x1e")[1:]:
        head, _, files = blk.rpartition("\x1f"); f = head.split("\x1f")
        if len(f) < 6: continue
        cs.append(dict(sha=f[0], parents=f[1].split(), date=f[2], email=f[3], subject=f[4], body=f[5][:700], files=[x for x in files.split("\n") if x.strip()]))
    return list(reversed(cs))


def keyf(f, text):
    ls = (text or "").split("\n"); l = f["line"]
    return (f["rule"], f["file"], (ls[l - 1].strip() if 1 <= l <= len(ls) else None))


def changed_old_lines(a, b):
    A, B = a.split("\n"), b.split("\n"); ch = set(); hunks = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
        if tag in ("replace", "delete"): ch.update(range(i1 + 1, i2 + 1)); hunks.append((i1 + 1, A[i1:i2], B[j1:j2]))
    return ch, hunks


def mine(url, out_dir):
    name = url.replace("https://github.com/", "").replace("/", "__"); dst = os.path.join(out_dir, "repos", name + ".json.gz")
    if os.path.exists(dst): return name, "cached"
    d = os.path.join(CLONES, name); t0 = time.time(); res = dict(repo=name, url=url, status=None, cands=[], stats=collections.Counter())
    try:
        r = subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none", "--single-branch", url + ".git", d], capture_output=True, timeout=150, env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        if r.returncode: res["status"] = "clone_failed"; raise StopIteration
        cs = log(d)
        if len(cs) < 3: res["status"] = "too_few_commits"; raise StopIteration
        idx = {c["sha"]: i for i, c in enumerate(cs)}; head = tree(d, cs[-1]["sha"]); lic = license_of(head or {})
        if not head or not lic: res["status"] = "no_permissive_license"; raise StopIteration
        res["license"] = lic; res["head_date"] = cs[-1]["date"]
        prior = PRIOR.get(name, set()); res["stats"]["prior_candidate_commits"] = len(prior)
        fixes = [c for c in cs if len(c["parents"]) == 1 and c["parents"][0] in idx and (c["sha"] in prior if prior else (FIX.search(c["subject"]) and not SKIP.search(c["subject"])))]
        rnd = random.Random(hashlib.md5(name.encode()).hexdigest()); sec = [c for c in fixes if SEC.search(c["subject"] + " " + c["body"][:200])]; oth = [c for c in fixes if c not in sec]
        rnd.shuffle(sec); rnd.shuffle(oth); pick = (sec[:MAX_FIX // 2 + 2] + oth)[:MAX_FIX]; res["stats"]["fix_like"] = len(fixes)
        vs = set()
        for c in pick: vs.add(c["sha"]); vs.add(c["parents"][0])
        vs.add(cs[-1]["sha"]); step = max(1, len(cs) // 4)
        for i in range(step, len(cs), step): vs.add(cs[i]["sha"])
        vs = sorted(vs, key=lambda s: idx[s])
        if len(vs) > MAX_V: vs = vs[-MAX_V:]
        TR, FD = {}, {}
        for s in vs:
            t = head if s == cs[-1]["sha"] else tree(d, s)
            if t: TR[s] = t; FD[s] = CF.findings_for(t)
        order = [s for s in vs if FD.get(s) is not None]; res["stats"]["versions_checked"] = len(order)
        persist = {}
        for i, s in enumerate(order):
            later = [set(keyf(f, TR[l].get(f["file"])) for f in FD[l] if f["line"]) for l in order[i + 1:]]
            persist[s] = {keyf(f, TR[s].get(f["file"])): sum(1 for L in later if keyf(f, TR[s].get(f["file"])) in L) for f in FD[s] if f["line"]}

        def labels_for(s, confirm_keys, c=None):
            lab = []
            for f in FD[s]:
                k = keyf(f, TR[s].get(f["file"]))
                if f["line"] and k in confirm_keys: lab.append(dict(decision="confirm", basis="fix-commit removed or changed the cited line", evidence=dict(commit=c["sha"], subject=c["subject"], line=f["line"], quote=k[2])))
                elif f["line"] and f["level"] == "warn" and f["stage"] == "static" and persist.get(s, {}).get(k, 0) >= N_DISMISS: lab.append(dict(decision="dismiss", basis="provisional: line unchanged in >= %d later versions, warn-level" % N_DISMISS, evidence=dict(later=persist[s][k], quote=k[2])))
                else: lab.append(dict(decision=None, basis=None, evidence=None))
            return lab
        for c in pick:
            p = c["parents"][0]
            if FD.get(p) is None or FD.get(c["sha"]) is None: res["stats"]["fix_no_trees"] += 1; continue
            fp, fc = FD[p], FD[c["sha"]]; confirm = set(); hunks_all = []
            for fn in TR[p]:
                ch, hk = changed_old_lines(TR[p][fn], TR[c["sha"]].get(fn, ""))
                if fn.endswith(CODE) and len(hunks_all) < 6: hunks_all += [dict(file=fn, old_line=i, removed=[x[:300] for x in rem[:6]], added=[x[:300] for x in add[:6]]) for i, rem, add in hk][:4]
                for f in fp:
                    if f["file"] == fn and f["line"] in ch:
                        k = keyf(f, TR[p][fn])
                        if k[2] and k not in {keyf(g, TR[c["sha"]].get(g["file"])) for g in fc if g["file"] == fn}: confirm.add(k)
            sec_like = bool(SEC.search(c["subject"] + " " + c["body"][:300]))
            if not confirm and not sec_like: continue
            res["cands"].append(dict(kind="fix", version=p, commit=c["sha"], date=c["date"], subject=c["subject"], body=c["body"], author=c["email"], files=TR[p], findings=fp, labels=labels_for(p, confirm, c),
                                     hunks=hunks_all if sec_like else [], sec_like=sec_like, n_confirm=len(confirm)))
        nclean = 0
        for s in order[:-1]:
            if nclean >= 2: break
            if any(f["level"] == "fail" for f in FD[s]): continue
            lab = labels_for(s, set())
            if any(l["decision"] is None for l in lab): continue
            code = {x for x in TR[s] if x.endswith(CODE)}; nxt = cs[idx[s] + 1: idx[s] + 1 + NEXT_K]
            if any(len(c["parents"]) == 1 and FIX.search(c["subject"]) and not SKIP.search(c["subject"]) and (set(c["files"]) & code) for c in nxt): continue
            res["cands"].append(dict(kind="clean", version=s, commit=None, date=cs[idx[s]]["date"], subject=cs[idx[s]]["subject"], body="", author=cs[idx[s]]["email"], files=TR[s], findings=FD[s], labels=lab, hunks=[], sec_like=False, n_confirm=0)); nclean += 1
        res["status"] = "ok"
    except StopIteration:
        pass
    except Exception as e:
        res["status"] = "error:" + repr(e)[:100]
    finally:
        shutil.rmtree(d, ignore_errors=True)
    res["stats"] = dict(res["stats"]); res["secs"] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with gzip.open(dst + ".tmp", "wt") as f: json.dump(res, f)
    os.replace(dst + ".tmp", dst)
    return name, res["status"]


def select(n, seed):
    for l in open(VH + "candidates.jsonl"):
        c = json.loads(l); PRIOR[c["repo"]].add(c["commit"])
    for f in ("verified_pairs.jsonl", "verified_pairs_2.jsonl"):
        for l in open(VH + f): VERIFIED.add(json.loads(l)["url"])
    U = json.load(open(VH + "universe.json"))["repos"]; ex = set()
    for fn in ("S4_EXCLUDE_REPOS.txt", "allkinds_S4_EXCLUDE_REPOS.txt"):
        p = os.path.join("/workspace/usuba-runs/scope-v4/drafts", fn)
        if os.path.exists(p): ex |= {l.strip().lower().split("github.com/")[-1] for l in open(p) if l.strip()}
    nm = lambda u: u.replace("https://github.com/", "").replace("/", "__")
    keep = [u for u in U if u.lower().split("github.com/")[-1] not in ex and PRIOR.get(nm(u))]
    random.Random(seed).shuffle(keep); return keep[:n]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--n", type=int, default=300); ap.add_argument("--seed", type=int, default=7); ap.add_argument("--workers", type=int, default=6); a = ap.parse_args()
    from concurrent.futures import ThreadPoolExecutor
    os.makedirs(CLONES, exist_ok=True); repos = select(a.n, a.seed); done = 0; cnt = collections.Counter()
    with ThreadPoolExecutor(a.workers) as ex:
        for name, st in ex.map(lambda u: mine(u, a.out), repos):
            done += 1; cnt[st.split(":")[0]] += 1
            if done % 10 == 0 or done == len(repos): print(done, len(repos), dict(cnt), flush=True)
