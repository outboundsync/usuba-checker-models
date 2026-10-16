#!/usr/bin/env python3
"""r6 data in the scope-v4 format (docs/SCOPE_DATA_BUILDER_SPEC.md): triage rows, added-finding (extend) rows and clean rows. NO fix/patch rows (scope trim, Harris 2026-10-15).
No training, no GPU, open-weights teachers only (llm_client, fail closed). Every row: messages = scope.prompt_scope.messages(code, REAL Checker report, target); hard asserts at build time.

Tiers: `verified` = every triage label rests on a spec basis (reviewer finding / verified upstream fix location / hardware-works fail-level / hardware-works + empty report). Default train set.
       `provisional` = some triage items were adjudicated by two open-weights teachers that agree and quote exactly (meta.provisional=true; written to a SEPARATE file, never in the default set).
Extend rows come from the HANCORE concrete pool, rebuilt from concrete_findings.jsonl (not from the r3 rows): funnel counters per slug in build_stats.json.
Attribution: strict plurality-ok + commit match, OR (R6S_RELAX_TIES=1, default) the finding is `quoted_code_near_line` verified at the very tree shown (the quote exists at that line at that SHA, so
the plurality rule's purpose - code shown == code reviewed - is met mechanically). R6S_RELAX_TIES=0 gives strict only.
usage: build_scope.py WORKDIR OUTDIR [--stage units|render|llm|assemble|all]"""
import sys, os, re, json, gzip, random, collections, hashlib, time, argparse, pickle
from concurrent.futures import ThreadPoolExecutor
H = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(H); M = os.path.dirname(T)
sys.path[:0] = [M, T, H]
import paths, code_blob as CB, holdout_guard as HG, llm_client as LC, exactline as X
import label_filters as LF
import checker_report as CR
import functest as FT
from scope import schema as S, prompt_scope as PS, postfilter as PF, checker_findings as CF
from build_reviewer_scrub import scrub

ap = argparse.ArgumentParser(); ap.add_argument("work"); ap.add_argument("out"); ap.add_argument("--stage", default="all"); ap.add_argument("--limit", type=int, default=0)
A = ap.parse_args() if __name__ == "__main__" else ap.parse_args([sys.argv[1] if len(sys.argv) > 1 else ".", sys.argv[2] if len(sys.argv) > 2 else "."])
W, OUT = A.work, A.out; os.makedirs(W, exist_ok=True); os.makedirs(OUT, exist_ok=True)
E = os.environ.get
RELAX = int(E("R6S_RELAX_TIES", "1")); LOCATE = E("R6S_LOCATE_FILE_LEVEL", "1") == "1"; PROV_MAX_ITEMS = int(E("R6S_PROV_MAX_ITEMS", "500")); PROV_MAX_UNLAB = int(E("R6S_PROV_MAX_UNLABELLED", "3")); PROV_MAX_UNLAB_EXT = int(E("R6S_PROV_MAX_UNLABELLED_EXT", "12"))
POOL = E("R6S_POOL", "/workspace/r6/work/pool.pkl"); FIND = E("R6S_FINDINGS", "/workspace/r6/scope/findings_pool.json")
HL = E("HANCORE_LABELS", "/workspace/usuba-runs/hancore-labels/"); FX = E("V3FIXES", "/workspace/usuba-runs/v3-fixes/"); WT = E("USUBA_MONO", "/workspace/wt-retrain-v2")
CACHE_DIR = E("HANCORE_CACHE", "/workspace/hancore_cache"); DRAFTS = E("SCOPE_DRAFTS", "/workspace/usuba-runs/scope-v4/drafts")
FOCUS = set(S.ADDED_CATEGORIES)
# a Checker scripts rule that already covers an added-finding category on the same file: the added finding is NOT added (spec section 2 dedup); the reviewer evidence then confirms that Checker finding
FAMILY = {"remote-code-pinning": {"USB-W03", "USB-HC17", "USB-HC19"}, "secrets-credentials": {"USB-W02", "USB-HC08", "USB-HC09", "USB-H07"},
          "url-scheme-network": {"USB-W09", "USB-HC10", "USB-HC20", "USB-HC25"}, "rich-text-markup-injection": {"USB-W06"}, "listing-metadata-docs": {"USB-HC16"}}
HARNESS = set(CR.HARNESS_FILES) | {".ok", ".fail", ".done"}
BANNED_FIND = re.compile(r"reviewer|\bhancore|\bsealed|ground.?truth|\bissue #", re.I)
BANNED = re.compile(r"hardware|\bdell\b|\bkey\b|ground.?truth|\blabel|upstream|\bcommit|reviewer|sweep|\bhancore|\bsealed", re.I)
st = collections.Counter(); drops = collections.Counter(); funnel = collections.defaultdict(collections.Counter)
norm_repo = lambda s: s.lower().rstrip("/").removesuffix(".git").split("github.com/")[-1]
ws_hash = lambda t: hashlib.sha1(re.sub(r"\s+", "", t).encode()).hexdigest()
def pk(name): return os.path.join(W, name)
def save(name, o): pickle.dump(o, open(pk(name), "wb"))
def load(name): return pickle.load(open(pk(name), "rb"))
def line_text(files, f, l):
    t = files.get(f)
    if t is None or not isinstance(l, int) or l < 1: return None
    ls = t.split("\n"); return ls[l - 1] if l <= len(ls) else None
def good_quote(s): return s is not None and len(re.sub(r"\s", "", s)) >= PF.MIN_QUOTE


# ------------------------------------------------------------------ stage 1: units (candidates + evidence, no file content yet)
def s4_repos():
    out = set()
    for fn in ("S4_EXCLUDE_REPOS.txt", "allkinds_S4_EXCLUDE_REPOS.txt"):
        p = os.path.join(DRAFTS, fn)
        if os.path.exists(p): out |= {norm_repo(l.strip()) for l in open(p) if l.strip()}
    return out


def match_ev(f, ev, dell):
    """a Checker finding is `matched` by evidence at the same file and within 3 lines (dell hardware notes may be file-level: line 0 matches same file)"""
    for e in ev:
        if e["file"] != f["file"]: continue
        if f["line"] and isinstance(e.get("line"), int) and abs(e["line"] - f["line"]) <= 3: return e
        if not f["line"] and dell and not isinstance(e.get("line"), int): return e
        if not f["line"] and dell: return e
    return None


def build_units():
    P = pickle.load(open(POOL, "rb")); F = json.load(open(FIND)); ex = s4_repos(); units = []
    keep_src = {"version_history", "dell_broken_verified", "dell_inuse_close", "dell_inuse_missing_binary", "dell_works_verified", "nudged_approve", "hancore_clean_approve"}
    for r in P:
        s = r["source"]; drops_key = "pool:" + s
        if s not in keep_src:
            drops["pool:source_not_in_scope_spec:" + s] += 1; continue
        if s == "version_history" and not r["id"].endswith(":broken"): drops["pool:history_fixed_twin_not_a_clean_row"] += 1; continue
        pv = r["prov"] or {}; repo = norm_repo(pv.get("repo") or pv.get("dell_job", "").replace("__", "/") or "")
        if repo in ex: drops["pool:s4_eval_repo"] += 1; continue
        fs = F.get(r["id"])
        if not isinstance(fs, list): drops["pool:checker_unavailable"] += 1; continue
        ev = [dict(file=f["file"], line=f.get("line"), text=f["finding"], kind=f["category"], basis=("verified upstream fix changed this location" if s == "version_history" else
              "hardware-observed break with the Checker FAIL; the sweep note names this location")) for f in r["target"]["findings"] if f.get("file")] if r["verdict"] != "approve" else []
        units.append(dict(id=r["id"], source=s, repo=repo, commit=pv.get("commit"), spec=r["spec"], origin=r["origin"], prov=pv, findings_cached=fs, evidence=ev, verdict0=r["verdict"], extend=[], weight=r.get("weight", 1.0)))
    units += build_concrete()
    st["units"] = len(units); return units


def build_concrete():
    sys.path.insert(0, os.path.join(paths.checker_root(), "hancore")); import common as HC
    HC.REV = os.path.join(WT, "dell/sweep/hancore_reviews.jsonl")
    STRICT = LF.plurality_table(HC); RET = LF.retraction_ids(json.load(open(FX + "retraction_list.json")))
    RET = {x.lower() for x in RET}; ex = s4_repos()
    SRC = {n.lower(): os.path.join(CACHE_DIR, n) for n in os.listdir(CACHE_DIR) if os.path.exists(os.path.join(CACHE_DIR, n, ".ok"))}
    SRC.update({n.lower(): os.path.join(HL, "src_full", n) for n in os.listdir(os.path.join(HL, "src_full"))})
    groups = collections.OrderedDict()
    allr = [json.loads(l) for l in open(HL + "concrete_findings.jsonl")]
    if LOCATE: allr += [dict(json.loads(l), line=None) for l in open(HL + "file_level_only.jsonl")]
    seen_fl = set()
    for r in allr:
        k = r["bug_kind"]; c = funnel[k]; c["raw"] += 1
        if r["strength"] not in ("strong", "likely"): c["f1_weak_strength"] += 1; continue
        if not isinstance(r["line"], int):
            kk = (r["plugin"], r["commit"], r["file"], r["prose"][:80])
            if not LOCATE or k not in FOCUS or kk in seen_fl: c["f2_no_line_number"] += 1; continue
            seen_fl.add(kk); r["_locate"] = True; c["f2_file_level_to_locate"] += 1
        if norm_repo(r["plugin"]) in ex: c["f3_s4_repo"] += 1; continue
        rid = f"hancore_concrete:{r['plugin']}:{r['commit'][:10]}".lower()
        if rid in RET: c["f3_retracted"] += 1; continue
        stt = STRICT.get(r["plugin_url"].lower().replace("http://", "https://")); strict_ok = bool(stt and stt["status"] == "ok" and stt["sha"] and stt["sha"].startswith(r["commit"][:10]))
        relaxed_ok = (RELAX >= 1 and r["verify"] == "quoted_code_near_line") or RELAX >= 2
        if not strict_ok and not relaxed_ok:
            c["f4_attribution:" + (stt["status"] if stt else "not_in_reviews") + ("" if not RELAX else "+not_quoted_verified")] += 1; continue
        c["f4_pass_strict" if strict_ok else "f4_pass_relaxed_quoted_verified"] += 1
        d = SRC.get((r["plugin"].replace("/", "__") + "@" + r["commit"]).lower())
        if not d: c["f5_no_source_tree"] += 1; continue
        r["_strict"] = strict_ok
        groups.setdefault((r["plugin"], r["commit"]), dict(dir=d, items=[], strict=strict_ok))["items"].append(r)
    units = []
    for (pl, cm), g in groups.items():
        units.append(dict(id=f"hancore_concrete:{pl}:{cm[:10]}", source="hancore_concrete", repo=norm_repo(pl), commit=cm, spec=dict(dir=g["dir"]), origin="hancore_cache", prov=dict(kind="hancore-concrete-verified", repo=norm_repo(pl), commit=cm, license="see repo (public plugin)"),
                          findings_cached=None, evidence=[], verdict0="changes_requested", extend=g["items"], weight=1.0))
    # review-clean HANCORE approves (reviewed plugin, approved/listed, no strong/likely/open finding, source at the reviewed commit)
    excl = {norm_repo(u) for u in json.load(open(HL + "excluded_plugins.json"))}
    return units


# ------------------------------------------------------------------ stage 2: files, REAL Checker report, evidence labels
def read_files(spec):
    files = dict(spec["files"]) if "files" in spec else (FT.read_dir(spec["dir"]) if os.path.isdir(spec["dir"]) else {})
    files = {p: t for p, t in files.items() if p not in HARNESS and os.path.basename(p) not in HARNESS}
    sf = {}
    for p, t in files.items():
        s = scrub(CB.norm_newlines(t))
        if s.count("\n") != CB.norm_newlines(t).count("\n"): return None, None
        sf[p] = s
    return sf, files


def _render_one(u):
    sf, raw = read_files(u["spec"])
    if not sf: return u["id"], None, None, None
    fs = u["findings_cached"] if u["findings_cached"] is not None else CF.findings_for(sf)
    return u["id"], sf, raw, fs


def stage_render(units):
    from multiprocessing import Pool
    t0 = time.time(); pre = []
    for u in units:     # cheap prefilter on the cached Checker report: skip units that cannot become a row in either tier
        fs = u["findings_cached"]
        if fs is not None:
            dell = u["source"].startswith("dell"); n_un = sum(1 for f in fs if not match_ev(f, u["evidence"], dell) and not (f["level"] == "fail" and u["source"] == "dell_works_verified"))
            n_lab = len(fs) - n_un
            if (not fs and u["source"] not in ("dell_works_verified", "nudged_approve", "hancore_clean_approve")) or n_un > PROV_MAX_UNLAB or (n_un and not n_lab and u["source"] not in ("dell_works_verified", "nudged_approve", "hancore_clean_approve")):
                drops["prefilter:cannot_become_a_row:" + u["source"]] += 1; continue
        pre.append(u)
    units = pre
    with Pool(6, maxtasksperchild=40) as mp: res = mp.map(_render_one, units, chunksize=4)
    R = {i: (sf, raw, fs) for i, sf, raw, fs in res}; out = []
    for u in units:
        sf, raw, fs = R[u["id"]]
        if not sf: drops["render:empty_or_scrub_shifts_lines"] += 1; continue
        if fs is None: drops["render:checker_unavailable_or_timeout"] += 1; continue
        blob, info = CB.render(sf)
        out.append(dict(u, files=sf, raw_files=raw, blob=blob, info=info, findings=fs))
    print(f"render {len(units)} -> {len(out)} in {time.time() - t0:.0f}s", flush=True)
    return out


LOC_RE = {"USB-W10": r"StdioCollector|SplitParser|FileView|readAll|\$\(|\bcat |\bread |\.text\b", "USB-W08": r"\bcurl\b|\bwget\b"}
def locate(f, files):
    """line of a file-level Checker finding (report line 0), for the window and the quote only (the target still echoes the report's line): first non-comment line holding a backticked token of the message, else the rule's construct"""
    t = files.get(f["file"])
    if f["line"] or t is None: return f["line"] or 0
    ls = t.split("\n"); toks = re.findall(r"`([^`\n]{3,80})`", f["message"])
    for tk in toks:
        for i, l in enumerate(ls):
            if tk in l and not X.is_comment(f["file"], l) and good_quote(l): return i + 1
    rx = LOC_RE.get(f["rule"])
    if rx:
        for i, l in enumerate(ls):
            if re.search(rx, l) and not X.is_comment(f["file"], l) and good_quote(l): return i + 1
    return 0


LOC_SYS = """You locate where a code-review finding applies inside one source file. You get the finding and the numbered file. Reply JSON only: {"line": <int>|null, "why": "<short>"}.
`line` = the number of the single line that holds the exact statement the finding describes (the call, assignment, literal or command). null when the file does not contain that statement or it is not visible."""
def locate_one(job):
    u, r = job; t = u["files"].get(r["file"])
    if t is None: return None, None
    ls = t.split("\n"); n = 0; out = []
    for i, l in enumerate(ls):
        n += len(l) + 1
        if n > CB.FILE_CAP: break
        out.append(f"{i + 1:5d}| {l[:220]}")
    user = f"CATEGORY: {r['bug_kind']}\nFINDING: {r['prose'][:1000]}\n\nFILE {r['file']}:\n" + "\n".join(out)
    return LC.call(LOC_SYS, user, tag="r6s_locate_qwen", max_tokens=300), LC.call(LOC_SYS, user, tag="r6s_locate_gptoss", model=LC.GPT, effort="low", max_tokens=1500)


def locate_all(units):
    jobs = [(u, r) for u in units for r in u["extend"] if r.get("_locate")]
    with ThreadPoolExecutor(12) as ex: res = list(ex.map(locate_one, jobs))
    LC.assert_error_budget(); keep = {}
    for (u, r), (a, b) in zip(jobs, res):
        c = funnel[r["bug_kind"]]; L = None
        if a and b and "_error" not in a and "_error" not in b and isinstance(a.get("line"), int) and a["line"] == b.get("line") and 1 <= a["line"] <= len(u["files"][r["file"]].split("\n")): L = a["line"]
        if L is None: c["f2b_not_located_models_disagree_or_null"] += 1; r["_drop"] = True; continue
        r["line"] = L; r["line_located"] = True; c["f2b_located_both_models_agree"] += 1
    for u in units: u["extend"] = [r for r in u["extend"] if not r.get("_drop")]
    return units


def label_unit(u):
    """-> adds u['triage'] = list of dict(finding, decision|None, basis, ev) ; u['added_cands'] = verified extend candidates after dedupe against the Checker report"""
    fs, files = u["findings"], u["files"]; dell = u["source"].startswith("dell")
    ev = list(u["evidence"])
    # reviewer (HANCORE) evidence: every verified strong/likely finding location, any category, is evidence for a Checker finding at that location or in the same family on the same file
    cands = []
    for r in u["extend"]:
        ev.append(dict(file=r["file"], line=r["line"], kind=r["bug_kind"], text=r["prose"], basis="reviewer finding with exact location", cat=r["bug_kind"]))
        if r["bug_kind"] in FOCUS: cands.append(r)
    tri = []; preset = u.get("preset") or {}
    for f in fs:
        d = None; b = None; e = match_ev(f, ev, dell); pk_ = (f["rule"], f["file"], f["line"])
        if pk_ in preset and not e: d, b, e = preset[pk_]
        elif e: d, b = "confirm", e["basis"]
        else:
            for r in cands:
                if r["file"] == f["file"] and f["rule"] in FAMILY.get(r["bug_kind"], ()): d, b, e = "confirm", "reviewer finding of the same family on this file", dict(file=r["file"], line=r["line"], text=r["prose"], kind=r["bug_kind"]); break
        if d is None and f["level"] == "fail" and u["source"] == "dell_works_verified": d, b = "dismiss", "hardware-works plugin, fail-level finding"     # 0 occurrences expected: kept so the rule is executable
        tri.append(dict(f=f, decision=d, basis=b, ev=e, loc=locate(f, files)))
    u["triage"] = tri
    keep = []
    for r in cands:
        f = r["file"]; l = r["line"]
        clash = [x for x in fs if x["file"] == f and (x["line"] == l or x["rule"] in FAMILY.get(r["bug_kind"], ()))]
        if clash: funnel[r["bug_kind"]]["f9_dedup_checker_already_reports_it"] += 1; continue
        keep.append(r)
    u["added_cands"] = keep
    return u


# ------------------------------------------------------------------ stage 3: LLM steps (open-weights only, fail closed)
VSYS = """You verify citations in code-review findings for a plugin. You get a finding and the numbered source lines around the CITED line ('>' marks it).
(a) defect_stated: true if the finding describes a concrete defect or risk in this code that a reviewer would ask to have fixed; false if it describes safe or intended behaviour, confirms a fix, states scope, or is not about a defect.
(b) exact: true if the CITED line is the exact statement the finding describes: the line holding the call / assignment / command / declaration whose problem it states (a statement spanning several lines may be cited at its first line). false when the cited line is a function header or a sibling, a log or message string, a different statement, an import, a comment, a closing brace, or only nearby.
(c) better_line: if exact is false and the exact statement is visible in the window, its line number, else null.
Reply JSON only: {"defect_stated": true|false, "exact": true|false, "better_line": null|int, "why": "<one short sentence>"}"""
def vwindow(lines, L, ctx=10):
    a = max(0, L - 1 - ctx); b = min(len(lines), L + ctx)
    return "\n".join(f"{'>' if i + 1 == L else ' '}{i + 1:5d}| {lines[i][:220]}" for i in range(a, b))
def gate_one(job):
    u, r = job; lines = u["files"][r["file"]].split("\n"); L = r["line"]
    user = f"FINDING: {r['prose'][:900]}\n\nFILE: {r['file']}\n{vwindow(lines, L)}"
    q = LC.call(VSYS, user, tag="r6s_gate_qwen", max_tokens=300)
    g = LC.call(VSYS, user, tag="r6s_gate_gptoss", model=LC.GPT, effort="low", max_tokens=1500)
    return q, g


EXT_SYS = """You write one training record for a plugin security reviewer. A reviewer already found a defect at an exact line; you explain it and propose a fix.
Reply JSON only: {"finding": str, "fix": str, "severity": "blocker"|"warning"}.
finding: 1-3 plain-English sentences (<=420 chars) naming the concrete risk in THIS code. No file names beyond the one given, no URLs, no mention of reviewers, issues, commits or labels.
fix: a concrete, short edit or replacement for the quoted line (<=380 chars), advisory; must differ from the quote.
severity rubric: blocker = a secret literal; remote code executed unpinned or unverified; a write that overwrites user config without consent; markup injection of untrusted text into an interactive surface. Everything else (http instead of https, missing licence, generic id, vague metadata) = warning."""
def ext_one(job):
    u, r = job; lines = u["files"][r["file"]].split("\n")
    user = f"CATEGORY: {r['bug_kind']}\nFILE: {r['file']}  LINE: {r['line']}\nQUOTED LINE: {lines[r['line'] - 1].strip()}\nREVIEWER NOTE: {r['prose'][:900]}\n\nCODE:\n{vwindow(lines, r['line'], 8)}"
    return LC.call(EXT_SYS, user, tag="r6s_extend_teacher", max_tokens=700)


TRI_SYS = """You write one record of a Checker-report triage. A deterministic rule fired; the decision is already known and you must justify it from the code.
Reply JSON only: {"reason": str}. reason = ONE line, <=200 chars, plain English, concrete about this code (name the call, variable or guard). Do not mention how the decision was reached: never use the words hardware, Dell, key, label, commit, upstream, reviewer, sweep, ground truth."""
def tri_one(job):
    u, t = job; f = t["f"]; files = u["files"]; ln = f["line"] or t.get("loc") or (t["ev"] or {}).get("line") or 0
    lines = files[f["file"]].split("\n") if f["file"] in files else []
    win = vwindow(lines, ln) if isinstance(ln, int) and 1 <= ln <= len(lines) else "(no line)"
    why = (t["ev"] or {}).get("text") or ""
    user = f"DECISION: {t['decision']} ({'the finding is real' if t['decision'] == 'confirm' else 'the finding is a false alarm'})\nRULE {f['rule']}: {f['message'][:500]}\nFILE: {f['file']} LINE: {f['line']}\nKNOWN FACT ABOUT THE CODE: {str(why)[:500]}\n\nCODE:\n{win}"
    return LC.call(TRI_SYS, user, tag="r6s_triage_reason", max_tokens=300)


ADJ_SYS = """You triage one finding of an automatic Omarchy/Quickshell plugin checker. Decide whether it is REAL (a defect a maintainer should fix) or a FALSE_ALARM (the code is fine or the rule does not apply here).
You get the rule message and the numbered code around the cited line ('>' marks it). When the evidence is not clear, answer REAL.
Reply JSON only: {"decision": "REAL"|"FALSE_ALARM", "reason": "<one line, <=200 chars>", "quote": "<one line copied exactly from the code shown, without the number prefix>"}"""
def adj_one(job):
    u, t = job; f = t["f"]; lines = u["files"][f["file"]].split("\n"); ln = f["line"] or t["loc"]
    user = f"RULE {f['rule']} ({f['level']}): {f['message'][:500]}\nFILE: {f['file']} LINE: {ln}\n\nCODE:\n{vwindow(lines, ln)}"
    a = LC.call(ADJ_SYS, user, tag="r6s_adjudicate_qwen", max_tokens=400)
    b = LC.call(ADJ_SYS, user, tag="r6s_adjudicate_gptoss", model=LC.GPT, effort="low", max_tokens=1500)
    return a, b


def stage_llm(units):
    ex = ThreadPoolExecutor(12)
    # 1. gate every extend candidate (mechanical + qwen + gpt-oss, all must pass: exact line, defect stated)
    jobs = [(u, r) for u in units for r in u["added_cands"]
            if r["file"] in u["files"] and (lambda t: t is not None and t.strip())(line_text(u["files"], r["file"], r["line"]))]
    for u in units:
        for r in u["added_cands"]:
            if not (r["file"] in u["files"] and (line_text(u["files"], r["file"], r["line"]) or "").strip()): funnel[r["bug_kind"]]["f6_cited_line_missing_at_sha"] += 1
    res = list(ex.map(gate_one, jobs)); LC.assert_error_budget(); ok = set(); again = []
    def passes(q, g): return q.get("exact") is True and q.get("defect_stated") is not False and g.get("exact") is True and g.get("defect_stated") is not False
    for (u, r), (q, g) in zip(jobs, res):
        c = funnel[r["bug_kind"]]
        if "_error" in q or "_error" in g: c["f7_llm_error_fail_closed"] += 1; continue
        if not passes(q, g):
            bq, bg = q.get("better_line"), g.get("better_line")     # re-anchor only when BOTH models name the same better line within 8 lines, then gate again at that line
            if q.get("defect_stated") is not False and g.get("defect_stated") is not False and isinstance(bq, int) and bq == bg and 1 <= abs(bq - r["line"]) <= 8 and 1 <= bq <= len(u["files"][r["file"]].split("\n")):
                again.append((u, dict(r, line=bq, line_orig=r["line"], _orig_ref=r))); continue
            c["f7_gate_failed:" + ("qwen" if not (q.get("exact") is True and q.get("defect_stated") is not False) else "") + ("gptoss" if not (g.get("exact") is True and g.get("defect_stated") is not False) else "")] += 1; continue
        ok.add((u["id"], r["file"], r["line"], r["bug_kind"]))
    res2 = list(ex.map(gate_one, again)); LC.assert_error_budget()
    for (u, r2), (q, g) in zip(again, res2):
        c = funnel[r2["bug_kind"]]
        if "_error" in q or "_error" in g or not passes(q, g): c["f7_gate_failed_after_reanchor"] += 1; continue
        r = r2["_orig_ref"]; r["line_orig"] = r["line"]; r["line"] = r2["line"]; c["f7_reanchored_both_models_agree"] += 1; ok.add((u["id"], r["file"], r["line"], r["bug_kind"]))
    for (u, r), (q, g) in zip(jobs, res):       # the visible/quote checks run on the final line
        pass
    okf = set()
    for u in units:
        for r in u["added_cands"]:
            k = (u["id"], r["file"], r["line"], r["bug_kind"])
            if k not in ok: continue
            c = funnel[r["bug_kind"]]
            if not CB.line_visible(u["info"], r["file"], r["line"]): c["f8_not_visible_under_code_blob"] += 1; continue
            if not good_quote(line_text(u["files"], r["file"], r["line"])): c["f8_quote_too_short"] += 1; continue
            c["f_pass_all_gates"] += 1; okf.add(k)
    ok = okf
    for u in units: u["added_cands"] = [r for r in u["added_cands"] if (u["id"], r["file"], r["line"], r["bug_kind"]) in ok]
    # 2. teacher text for the surviving extend findings
    jobs = [(u, r) for u in units for r in u["added_cands"]]; res = list(ex.map(ext_one, jobs)); LC.assert_error_budget()
    for (u, r), o in zip(jobs, res): r["_teach"] = o
    # 3. triage reasons for labelled items (verified tier)
    jobs = [(u, t) for u in units for t in u["triage"] if t["decision"]]; res = list(ex.map(tri_one, jobs)); LC.assert_error_budget()
    for (u, t), o in zip(jobs, res): t["_reason"] = o
    # 4. provisional: adjudicate unlabelled items, bounded per class (extend units first: they carry the per-slug floor)
    BUD = {"extend": int(E("R6S_PROV_EXT_BUDGET", "1100")), "hancore_other": 100, "hancore_clean": 60, "dell_broken": 80, "history": 60, "dell_works": 120}
    def cls(u):
        if u["added_cands"]: return "extend"
        return {"hancore_concrete": "hancore_other", "hancore_clean_approve": "hancore_clean", "nudged_approve": "hancore_clean", "dell_broken_verified": "dell_broken", "dell_inuse_missing_binary": "dell_broken",
                "dell_inuse_close": "dell_broken", "version_history": "history", "dell_works_verified": "dell_works"}[u["source"]]
    used = collections.Counter(); cand = []
    for u in sorted(units, key=lambda u: (cls(u) != "extend", sum(1 for t in u["triage"] if not t["decision"]), u["id"])):
        un = [t for t in u["triage"] if not t["decision"]]; c = cls(u)
        if not un or len(un) > (PROV_MAX_UNLAB_EXT if c == "extend" else PROV_MAX_UNLAB) or any(not (t["f"]["line"] or t["loc"]) or t["f"]["stage"] == "runtime" for t in un): continue
        if not any(t["decision"] for t in u["triage"]) and u["source"] not in ("dell_works_verified", "hancore_clean_approve", "nudged_approve") and c != "extend": continue
        if used[c] + len(un) > BUD[c]: continue
        used[c] += len(un); cand += [(u, t) for t in un]
    st.update({"provisional_adjudicated_" + k: v for k, v in used.items()})
    res = list(ex.map(adj_one, cand)); LC.assert_error_budget()
    for (u, t), (a, b) in zip(cand, res): t["_adj"] = (a, b)
    st["provisional_items_adjudicated"] = len(cand)
    return units


# ------------------------------------------------------------------ stage 4: rows
def mk_target(u, tier, files):
    """-> (target, meta_extra) or (None, reason). Hard asserts live here and in validate(). Quotes must be VISIBLE in the rendered prompt (truncated files show only their first lines)."""
    full = files; files = HG.parse_blob(u["blob"])
    tri = []; fails_confirmed = False; basis = collections.Counter()
    for t in u["triage"]:
        f = t["f"]; d = t["decision"]; reason = None; quote = None
        if d:
            o = t.get("_reason") or {}
            if "_error" in o or not o.get("reason"): return None, "triage:no_reason"
            reason = " ".join(str(o["reason"]).split())[:S.MAX_REASON]
            if BANNED.search(reason): return None, "triage:reason_mentions_label_source"
            b = t["basis"]
        else:
            if tier != "provisional": return None, "triage:unlabelled_item"
            a, bb = t.get("_adj", ({"_error": 1}, {"_error": 1}))
            if "_error" in a or "_error" in bb: return None, "triage:adjudication_unavailable"
            da, db = str(a.get("decision")).upper(), str(bb.get("decision")).upper()
            if da not in ("REAL", "FALSE_ALARM") or db not in ("REAL", "FALSE_ALARM"): return None, "triage:teacher_answer_unparseable"
            default_confirm = False
            if da != db:
                if not u["added_cands"] or not DEFAULT_CONFIRM: return None, "triage:teachers_disagree"
                default_confirm = True; a = a if da == "REAL" else bb       # extend rows only: the prompt's own policy, "when unsure, confirm"; the teacher that said REAL gives the reason
            d = "confirm" if (da == "REAL" or default_confirm) else "dismiss"
            b = "default-confirm: teachers disagree (provisional)" if default_confirm else "two open-weights teachers agree (provisional)"
            reason = " ".join(str(a.get("reason") or "").split())[:S.MAX_REASON]
            if not reason or BANNED.search(reason): return None, "triage:reason_bad"
            quote = a.get("quote") if PF.quote_in_file(a.get("quote") or "", files.get(f["file"], "")) and (default_confirm or PF.quote_in_file(bb.get("quote") or "", files.get(f["file"], ""))) else None
            if d == "dismiss" and f["level"] == "fail" and f["stage"] == "runtime": d = "confirm"
        if quote is None:
            ln = f["line"] or t.get("loc") or ((t["ev"] or {}).get("line") if isinstance(((t["ev"] or {}).get("line")), int) else 0)
            lt = line_text(files, f["file"], ln) if ln else None
            if not good_quote(lt):                                    # nearest quotable line within 2 lines
                lt = next((x for x in (line_text(files, f["file"], ln + k) for k in (1, -1, 2, -2)) if good_quote(x)), None) if ln else None
            if not good_quote(lt): return None, "triage:no_quotable_line"
            quote = lt.strip()
        if d == "dismiss" and f["stage"] == "runtime": return None, "triage:runtime_dismissal"
        quote = quote.strip()[:S.MAX_TEXT]
        tri.append(dict(rule=f["rule"], file=f["file"], line=f["line"], decision=d, reason=reason, quote=quote)); basis[b] += 1
        fails_confirmed |= (d == "confirm" and f["level"] == "fail")
    add = []; blocker = False; loc_basis = []
    for r in u["added_cands"]:
        o = r.get("_teach") or {}
        if "_error" in o: drops["extend:teacher_error"] += 1; continue
        fi, fx, sv = str(o.get("finding") or "").strip(), str(o.get("fix") or "").strip(), o.get("severity")
        lt = line_text(files, r["file"], r["line"])
        if lt is None: drops["extend:line_not_in_rendered_prompt"] += 1; continue
        lt = lt.strip()
        if sv not in S.SEVERITIES or not fi or not fx or fx == lt or len(fi) > S.MAX_TEXT or len(fx) > S.MAX_TEXT or "\n" in lt or BANNED_FIND.search(fi) or BANNED_FIND.search(fx): drops["extend:teacher_text_invalid"] += 1; funnel[r["bug_kind"]]["f10_teacher_text_invalid"] += 1; continue
        a = dict(category=r["bug_kind"], severity=sv, file=r["file"], line=r["line"], quote=lt, finding=fi, fix=fx); loc_basis.append(("llm-located" if r.get("line_located") else ("re-anchored" if r.get("line_orig") else "reviewer-line")) + "/" + ("strict" if r.get("_strict") else ("tie-quoted-verified" if r.get("verify") == "quoted_code_near_line" else "tie-gate-verified")))
        if any((x["file"], x["line"], x["category"]) == (a["file"], a["line"], a["category"]) for x in add): continue
        add.append(a); blocker |= sv == "blocker"
    add = add[:S.MAX_ADDED]
    tgt = dict(scripts_triage=tri, added_findings=add, verdict="changes_requested" if (fails_confirmed or blocker) else "approve")
    errs = S.validate(tgt, u["findings"])
    if errs: return None, "schema:" + errs[0][:60]
    for a in add:
        if a["file"] not in files or not PF.quote_in_file(a["quote"], files[a["file"]]) or not PF.quote_on_line(a["quote"], files[a["file"]], a["line"], 2): return None, "assert:added_quote_not_on_line"
        if (a["file"], a["line"]) in {(f["file"], f["line"]) for f in u["findings"]}: return None, "assert:added_repeats_checker_finding"
        if not CB.line_visible(u["info"], a["file"], a["line"]): return None, "assert:added_line_not_visible"
    for t in tri:
        if not PF.quote_in_file(t["quote"], files.get(t["file"], "")): return None, "assert:triage_quote_not_in_file"
    return tgt, dict(basis=dict(basis), added_basis=loc_basis)


def stage_rows(units):
    from tokenizers import Tokenizer
    tk = Tokenizer.from_file(paths.tokenizer_json())
    ntok = lambda msgs: len(tk.encode("".join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in msgs) + "<|im_start|>assistant\n<think>\n\n</think>\n\n").ids)
    guard = HG.Guard(); cm = CR.checker_meta(); v2v = {norm_repo(k["repo"]) for v in json.load(open(os.path.join(T, "data", "val_v2_keys.json"))).values() for k in v if k.get("repo")}
    out = {"verified": [], "provisional": []}
    for u in units:
        files = u["files"]; fs = u["findings"]
        for tier in ("verified", "provisional"):
            prov_lab = any(str(t.get("basis") or "").startswith("provisional") for t in u["triage"])
            if tier == "verified" and prov_lab: continue
            if tier == "verified" and any(not t["decision"] for t in u["triage"]): drops["row:unlabelled_checker_items_verified_tier"] += 1; continue
            if tier == "provisional" and not prov_lab and (all(t["decision"] for t in u["triage"]) or not any("_adj" in t for t in u["triage"])): continue
            if not u["triage"] and not u["added_cands"] and u["source"] not in ("dell_works_verified", "nudged_approve", "hancore_clean_approve") and u["prov"].get("r7_kind") != "clean": drops["row:nothing_to_teach"] += 1; continue
            tgt, extra = mk_target(u, tier, files)
            if tgt is None: drops["row:" + extra] += 1; continue
            msgs = PS.messages(u["blob"], fs, tgt); n = ntok(msgs)
            if n > 32000: drops["row:over_32k_tokens"] += 1; continue
            if u["repo"] in v2v: drops["row:v2_val_repo_in_pool"] += 1; continue
            kind = "clean" if not tgt["scripts_triage"] and not tgt["added_findings"] else ("extend" if tgt["added_findings"] else "triage")
            meta = dict(row_type=kind, tier=tier, provisional=tier == "provisional", hand_reviewed=False, source=u["source"], label_basis=extra["basis"], added_finding_basis=extra["added_basis"], prompt_sha256=PS.PROMPT_SHA256, prompt_id=PS.PROMPT_ID,
                        code_blob_policy=CB.POLICY_ID, checker_git_sha=cm["checker_git_sha"], rules_hash=cm["rules_hash"], runtime_stage="absent (static findings only)", files_origin=u["origin"],
                        repo=u["repo"], commit=u["commit"], license=u["prov"].get("license") or "see repo (public plugin)", attribution=("strict-plurality" if u["source"] == "hancore_concrete" else "n/a"), builder="build_scope",
                        guard_fingerprints_sha256=guard.fp_sha)
            rid = u["id"] + (":" + tier if tier == "provisional" else "")
            row = dict(id=rid, split=None, source=u["source"], row_type=kind, provenance=dict(u["prov"], repo=u["repo"]), weight=u["weight"], tokens=n, meta=meta, messages=msgs)
            why = guard.check_row(row, files=files) or guard.check_row(row, files=u["raw_files"]) or guard.check_row(row)
            if why: drops["guard:" + why.split(":")[0]] += 1; st["guard_reject_" + u["source"]] += 1; continue
            out[tier].append(dict(row, _repo=u["repo"], _fh=frozenset(ws_hash(c) for p, c in u["raw_files"].items() if not p.lower().startswith(("readme", "license")) and c.strip())))
    return out


# ------------------------------------------------------------------ stage 5: assemble (caps, dedupe, per-slug floor, split, write)
FLOOR = int(E("R6S_FLOOR", "15"))
BELOW = []     # rows dropped by the per-slug floor: written to below_floor.jsonl.gz (NOT training data) so a later top-up can reuse them
DEFAULT_CONFIRM = E("R6S_DEFAULT_CONFIRM", "1") == "1"
DELL_SHARE = float(E("R6S_DELL_SHARE", "0.35")); APPROVE_MAX = float(E("R6S_APPROVE_MAX", "0.50"))
def assemble(tiers):
    """whole-tree dedupe over BOTH tiers (extend > triage > clean, verified before provisional), then a cap on clean rows drawn from the Dell sweep (keeps the Dell-sweep share down)"""
    pri = {"extend": 0, "triage": 1, "clean": 2}; allr = sorted(tiers["verified"] + tiers["provisional"], key=lambda r: (pri[r["row_type"]], r["meta"]["provisional"], r["id"]))
    seen = []; kept = []
    for r in allr:
        if any(len(r["_fh"] & s) / max(1, min(len(r["_fh"]), len(s))) >= 0.8 for s in seen): drops["dedupe:near_duplicate_tree"] += 1; continue
        seen.append(r["_fh"]); kept.append(r)
    return kept


def cap_dell(kept):
    """Dell-sweep-pipeline rows <= DELL_SHARE of the build AND total approves <= APPROVE_MAX; hardware-broken (confirm) rows first, then clean/approve rows; verified before provisional"""
    isdell = lambda r: r["source"].startswith("dell") or r["source"] == "nudged_approve"
    ap = lambda r: json.loads(r["messages"][-1]["content"])["verdict"] == "approve"
    non = [r for r in kept if not isdell(r)]; dl = [r for r in kept if isdell(r)]
    prio = lambda r: (ap(r), r["meta"]["provisional"], {"dell_broken_verified": 0}.get(r["source"], 1), r["id"])
    dl.sort(key=prio); out = list(non); na = sum(ap(r) for r in non); nd = 0
    for r in dl:
        tot = len(out) + 1
        if (nd + 1) / tot > DELL_SHARE or (ap(r) and (na + 1) / tot > APPROVE_MAX): drops["cap:dell_sweep_share_or_approve_mix"] += 1; continue
        out.append(r); nd += 1; na += ap(r)
    return out


def slug_counts(rows):
    c = collections.Counter()
    for r in rows:
        for a in json.loads(r["messages"][-1]["content"])["added_findings"]: c[a["category"]] += 1
    return c


def enforce_floor(rows):
    """a focus slug with < FLOOR added findings across train+val is OUT_OF_SCOPE for the build: rows carrying it are dropped (their other labels would hide a real finding); iterate until stable"""
    low_all = {}
    while True:
        c = slug_counts(rows); low = {k for k, v in c.items() if v < FLOOR}
        if not low: return rows, c, low_all
        for k in low: low_all[k] = c[k]
        gone = [r for r in rows if ({a["category"] for a in json.loads(r["messages"][-1]["content"])["added_findings"]} & low)]
        BELOW.extend(gone); rows = [r for r in rows if r not in gone]; drops["slug_floor:rows_dropped"] += len(gone)


def split_and_write(rows, tag):
    rnd = random.Random(2027); repos = sorted({r["_repo"] for r in rows}); rnd.shuffle(repos)
    val_repos = set(repos[:max(1, len(repos) // 10)]); tr, va = [], []
    for r in rows:
        r = {k: v for k, v in r.items() if not k.startswith("_")}; r["split"] = "val" if _r(r) in val_repos else "train"; (va if r["split"] == "val" else tr).append(r)
    for name, rs in (("train", tr), ("val", va)):
        with gzip.open(os.path.join(OUT, f"{tag}{name}.jsonl.gz"), "wt") as f:
            for r in rs: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return tr, va
def _r(r): return r["meta"]["repo"]


def save_counters(stage):
    json.dump(dict(st=dict(st), drops=dict(drops), funnel={k: dict(v) for k, v in funnel.items()}), open(pk(f"counters_{stage}.json"), "w"))
def merge_counters():
    for stg in ("units", "render", "llm"):
        p = pk(f"counters_{stg}.json")
        if os.path.exists(p):
            d = json.load(open(p)); st.update({k: v for k, v in d["st"].items()}); drops.update(d["drops"])
            for k, v in d["funnel"].items(): funnel[k].update(v)


def main():
    stage = A.stage; t0 = time.time()
    if stage in ("units", "all"):
        units = build_units(); save("units.pkl", units); save_counters("units"); print("units", len(units), flush=True)
    if stage in ("render", "all"):
        units = load("units.pkl")
        if A.limit: units = units[:A.limit]
        units = [label_unit(u) for u in locate_all(stage_render(units))]; save("rendered.pkl", units); save_counters("render"); print("rendered", len(units), flush=True)
    if stage in ("llm", "all"):
        units = stage_llm(load("rendered.pkl")); LC.assert_error_budget(); save("llm.pkl", units); save_counters("llm"); print("llm", LC.stats(), flush=True)
    if stage in ("assemble", "all"):
        merge_counters(); units = load("llm.pkl"); kept = assemble(stage_rows(units)); tiers = {"verified": [r for r in kept if not r["meta"]["provisional"]], "provisional": [r for r in kept if r["meta"]["provisional"]], "all": kept}; report = {}
        ver_only = tiers["verified"]; allrows = tiers["verified"] + tiers["provisional"]; allrows = tiers["all"] if "all" in tiers else allrows
        st["slug_counts_verified_only"] = dict(slug_counts(ver_only))
        ver, c, low = enforce_floor(allrows); ver = cap_dell(ver); st.update({"out_of_scope_slug:" + k: v for k, v in low.items()}); prov = [r for r in ver if r["meta"]["provisional"]]
        with gzip.open(os.path.join(OUT, "below_floor.jsonl.gz"), "wt") as f:
            for r in BELOW: f.write(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, ensure_ascii=False) + "\n")
        tr, va = split_and_write(ver, "")
        json.dump(dict(stats=dict(st), drops=dict(drops), funnel={k: dict(v) for k, v in funnel.items()}, slug_counts=dict(c), out_of_scope=sorted(low), rows=dict(total=len(ver), verified=len(ver) - len(prov), provisional=len(prov), train=len(tr), val=len(va))),
                  open(os.path.join(OUT, "build_stats.json"), "w"), indent=1)
        print("rows", len(ver), "prov", len(prov), dict(c), "low", low, flush=True)
    print("done", round(time.time() - t0), "s", LC.stats(), flush=True)


if __name__ == "__main__": main()
