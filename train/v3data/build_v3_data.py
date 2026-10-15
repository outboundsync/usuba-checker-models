#!/usr/bin/env python3
"""Usuba v3 training-data DRAFT (no training). Same record schema as the v2 final set (train_lora.py unchanged).
Sources: (a) HANCORE verified concrete findings (high+medium confidence, file+line, quoted-construct verified at the reviewed commit),
(b) v2 dell_broken_verified (+inuse rows that cite file:line) with Qwen3.5-397B guided answers, (c) works approve rows (v2 dell_works_verified, nudged_approve),
(d) upstream verified fixes (v2 fix_upstream). No Anthropic/DeepSeek/Gemini output. Reads no Dell labels (only the v2 rows already built, and Dell key *ids/trees* for exclusion).
Usage: python3 build_v3_data.py [--out DIR]"""
import argparse, collections, gzip, hashlib, json, os, random, re, sys, statistics
from concurrent.futures import ProcessPoolExecutor
H = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(H); ROOT = os.path.dirname(T)
sys.path[:0] = [T, os.path.join(ROOT, "functest"), os.path.join(ROOT, "hancore"), os.path.join(T, "v2", "distill")]
import prompt_v3 as P   # v3 system prompt + shots; every row uses it (v2-derived rows are re-wrapped with P.rebuild)
import build_train_set as B
STORE = "/cursor/stores/store-59a6dbfe-4592-4709-aa00-b03118ea5a20/usuba-v2distill/"
HL = "/workspace/usuba-runs/hancore-labels/"
QWEN_TOK = os.path.expanduser("~/.cache/huggingface/hub/models--Qwen--Qwen3.5-9B/snapshots/c202236235762e1c871ad0ccb60c8ee5ba337b9a/tokenizer.json")
MAX_TOK = 32000          # train_lora max_len is 32768; keep margin
CODE_CAP, FILE_CAP, CITED_CAP = 24000, 8000, 16000
MAX_FINDINGS = 3; FIND_LEN = 300
HYG = re.compile(r"(?i)remains? (blocked|open)|still (pins|blocked|open)|blocked:|retarget|\bthe update\b|re-?review|\bprevious|\bearlier\b|\bblocker remains|\bremaining\b|cannot be approved|\bagain\b")   # prompt_v3: no earlier-review wording in findings
HYG_URL = re.compile(r"(?i)https?://|\(\[|kernel doc")   # citations of external URLs: dropped for HANCORE prose only (Dell placeholder-endpoint findings legitimately quote a URL)
KEEP_V2 = {"dell_broken_verified", "dell_inuse_close", "dell_inuse_missing_binary", "dell_works_verified", "nudged_approve", "fix_upstream"}
UNBOUNDED_CAP_SHARE = 0.20   # of all broken rows
BAD_WORDS = re.compile(r"(?i)\b(sonnet|claude|anthropic|deepseek|gemini|gpt-?\d|openai)\b")
_tk = None
def ntok(s):
    global _tk
    if _tk is None:
        from tokenizers import Tokenizer; _tk = Tokenizer.from_file(QWEN_TOK)
    return len(_tk.encode(s).ids)

# ---------- prose -> answer finding ----------
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
META = re.compile(r"(?i)(\bcommit\b|\bHEAD\b|\bSHA\b|\bre-?review|previous(ly)?\b|earlier (finding|review)|\bthanks\b|\bclosing\b|marketplace|\bvalidat|\bbaseline\b|\bis (now )?fixed\b|\bwas fixed\b|\bfix(ed)? (in|at|by)\b|\bprior (finding|review)|issue #|\bPR\b|#\d{3,})")
def sentences(s):
    s = re.sub(r"\s+", " ", s)
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z`\-\*])", s) if x.strip()]
def build_finding(r, scrub):
    """cleaned real prose, windowed around the sentence(s) that cite the file; <=300 chars. returns None if nothing usable."""
    base = os.path.basename(r["file"]); txt = B.clean_finding(scrub(r["prose"]))
    txt = re.sub(r"\[([^\]]+)\]\(https?://[^)]*\)", r"\1", txt); txt = re.sub(r"\*\*|__", "", txt); txt = re.sub(r"^[\-\*\d.)\s]+", "", txt)
    ss = sentences(txt)
    ss = [re.sub(r"`?\b[0-9a-f]{40}\b`?", "", x) for x in ss]
    idx = [i for i, x in enumerate(ss) if base in x and not META.search(x)] or [i for i, x in enumerate(ss) if not META.search(x) and (base in x or "`" in x)]
    if not idx: return None
    out = ""
    for x in ss[idx[0]:]:
        if META.search(x) or SHA.search(x) and re.search(r"[0-9]", SHA.search(x).group(0)) and len(SHA.search(x).group(0)) >= 12: continue
        if len(out) + len(x) + 1 > FIND_LEN:
            break
        out = (out + " " + x).strip()
    if not out:   # one long sentence: cut on a clause boundary
        x = ss[idx[0]]
        if META.search(x): return None
        cut = x[:FIND_LEN]; j = max(cut.rfind("; "), cut.rfind(", "), cut.rfind(" — "))
        out = cut[:j] if j > 120 else cut[:FIND_LEN - 1].rstrip()
        out = out.rstrip(" ,;:(") + "…"
    out = re.sub(r"\s+", " ", out).strip(" ,;:-")
    if len(out) < 40 or BAD_WORDS.search(out): return None
    return out[0].upper() + out[1:]
CODE_TOK = re.compile(r"`([^`\n]{2,80})`")
def is_generic(f):
    """boilerplate: no file+line, or prose names no concrete construct (no backticked identifier/command/path other than the bare file ref)"""
    if not f.get("file") or not isinstance(f.get("line"), int): return True
    spans = [m.group(1) for m in CODE_TOK.finditer(f["finding"])]
    spans = [s for s in spans if not re.fullmatch(r"[\w./@+-]+\.(qml|js|mjs|sh|py|lua|json|bash|conf|toml)(:\d+(-\d+)?)?", s)]
    return not spans


# ---- quality gates for HANCORE findings (v3: prose must state a problem, match the kind, and its construct must sit near the cited line) ----
NEG = re.compile(r"(?i)(\bno (finding|blocker|issue|concern)s?\b|not a (finding|bug|blocker|vulnerab)|false[- ]positive|\bbenign\b|\bharmless\b|state the opposite|matches? (are|is) (only )?(readme|prose|docs?)|\bnot (exploitable|reachable)\b|there is no \S+(, \S+)* (anywhere|in the repo)|\bno longer\b|\bresolved\b|\bremaining matches\b|\bonly (a )?(comment|documentation|readme)\b|\bnothing to (fix|change)\b|\bis (safe|fine|correct|acceptable)\b)")
HC = {"unbounded-input-resource": r"byte limit|exhaust|producer-side|unbounded|size cap|no (size |byte |line )?(cap|limit|bound)|without (a )?(size |byte )?(cap|limit|bound)|entire|complete(ly)? (output|stdout|file|response)|uncapped|buffer|large|memory|max(imum)?[ _-]?(bytes|size)|bounded|unlimited|whole|collect",
      "install-deps-packaging": r"install|depend|packag|not (installed|shipped)|missing (binary|dependency)|pip|npm|pacman|yay|aur|apt|marker|service",
      "file-safety-symlink-perms": r"symlink|permission|predictable|world-?(read|writ)|/tmp|race|atomic|chmod|umask|0[67][0-7]{2}|mktemp|redirect|overwrit|temp(orary)?",
      "secrets-credentials": r"secret|credential|token|password|api[ _-]?key|session|bearer|keyring|cookie|auth",
      "privileged-system": r"sudo|root|privileg|systemd|pkexec|polkit|/etc|system(-wide)?|setuid|udev|capabilit",
      "process-lifecycle-timeouts": r"timeout|deadline|hang|never (exit|terminat|return)|orphan|kill|lifecycle|zombie|stuck|indefinite|process[- ]group|cleanup|terminate|wait",
      "remote-code-pinning": r"pin|curl|wget|\| *(ba)?sh|remote|download|unverified|checksum|integrity|signature|digest|hash|unpinned|latest|clone|fetch",
      "url-scheme-network": r"url|scheme|http|network|xdg-open|redirect|host|https?:|socket|request|domain|port",
      "rich-text-markup-injection": r"rich ?text|markup|html|textFormat|inject|escape|StyledText|MarkdownText|StyledText|sanitiz|untrusted|\bformat",
      "shell-lua-injection": r"inject|sh -c|bash -c|quot|escap|interpolat|eval|shell|argv|command[- ]line|concatenat|lua|argument",
      "user-config-modification": r"config|overwrit|modif|dotfile|settings|\.json|writes?|edit",
      "listing-metadata-docs": r"manifest|readme|metadata|listing|docs?\b|license|description|screenshot",
      "runtime-qml-api-compat": r"qml|api|deprecated|compat|property|signal|import"}
SPAN = re.compile(r"`([^`\n]{3,100})`")
FILE_RE = r"[\w./@+-]+\.(?:qml|js|mjs|sh|py|lua|json|bash|conf|toml|md|css|service|desktop|txt)"
def construct_near_line(finding, text, line, win=8):
    """a backticked identifier/command from the finding (not a bare file ref) occurs within +-win lines of the cited line"""
    L = text.split("\n"); w = "\n".join(L[max(0, line - 1 - win): line + win])
    for m in SPAN.finditer(finding):
        sp = m.group(1).strip()
        if re.fullmatch(FILE_RE + r"(:\d+(-\d+)?)?", sp) or re.fullmatch(r"[:,\d\- ]+", sp): continue
        for c in {sp, re.split(r"[( ]", sp)[0], re.split(r"[=\s]", sp)[0].strip("$-"), sp.rstrip(".")}:
            if len(c) >= 4 and c in w: return True
    return False

STRONG = {"file-safety-symlink-perms": r"symlink|predictable|world-?writable|/tmp/|mktemp|\bchmod|umask|0[67][0-7]{2}\b|redirect(s|ion)? .*(follow|truncat)|truncat|atomic",
          "remote-code-pinning": r"unpinned|not pinned|without pinn|mutable|default branch|git clone|clone |pinned (version|digest|commit|hash)|mutable (main|branch|tag)|curl [^`]*\|\s*(ba)?sh|checksum|integrity|signature|\bpip3? install|npm install|git clone|latest\b|downloads? .*(execut|install|run)",
          "rich-text-markup-injection": r"textformat|rich-?text|markup|plaintext|styledtext|autotext|html|markdown",
          "unbounded-input-resource": r"byte limit|exhaust|producer-side|unbounded|uncapped|size cap|byte cap|no (size |byte |line |max )?(cap|limit|bound)|without (a )?(size |byte )?(cap|limit|bound)|complete (output|stdout|file|response)|entire (output|stdout|file|response)|max[_ ]?bytes|collects? .*(output|stdout)|reads? .*whole",
          "secrets-credentials": r"secret|credential|password|api[ _-]?key|bearer|\btoken|keyring|cookie|authorization",
          "process-lifecycle-timeouts": r"timeout|deadline|\bkill|\bpid\b|hang|orphan|zombie|process[- ]group|indefinite|never (exit|terminat|return)",
          "privileged-system": r"sudo|pkexec|polkit|setuid|/etc/|systemctl|udev|root\b|privilege",
          "shell-lua-injection": r"inject|concatenat|interpolat|escap(e|ing)|shell command|sh -c|bash -c|eval\b|unquoted|quoting",
          "url-scheme-network": r"url scheme|scheme|xdg-open|\bhttps?://|redirect(s)? to|ssrf|\bhost\b|plain http|tls",
          "install-deps-packaging": r"install\.sh|installer|rm -rf|dependenc|packag|aur\b|pacman|marker",
          "user-config-modification": r"~/\.config|user config|dotfile|settings file|hyprland\.conf|overwrit(es|ing) (the )?(user|existing)",
          "listing-metadata-docs": r"manifest\.json|readme|listing|license",
          "runtime-qml-api-compat": r"deprecated|incompatib"}
KIND_PRIO = ["file-safety-symlink-perms", "remote-code-pinning", "rich-text-markup-injection", "unbounded-input-resource", "secrets-credentials", "process-lifecycle-timeouts", "privileged-system", "shell-lua-injection", "url-scheme-network", "install-deps-packaging", "user-config-modification", "listing-metadata-docs", "runtime-qml-api-compat"]
RELABEL_OK = set(KIND_PRIO[:9])   # loose kinds (install/config/listing/compat) are never relabel targets
def settle_kind(kind, f):
    """keep the labeled kind when the finding text strongly supports it; else relabel to the single strongest-supported other kind; else None"""
    if re.search(STRONG[kind], f, re.I): return kind, False
    hits = [k for k in KIND_PRIO if k in RELABEL_OK and re.search(STRONG[k], f, re.I)]
    # prefer the kind whose pattern matches earliest in the text
    if not hits: return None, False
    best = min(hits, key=lambda k: re.search(STRONG[k], f, re.I).start())
    return best, True
def quality_ok(r, f, text):
    if NEG.search(f): return "negative_prose"
    k, rel = settle_kind(r["bug_kind"], f)
    if k is None: return "kind_text_mismatch"
    r["orig_kind"] = r["bug_kind"]; r["bug_kind"] = k; r["relabeled"] = rel
    if not construct_near_line(f, text, r["line"]): return "construct_not_near_line"
    return None

# ---------- plugin code / prompt blob ----------
def v3_blob(files, cited):
    """manifest first, then the cited files (cap extended so the cited line is visible), then v2 order; same '### path' + fenced layout as v2"""
    order = lambda p: (0 if p == "manifest.json" else 1 if p in cited else 2 if p.endswith((".qml", ".js", ".sh", ".py", ".lua", ".bash")) else 3 if p.lower().startswith("readme") else 4, p)
    out, n, shown = [], 0, {}
    for p in sorted(files, key=order):
        cap = max(FILE_CAP, min(CITED_CAP, cited.get(p, 0))) if p in cited else FILE_CAP
        c = files[p][:cap]
        if n + len(c) > CODE_CAP and p not in cited and p != "manifest.json": out.append(f"### {p}\n(omitted: {len(files[p])} chars)"); continue
        out.append(f"### {p}\n```\n{c}\n```"); n += len(c); shown[p] = c
    return "\n\n".join(out), shown
CACHE = "/workspace/hancore_cache"
SRC = {n.lower(): os.path.join(CACHE, n) for n in os.listdir(CACHE) if os.path.exists(os.path.join(CACHE, n, ".ok"))}
SRC.update({n.lower(): os.path.join(HL, "src_full", n) for n in os.listdir(os.path.join(HL, "src_full"))})   # full trees win
def derive_line(r, files):
    """medium rows have no line: locate the first quoted code span (>=6 chars, not a file name) that occurs exactly once in the cited file"""
    t = files.get(r["file"])
    if t is None: return None
    for m in CODE_TOK.finditer(r["prose"]):
        sp = m.group(1).strip()
        if len(sp) < 6 or re.fullmatch(r"[\w./@+-]+\.(qml|js|mjs|sh|py|lua|json|bash|conf|toml)(:\d+(-\d+)?)?", sp) or t.count(sp) != 1: continue
        return t[:t.index(sp)].count("\n") + 1
    return None
def make_hancore_row(args):
    """worker: build prompt for one (plugin, commit) group. returns dict or dict(drop=reason)"""
    key, recs = args
    import functest, checker_report
    from build_reviewer_scrub import scrub
    d = SRC.get((recs[0]["plugin"].replace("/", "__") + "@" + recs[0]["commit"]).lower())
    if not d: return dict(drop="no_src_dir", key=key)
    files = {p: c for p, c in functest.read_dir(d).items() if p not in checker_report.HARNESS_FILES}
    if not files: return dict(drop="empty_src", key=key)
    # findings
    cands = []; qdrops = collections.Counter()
    for r in recs:
        r = dict(r)
        if r["file"] not in files: continue
        if not r["line"]:
            r["line"] = derive_line(r, files); r["line_derived"] = True
            if not r["line"]: continue
        lines = files[r["file"]].split("\n")
        if r["line"] > len(lines): continue
        f = build_finding(r, scrub)
        if not f: continue
        qr = quality_ok(r, f, files[r["file"]])
        if qr: qdrops[qr] += 1; continue
        cands.append((r, f))
    if not cands: return dict(drop="no_usable_prose_or_file" + ("/" + qdrops.most_common(1)[0][0] if qdrops else ""), key=key, qdrops=dict(qdrops))
    # pick up to MAX_FINDINGS: high first, distinct kind first, distinct (file,line)
    cands.sort(key=lambda x: (x[0]["confidence"] != "high", x[0]["verify"] != "quoted_code_near_line", x[0]["line"]))
    sel, kinds, seen = [], set(), set()
    for r, f in cands:
        if (r["file"], r["line"]) in seen: continue
        if r["bug_kind"] in kinds and len(sel) < MAX_FINDINGS and any(k not in kinds for k in {x[0]["bug_kind"] for x in cands}): continue
        sel.append((r, f)); kinds.add(r["bug_kind"]); seen.add((r["file"], r["line"]))
        if len(sel) == MAX_FINDINGS: break
    cited = {}
    for r, f in sel:
        off = sum(len(x) + 1 for x in files[r["file"]].split("\n")[:r["line"] + 25]); cited[r["file"]] = max(cited.get(r["file"], 0), off)
    blob, shown = v3_blob(files, cited)
    blob = scrub(blob)
    fl = []
    for r, f in sel:
        sh = shown.get(r["file"])
        if sh is None or len(sh.split("\n")) < r["line"] or len(files[r["file"]][:len(sh)].split("\n")) != len(scrub(sh).split("\n")): continue   # cited line must be visible and unshifted by scrub
        fl.append(dict(category=r["bug_kind"], severity="blocker", file=r["file"], line=int(r["line"]), finding=f))
    if not fl: return dict(drop="cited_line_not_visible", key=key)
    srcorigin = "src_full" if "src_full" in d else "hancore_cache_partial_tree"
    rep = checker_report.report(files)
    rep = [scrub(x) for x in rep] if rep is not None else None
    target = dict(verdict="changes_requested", load="unsure", findings=fl)
    return dict(key=key, srcorigin=srcorigin, blob=blob, rep=rep, target=target, fh=sorted(B.file_hashes(files)), mid=B.manifest_id(files), recs=[dict(bug_kind=r["bug_kind"], confidence=r["confidence"], verify=r["verify"], line_derived=bool(r.get("line_derived")), kind_relabeled=bool(r.get("relabeled")), orig_kind=r.get("orig_kind"), comment_url=r["comment_url"], file=r["file"], line=r["line"]) for r, _ in sel], low=any(r["confidence"] == "low" for r, _ in sel))

def v2_user_files(m):
    """parse '### path ```code```' blocks from the last user message of a v2 row"""
    u = m["messages"][-2]["content"] if m["messages"][-1]["role"] == "assistant" else m["messages"][-1]["content"]
    return {mm.group(1): mm.group(2) for mm in re.finditer(r"^### (.+?)\n```\n(.*?)\n```$", u, re.S | re.M)}, u
def cites_ok(files, tgt):
    for f in tgt["findings"]:
        if f.get("severity") != "blocker": continue
        fn = f.get("file"); ln = f.get("line")
        if not fn or not isinstance(ln, int): return False
        hit = [p for p in files if p == fn or p.endswith("/" + fn)]
        if not hit or ln > max(files[p].count("\n") + 1 for p in hit): return False
    return True

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="/workspace/usuba-runs/v3-data"); ap.add_argument("--limit", type=int, default=0); a = ap.parse_args()
    rnd = random.Random(1337); st = collections.Counter(); drops = collections.Counter(); os.makedirs(a.out, exist_ok=True)
    # ---- exclusion fingerprints ----
    h_repos, h_ids, h_trees = B.holdout_fingerprint()
    key_ids, key_trees = set(), []
    for l in open(os.path.join(ROOT, "functest", "dell_ground_truth.jsonl")):
        k = json.loads(l); key_ids.add(k["id"].lower())
        p = os.path.join(ROOT, k.get("path") or "")
        if k.get("path") and os.path.isdir(p):
            import functest as FT
            fh = B.file_hashes(FT.read_dir(p))
            if fh: key_trees.append(fh)
    key_tails = {i.split(".")[-1] for i in key_ids if len(i.split(".")[-1]) >= 8}
    excl_json = json.load(open(HL + "excluded_plugins.json"))
    excl_repos = {B.norm_repo(u) for u in excl_json}
    def excluded(repo, mid, fh):
        if repo in h_repos or repo in excl_repos: return "holdout_or_dellkey_repo"
        if mid and mid.lower() in h_ids: return "holdout_manifest_id"
        if mid and mid.lower() in key_ids: return "dellkey_manifest_id"
        if B.near_dup(fh, h_trees): return "holdout_near_dup"
        if B.near_dup(fh, key_trees): return "dellkey_near_dup"
        if repo.split("/")[-1].split(".")[-1] in key_tails and len(repo.split("/")[-1]) >= 8 and repo.split("/")[-1] in {i.split(".")[-1] for i in key_ids}: return "dellkey_repo_name"
        return None
    rows = []   # unified: dict(id, source, repo, label, verdict, messages, tokens, provenance, target_kind, fh, mid, extra)
    # ---- (a) HANCORE ----
    R = [json.loads(l) for l in open(HL + "concrete_findings.jsonl")]
    st["hancore_findings_total"] = len(R)
    pool = [r for r in R if r["confidence"] in ("high", "medium")]
    st["hancore_findings_high_medium"] = len(pool)
    groups = collections.defaultdict(list)
    for r in pool: groups[(r["plugin"], r["commit"])].append(r)
    st["hancore_groups"] = len(groups)
    low_pool = collections.defaultdict(list)
    for r in R:
        if r["confidence"] == "low" and r["line"]: low_pool[(r["plugin"], r["commit"])].append(r)
    lowkeys = rnd.sample(sorted(k for k in low_pool if k not in groups), 40)
    jobs = list(groups.items()) + [(k, low_pool[k]) for k in lowkeys]
    if a.limit: jobs = jobs[:a.limit]
    hres = []
    with ProcessPoolExecutor(8) as ex:
        for out in ex.map(make_hancore_row, jobs, chunksize=4): hres.append(out)
    low_examples = []
    for (key, recs), out in zip(jobs, hres):
        if "drop" in out: drops["hancore:" + out["drop"]] += 1; continue
        repo = B.norm_repo(key[0]); fh = set(out["fh"])
        why = excluded(repo, out["mid"], fh)
        if why: drops["hancore:excl:" + why] += 1; continue
        msgs = P.messages(out["blob"], out["rep"], out["target"]); tk = ntok(json.dumps(msgs))
        rec = dict(id=f"hancore_concrete:{repo}:{key[1][:10]}", source="hancore_concrete", repo=repo, label="broken", verdict="changes_requested", messages=msgs, tokens=tk,
                   target_kind="hancore_concrete", provenance=dict(kind="hancore-concrete-verified", commit=key[1], source_tree=out["srcorigin"], findings=out["recs"], comment_urls=sorted({x["comment_url"] for x in out["recs"]})[:5]), fh=fh, mid=out["mid"])
        if out["low"]: rec["source"] = "hancore_low_sample"; low_examples.append(rec); continue
        if tk > MAX_TOK: drops["hancore:over_token_cap"] += 1; continue
        rows.append(rec)
    # ---- (b,c,d) v2 rows ----
    v2 = []
    for fn in ("train.jsonl.gz", "val.jsonl.gz"): v2 += [json.loads(l) for l in gzip.open(STORE + "final/" + fn, "rt")]
    st["v2_rows_read"] = len(v2)
    for m in v2:
        if m["source"] not in KEEP_V2: drops["v2:source_not_used:" + m["source"]] += 1; continue
        tgt = json.loads(m["messages"][-1]["content"]); files, u = v2_user_files(m)
        repo = B.norm_repo(m["id"].split(":", 1)[1].rsplit(":", 1)[0]) if ":" in m["id"] else ""
        if m["verdict"] == "changes_requested":
            if not cites_ok(files, tgt): drops["v2:broken_no_file_line_or_cite_invalid:" + m["source"]] += 1; continue
            if any(BAD_WORDS.search(f["finding"]) for f in tgt["findings"]): drops["v2:bad_words"] += 1; continue
        fh = {hashlib.sha1(re.sub(r"\s+", "", c).encode()).hexdigest() for p, c in files.items() if not p.lower().startswith(("readme", "license")) and c.strip()}
        mid = B.manifest_id({"manifest.json": files.get("manifest.json", "")})
        rows.append(dict(id=m["id"], source=m["source"], repo=repo, label=m["label"], verdict=m["verdict"], messages=P.rebuild(m["messages"]), tokens=m["tokens"], target_kind=m["target_kind"], provenance=m["provenance"], fh=fh, mid=mid))
    # ---- v3 pass: hygiene filter on findings (drop a finding that cites URLs / earlier reviews; drop the row if no blocker is left), recount tokens with prompt_v3 ----
    rows2 = []
    for r in rows:
        tgt = json.loads(r["messages"][-1]["content"]); n0 = len(tgt["findings"])
        if n0:
            tgt["findings"] = [f for f in tgt["findings"] if not HYG.search(f["finding"]) and not (r["source"] == "hancore_concrete" and HYG_URL.search(f["finding"]))]
            if len(tgt["findings"]) < n0: st["hyg_findings_dropped"] += n0 - len(tgt["findings"])
            if r["verdict"] == "changes_requested" and not any(f["severity"] == "blocker" for f in tgt["findings"]): drops["v3:hygiene_no_blocker_left:" + r["source"]] += 1; continue
            if len(tgt["findings"]) < n0: r["messages"] = r["messages"][:-1] + [{"role": "assistant", "content": json.dumps(tgt, ensure_ascii=False)}]
        r["tokens"] = ntok(json.dumps(r["messages"]))
        if r["tokens"] > MAX_TOK: drops["v3:over_token_cap:" + r["source"]] += 1; continue
        rows2.append(r)
    rows = rows2
    # ---- exclusion on v2-derived rows + dedupe ----
    kept = []
    for r in rows:
        if not r["id"].startswith("hancore_concrete"):
            why = excluded(r["repo"], r["mid"], r["fh"])
            if why: drops["v2:excl:" + why] += 1; continue
        kept.append(r)
    # near-dup dedupe: broken rows first (hancore, then dell broken), then approve; later row dropped if >=50% min-overlap with an earlier kept row
    prio = {"hancore_concrete": 0, "dell_broken_verified": 1, "dell_inuse_close": 1, "dell_inuse_missing_binary": 1, "fix_upstream": 3, "dell_works_verified": 2, "nudged_approve": 2}
    kept.sort(key=lambda r: (prio[r["source"]], r["id"]))
    final, idx = [], collections.defaultdict(list)   # inverted index file-hash -> row positions
    for r in kept:
        cand = collections.Counter()
        for h in r["fh"]:
            for j in idx[h]: cand[j] += 1
        dup = next((j for j, n in cand.items() if n / max(1, min(len(r["fh"]), len(final[j]["fh"]))) >= 0.5), None) if r["fh"] else None
        if dup is not None:
            drops[f"dedupe_near_dup:{r['source']}_vs_{final[dup]['source']}"] += 1; continue
        final.append(r)
        for h in r["fh"]: idx[h].append(len(final) - 1)
    # ---- caps: unbounded-input share ----
    broken = [r for r in final if r["verdict"] == "changes_requested"]; approve = [r for r in final if r["verdict"] == "approve"]
    def kinds(r): return {f["category"] for f in json.loads(r["messages"][-1]["content"])["findings"]}
    ub = [r for r in broken if r["source"] == "hancore_concrete" and kinds(r) == {"unbounded-input-resource"}]
    cap_ub = int(UNBOUNDED_CAP_SHARE * len(broken))
    if len(ub) > cap_ub:
        rnd.shuffle(ub); drop = {r["id"] for r in ub[cap_ub:]}; drops["cap:unbounded_only_rows"] += len(drop)
        final = [r for r in final if r["id"] not in drop]; broken = [r for r in final if r["verdict"] == "changes_requested"]; approve = [r for r in final if r["verdict"] == "approve"]
    # ---- approve mix: target 40-50%; trim approve to <=50% (broken kept whole) ----
    max_app = int(len(broken) * 0.9)
    if len(approve) > max_app:
        # keep fix_upstream and nudged first (small, informative), then random works
        approve.sort(key=lambda r: (prio[r["source"]] != 3, rnd.random())); drops["cap:approve_trim_to_50pct"] += len(approve) - max_app
        approve = approve[:max_app]
    final = broken + approve
    # ---- split by repo (3% val repos, deterministic) ----
    byrepo = collections.defaultdict(list)
    for r in final: byrepo[r["repo"]].append(r)
    repos = sorted(byrepo); rnd.shuffle(repos); val_repos = set(repos[:max(1, int(len(repos) * 0.04))])
    out = {"train": [], "val": []}
    rnd.shuffle(final)
    for r in final:
        sp = "val" if r["repo"] in val_repos else "train"
        rec = dict(id=r["id"], split=sp, source=r["source"], orig_source=r["source"], label=r["label"], verdict=r["verdict"], target_kind=r["target_kind"], reject_reason=None,
                   is_pair_parent=False, pair=None, tokens=r["tokens"], provenance=r["provenance"], weight=1.0, messages=r["messages"])
        out[sp].append(rec)
    for sp in out:
        with gzip.open(os.path.join(a.out, f"{sp}.jsonl.gz"), "wt") as f:
            for rec in out[sp]: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    # low-confidence sample (NOT in train)
    with open(os.path.join(a.out, "low_confidence_sample.jsonl"), "w") as f:
        for r in low_examples[:40]: f.write(json.dumps(dict(id=r["id"], provenance=r["provenance"], tokens=r["tokens"], messages=r["messages"]), ensure_ascii=False) + "\n")
    json.dump(dict(stats=dict(st), drops=dict(drops), val_repos=sorted(val_repos), key_ids_n=len(key_ids), key_trees_n=len(key_trees), holdout_repos_n=len(h_repos), holdout_trees_n=len(h_trees), holdout_ids_n=len(h_ids)),
              open(os.path.join(a.out, "build_stats.json"), "w"), indent=1)
    # keep fingerprints for the independent leakage check
    print(json.dumps(dict(st), indent=1), json.dumps(dict(drops), indent=1), len(out["train"]), len(out["val"]))
if __name__ == "__main__": main()
