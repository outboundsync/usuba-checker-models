#!/usr/bin/env python3
"""r6 dataset build = build_r5.py (audit fixes A1-A3, A5, A7, A12, E) + Harris 2026-10-15 decisions: version-history bug-fix pairs first (share cap R6_HIST_SHARE, default 0.70 of broken rows),
HANCORE second (explicit-mention plurality attribution, label_filters.plurality_table), approve mix ~R6_APPROVE_RATIO (0.47) with HANCORE-clean first, Dell-sweep approves capped so the Dell share falls,
every kind >= 15 findings across train+val (merge into PARENT kind, else drop), guard with per-file J>=0.5 / same-name / same-author. Only the policy knobs differ from r5; see assemble().
 No training, no GPU, no Dell commands; open-weights models only via llm_client (fail closed).

Stages (each writes to $R5_WORK; rerun is idempotent, LLM replies replay from the cache):
  1 pool     r3 pool + version-history + jankeesvw + synthetic/winners + review-clean HANCORE approves  -> candidates with FULL source files where available
  2 render   scrub, ONE code_blob (label independent, truncation markers, line numbers), ONE pinned Checker regenerated for EVERY row (HC rules included), cited-line visibility
  3 gates    fail-closed exact-line gates: mechanical + qwen + gpt-oss for every file:line finding (errors drop the finding and are counted)
  4 guard    content-based holdout/Dell-key guard (holdout_guard.Guard), manifest ids, v2-val exclusion, unknown provenance -> reject
  5 assemble dedupe, caps, A2 approve policy (real clean plugins first), A3 label space + minimum rows per slug, repo-disjoint val -> train/val.jsonl.gz
  usage: build_r6.py WORKDIR OUTDIR [--stage pool|render|gates|assemble|all]
Seeds: Random(2027) assemble. Inputs are read from env-configurable locations (paths.py / R4_WORK etc.)."""
import sys, os, re, json, gzip, random, collections, hashlib, time, argparse, pickle
from concurrent.futures import ThreadPoolExecutor
H = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(H)
sys.path[:0] = [T, H]
import paths, code_blob as CB, prompt_v4 as P4, holdout_guard as HG, llm_client as LC, exactline as X
import checker_report as CR
import label_filters as LF
import functest as FT

ap = argparse.ArgumentParser(); ap.add_argument("work"); ap.add_argument("out"); ap.add_argument("--stage", default="all"); ap.add_argument("--limit", type=int, default=0)
A = ap.parse_args(); W, OUT = A.work, A.out; os.makedirs(W, exist_ok=True); os.makedirs(OUT, exist_ok=True)
R4W = os.environ.get("R4_WORK", "/workspace/r4"); WT = os.environ.get("USUBA_MONO", "/workspace/wt-retrain-v2")     # r4 intermediates; mono tree with dell/sweep + hancore data (inputs only)
FX = os.environ.get("V3FIXES", "/workspace/usuba-runs/v3-fixes/"); HL = os.environ.get("HANCORE_LABELS", "/workspace/usuba-runs/hancore-labels/")
CACHE_DIR = os.environ.get("HANCORE_CACHE", "/workspace/hancore_cache")
rd = lambda p: [json.loads(l) for l in gzip.open(p, "rt")]
tgt = lambda r: json.loads(r["messages"][-1]["content"])
st = collections.Counter(); drops = collections.Counter()
SYN = {"synthetic_lifecycle"}
HARNESS = set(CR.HARNESS_FILES) | {".ok", ".fail", ".done"}


def ws_hash(t): return hashlib.sha1(re.sub(r"\s+", "", t).encode()).hexdigest()
def full_hashes(files): return {ws_hash(c) for p, c in files.items() if not p.lower().startswith(("readme", "license")) and c.strip()}
def norm_repo(s): return s.lower().rstrip("/").removesuffix(".git").split("github.com/")[-1]


# ------------------------------------------------------------------ stage 1: pool with full sources
def parse_files_plain(u):
    """files from a stored r2-r4 prompt (plain, unnumbered). Returns (files, suspect) - suspect = a file may have been cut by the old 8k/16k/48k caps or omitted"""
    f = HG.parse_blob(u); sus = "(omitted:" in u or any(len(c) >= 7900 for c in f.values())
    return f, sus


def build_pool():
    pool = []
    sys.path.insert(0, os.path.join(paths.checker_root(), "hancore")); import common as HC
    HC.REV = os.path.join(WT, "dell/sweep/hancore_reviews.jsonl")
    STRICT = LF.plurality_table(HC)                       # audit E: one reviewed commit per plugin (majority SHA, "fixed in <sha>" and foreign-repo URLs excluded)
    RET = LF.retraction_ids(json.load(open(FX + "retraction_list.json")))   # withdrawn findings (whole or partial): the row is dropped
    r3 = rd(R4W + "/r3_pool_final.jsonl.gz"); hb = rd(R4W + "/hist/hist_broken.jsonl.gz"); ha = rd(R4W + "/hist/hist_approve_candidates.jsonl.gz"); jank = rd(R4W + "/jank_rows.jsonl.gz")
    ex = []
    for fn in ("synthetic_rows.jsonl", "winners_rows.jsonl"):
        for l in open(FX + fn):
            r = json.loads(l)
            if r["provenance"].get("include_in_train", True) is False: continue
            ex.append(r)
    st["pool_r3"], st["pool_hist_broken"], st["pool_hist_approve"], st["pool_jank"], st["pool_extra"] = len(r3), len(hb), len(ha), len(jank), len(ex)
    rows = [dict(r, source=r.get("source")) for r in r3 + hb + ha + ex] + [dict(r, source="jankeesvw-history") for r in jank]
    # index of dell corpus, hancore source dirs, history trees
    C = {}
    for l in open(WT + "/dell/sweep/corpus.jsonl"):
        c = json.loads(l); C[c["key"].lower()] = c
    SRC = {n.lower(): os.path.join(CACHE_DIR, n) for n in os.listdir(CACHE_DIR) if os.path.exists(os.path.join(CACHE_DIR, n, ".ok"))}
    SRC.update({n.lower(): os.path.join(HL, "src_full", n) for n in os.listdir(os.path.join(HL, "src_full"))})
    PREP = {}
    for l in open(R4W + "/prepared.jsonl"):
        p = json.loads(l); PREP[(p["repo"].lower().replace("__", "/"), p["commit"])] = p
    out = []
    for r in rows:
        if A.limit and len(out) >= A.limit: break
        src, pv = r["source"], r.get("provenance") or {}; t = tgt(r); spec = None; origin = None
        why = LF.synthetic_reason(r) if LF.SYNTHETIC_POLICY == "exclude" else None
        if why: drops["synthetic:excluded_template_artefact"] += 1; continue
        if src == "hancore_concrete":
            if r["id"] in RET: drops["retraction:withdrawn_finding_row_dropped"] += 1; continue
            ok, why = LF.attribution_v2(STRICT, r["id"], pv.get("commit"))
            if not ok: drops[why] += 1; continue
        if src.startswith("dell") or src == "nudged_approve":
            m = re.match(r"^[\w-]+:([^:]+):", r["id"]); c = C.get(m.group(1).lower()) if m else None
            if c and c.get("local_dir") and os.path.isdir(c["local_dir"]) and (not pv.get("commit") or pv["commit"] == c.get("commit")): spec, origin = dict(dir=c["local_dir"]), "dell_corpus"
        elif src == "hancore_concrete":
            pl = r["id"].split(":", 1)[1].rsplit(":", 1)[0]; d = SRC.get((pl.replace("/", "__") + "@" + pv.get("commit", "")).lower())
            if d: spec, origin = dict(dir=d), "hancore_full" if "src_full" in d else "hancore_cache"
        elif src == "version_history":
            p = PREP.get((pv["repo"].lower(), pv["commit"]))
            if p:
                d = p["tree_pre"] if r["id"].endswith(":broken") else p.get("tree_post")
                if d and os.path.isdir(d): spec, origin = dict(dir=d), "history_tree"
        if spec is None:     # fallback: the files shown in the old prompt, only if provably not cut (no file near an old cap, nothing omitted)
            f, sus = parse_files_plain(r["messages"][-2]["content"])
            if sus or not f: drops["pool:no_full_source_and_shown_may_be_truncated"] += 1; continue
            spec, origin = dict(files=f), "shown_untruncated"
        out.append(dict(id=r["id"], source=src, verdict=r["verdict"], label=r.get("label"), target=t, prov=pv, weight=r.get("weight", 1.0), spec=spec, origin=origin,
                        old_msgs_user=None, pair=r.get("pair"), orig_source=r.get("orig_source")))
    # review-clean HANCORE approves (A2): reviewed plugin, approved/listed by the reviewer, no strong/likely/open finding, source at the reviewed commit
    excl = {norm_repo(u) for u in json.load(open(HL + "excluded_plugins.json"))}
    n_hc = 0
    for p, d in sorted(HC.load(strict_sha=True).items()):
        sts = {HC.strength(x["fixed"]) for x in d["findings"]}
        if sts & {"strong", "likely", "open"} or not (d["approved"] or d["listed"]) or not d["sha"]: continue
        repo = norm_repo(p)
        if repo in excl: drops["hancore_clean:excluded_plugin"] += 1; continue
        dd = SRC.get((repo.replace("/", "__") + "@" + d["sha"]).lower())
        if not dd: drops["hancore_clean:no_source"] += 1; continue
        out.append(dict(id=f"hancore_clean:{repo}:{d['sha'][:10]}", source="hancore_clean_approve", verdict="approve", label="works", target=dict(verdict="approve", load="works", findings=[]),
                        prov=dict(kind="hancore-reviewed-clean", repo=repo, commit=d["sha"], approved=d["approved"], listed=d["listed"], weak_outcomes=sorted(sts), license="see repo (public plugin)"),
                        weight=1.0, spec=dict(dir=dd), origin="hancore_cache", pair=None, orig_source=None)); n_hc += 1
    st["hancore_clean_approve_candidates"] = n_hc
    return out


# ------------------------------------------------------------------ stage 2: files + Checker report (parallel)
def _work(c):
    spec = c["spec"]
    files = spec["files"] if "files" in spec else FT.read_dir(spec["dir"])
    files = {p: t for p, t in files.items() if p not in HARNESS and os.path.basename(p) not in HARNESS}
    rep = None if not files else CR.report(files)
    return c["id"], files, rep


def stage_render(pool):
    from multiprocessing import Pool
    t0 = time.time()
    with Pool(6, maxtasksperchild=40) as mp: res = mp.map(_work, pool, chunksize=4)
    print(f"checker+read {len(pool)} rows in {time.time() - t0:.0f}s", flush=True)
    R = {i: (f, r) for i, f, r in res}
    from build_reviewer_scrub import scrub
    rows = []
    for c in pool:
        files, rep = R[c["id"]]
        if not files: drops["render:empty_source"] += 1; continue
        if rep is None: drops["render:checker_unavailable_or_timeout"] += 1; continue
        sf = {}
        ok = True
        for p, t in files.items():
            s = scrub(CB.norm_newlines(t))
            if s.count("\n") != CB.norm_newlines(t).count("\n"): ok = False; break     # scrub must never shift line numbers
            sf[p] = s
        if not ok: drops["render:scrub_shifts_lines"] += 1; continue
        blob, info = CB.render(sf)
        t = json.loads(json.dumps(c["target"])); keep = []
        for f in t["findings"]:
            f = dict(f); slug = P4.to_slug(f["category"])
            if slug is None: drops["finding:unmappable_category"] += 1; continue
            if slug in P4.OUT_OF_SCOPE: drops["finding:out_of_scope_slug:" + slug] += 1; continue
            f["category_orig"] = f["category"] if slug != f["category"] else None; f["category"] = slug
            if f.get("file") and isinstance(f.get("line"), int):
                if f["file"] not in sf: drops["finding:file_missing"] += 1; continue
                if c["source"] == "hancore_concrete" and not LF.cited_line_exists(sf, f): drops["attribution:cited_line_missing_at_attributed_sha"] += 1; continue   # r6: the cited line must exist at the attributed SHA
                if not CB.line_visible(info, f["file"], f["line"]): drops["finding:cited_line_not_visible_under_shared_policy"] += 1; continue
            keep.append(f)
        if c["verdict"] != "approve" and not keep: drops["row:no_finding_left"] += 1; continue
        if len(keep) < len(t["findings"]): st["rows_with_findings_dropped"] += 1
        t["findings"] = keep
        rows.append(dict(c, files=sf, raw_files=files, blob=blob, info=info, report=[scrub(x) for x in rep], target=t))
    return rows


# ------------------------------------------------------------------ stage 3: fail-closed gates
VSYS = """You verify citations in code-review findings for a plugin. You get a finding and the numbered source lines around the CITED line ('>' marks it).
(a) defect_stated: true if the finding describes a concrete defect or risk in this code that a reviewer would ask to have fixed; false if it describes safe or intended behaviour, confirms a fix, states scope, or is not about a defect.
(b) exact: true if the CITED line is the exact statement the finding describes: the line holding the call / assignment / command / declaration whose problem it states (a statement spanning several lines may be cited at its first line). false when the cited line is a function header or a sibling, a log or message string, a different statement, an import, a comment, a closing brace, or only nearby.
(c) better_line: if exact is false and the exact statement is visible in the window, its line number, else null.
Reply JSON only: {"defect_stated": true|false, "exact": true|false, "better_line": null|int, "why": "<one short sentence>"}"""
def vwindow(lines, L, ctx=10):
    a = max(0, L - 1 - ctx); b = min(len(lines), L + ctx)
    return "\n".join(f"{'>' if i + 1 == L else ' '}{i + 1:5d}| {lines[i][:220]}" for i in range(a, b))
def gate_one(job):
    c, f = job; lines = c["files"][f["file"]].split("\n"); L = f["line"]
    mech = X.check(f["finding"], lines, L, f["file"])
    user = f"FINDING: {f['finding']}\n\nFILE: {f['file']}\n{vwindow(lines, L)}"
    q = LC.call(VSYS, user, tag="r4_lineverify_final", max_tokens=300)
    g = LC.call(VSYS, user, tag="r4_lineverify_gptoss", model=LC.GPT, effort="low", max_tokens=1500)
    return mech, q, g
def stage_gates(rows):
    jobs = [(c, f) for c in rows if c["source"] not in SYN and c["target"]["findings"] for f in c["target"]["findings"] if f.get("file") and isinstance(f.get("line"), int)
            and not (c["verdict"] == "approve")]
    with ThreadPoolExecutor(12) as ex: res = list(ex.map(gate_one, jobs))
    LC.assert_error_budget()
    gstat = collections.Counter(); bad = set()
    for (c, f), (mech, q, g) in zip(jobs, res):
        gstat["findings"] += 1
        if "_error" in q or "_error" in g: gstat["llm_error"] += 1; bad.add((c["id"], f["file"], f["line"])); continue            # fail closed
        mp = mech in ("strict", "two_line", "nocheck"); qp = q.get("exact") is True and q.get("defect_stated") is not False; gp = g.get("exact") is True and g.get("defect_stated") is not False
        gstat["mech_pass"] += mp; gstat["qwen_pass"] += qp; gstat["gptoss_pass"] += gp
        if mp and qp and gp: gstat["all_pass"] += 1
        else:
            bad.add((c["id"], f["file"], f["line"])); gstat["fail_" + ("mech" if not mp else "") + ("qwen" if not qp else "") + ("gptoss" if not gp else "")] += 1
    out = []
    for c in rows:
        fl = [f for f in c["target"]["findings"] if (c["id"], f.get("file"), f.get("line")) not in bad]
        nd = len(c["target"]["findings"]) - len(fl)
        if nd: drops["finding:failed_exact_line_gate"] += nd
        if c["verdict"] != "approve" and not fl: drops["row:all_findings_failed_gate"] += 1; continue
        c = dict(c, target=dict(c["target"], findings=fl)); out.append(c)
    # synthetic rows: re-anchor a failing cited line mechanically, else drop
    for c in out:
        if c["source"] in SYN:
            for f in c["target"]["findings"]:
                if f.get("file") and isinstance(f.get("line"), int):
                    lines = c["files"][f["file"]].split("\n")
                    if X.check(f["finding"], lines, f["line"], f["file"]) not in ("strict", "two_line"):
                        cand = [i + 1 for i in range(len(lines)) if X.check(f["finding"], lines, i + 1, f["file"]) == "strict"]
                        if cand: f["line"] = cand[0]; st["synthetic_reanchored"] += 1
                        else: f["_bad"] = True
    out = [c for c in out if not any(f.get("_bad") for f in c["target"]["findings"])]
    return out, dict(gstat, **LC.stats())


# ------------------------------------------------------------------ stage 4: row build + guard + exclusions
def ntok_factory():
    from tokenizers import Tokenizer
    tk = Tokenizer.from_file(paths.tokenizer_json())
    # Qwen ChatML framing (what the chat template adds around every message) so the count matches the trainer's templated length within a few tokens
    return lambda msgs: len(tk.encode("".join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in msgs) + "<|im_start|>assistant\n<think>\n\n</think>\n\n").ids)


def v2_val_repos():
    d = json.load(open(os.path.join(T, "data", "val_v2_keys.json")))
    return {norm_repo(k["repo"]) for v in d.values() for k in v if k.get("repo")}


def repo_of(r):
    if r["source"] in ("version_history", "jankeesvw-history", "hancore_clean_approve"): return (r["prov"].get("repo") or r["id"]).lower()
    m = re.match(r"^[\w-]+:([^:]+):", r["id"]); return (m.group(1) if m else r["id"]).lower()


def stage_rows(rows):
    ntok = ntok_factory(); guard = HG.Guard(); v2v = v2_val_repos(); cm = CR.checker_meta(); out = []
    for c in rows:
        orig = [f.get("category_orig") for f in c["target"]["findings"]]   # kept in provenance only: the model must not be trained to emit its own pre-fold label
        clean = dict(c["target"], findings=[{k: v for k, v in f.items() if k != "category_orig"} for f in c["target"]["findings"]])
        msgs = P4.messages(c["blob"], c["report"], clean); tk = ntok(msgs)
        if tk > 32000: drops["row:over_32k_tokens"] += 1; continue
        repo = repo_of(c)
        if repo in v2v: drops["row:v2_val_repo_in_pool"] += 1; continue
        pv = dict(c["prov"], category_orig=orig); meta = dict(prompt_sha256=P4.PROMPT_SHA256, code_blob_policy=CB.POLICY_ID, checker_git_sha=cm["checker_git_sha"], rules_hash=cm["rules_hash"], files_origin=c["origin"],
                                          builder="build_r6", guard_fingerprints_sha256=guard.fp_sha)
        row = dict(id=c["id"], split=None, source=c["source"], orig_source=c["orig_source"], label=c["label"], verdict=c["verdict"], provenance=pv, weight=c["weight"], tokens=tk, meta=meta, messages=msgs, pair=c["pair"])
        why = guard.check_row(row, files=c["files"])        # full shown files, plus repo/id/provenance rules
        if why is None:     # also the full raw files (pre-truncation) so a long file cannot hide a copy
            why = guard.check_row(row, files={p: t for p, t in c["raw_files"].items()})
        if why is None: why = guard.check_row(row)       # finally exactly what the model sees: the files parsed back out of the rendered prompt (preflight item 6 does the same)
        if why: drops["guard:" + why.split(":")[0]] += 1; st["guard_reject_" + c["source"]] += 1; continue
        out.append(dict(row, _repo=repo, _fh=full_hashes(c["raw_files"]), _info=c["info"], _files=sorted(c["files"])))
    return out


# ------------------------------------------------------------------ stage 5: assemble
HIST_SHARE = float(os.environ.get("R6_HIST_SHARE", "0.70")); APPROVE_RATIO = float(os.environ.get("R6_APPROVE_RATIO", "0.47")); TWIN_FRAC = float(os.environ.get("R6_TWIN_FRAC", "0.8")); TWIN_APPROVE_SHARE = float(os.environ.get("R6_TWIN_APPROVE_SHARE", "0.5")); MIN_KIND = 15
# kind -> parent kind (same family); applied to kinds below MIN_KIND across train+val, then dropped if the parent is also below
PARENT = {"load:unknown-type": "load:undefined-reference", "load:missing-import": "load:undefined-reference", "load:invalid-binding": "load:undefined-reference", "load:component-not-created": "load:undefined-reference",
          "load:panel-lifecycle": "load:undefined-reference", "runtime:error-handling": "runtime:logic-error", "runtime:state-or-race": "runtime:logic-error",
          "in-use:invalid-command-arg": "in-use:missing-binary", "in-use:missing-file": "in-use:missing-binary", "in-use:placeholder-data": "in-use:stale-or-wrong-display"}
THIN = {"null-or-missing-guard", "missing-dependency-or-install", "shell-quoting-or-expansion", "error-handling", "security", "api-compat-change"}
def remap_kinds(rows, mapping):
    """merge finding categories (child -> parent) in the target JSON; a drop (parent None) removes the finding, and a broken row left with none is dropped"""
    out = []
    for r in rows:
        t = tgt(r); fs = []
        for f in t["findings"]:
            c = f["category"]
            if c in mapping:
                if mapping[c] is None: drops["kind_floor:finding_dropped"] += 1; continue
                f = dict(f, category=mapping[c]); st["kind_floor_merged"] += 1
            fs.append(f)
        if r["verdict"] != "approve" and not fs: drops["kind_floor:row_dropped"] += 1; continue
        r = dict(r); t = dict(t, findings=fs); r["messages"] = r["messages"][:-1] + [dict(r["messages"][-1], content=json.dumps(t, ensure_ascii=False))]; out.append(r)
    return out


def assemble(rows):
    rnd = random.Random(2027)
    nol = {r["id"] for r in rows if any(not isinstance(f.get("line"), int) or not f.get("file") for f in tgt(r)["findings"])}   # hard rule: every finding in a shipped label has file AND line
    if nol:
        rows = [r for r in rows if r["id"] not in nol]; drops["row:finding_without_file_or_line"] += len(nol)
    kinds = lambda r: {f["category"] for f in tgt(r)["findings"]}
    isb = lambda r: r["verdict"] != "approve"
    prio = lambda r: {"jankeesvw-history": 1, "dell_broken_verified": 0, "dell_inuse_close": 0, "dell_inuse_missing_binary": 0, "hancore_concrete": 0, "hancore_clean_approve": 0}.get(r["source"], 2)
    rows.sort(key=lambda r: (prio(r), r["id"])); final, idx = [], collections.defaultdict(list)
    twin = lambda r: (r["provenance"].get("commit"), r["_repo"]) if r["source"] == "version_history" else None
    for r in rows:
        cand = collections.Counter(j for h in r["_fh"] for j in idx[h]); dup = None
        for j, n in cand.items():
            o = final[j]
            if n / max(1, min(len(r["_fh"]), len(o["_fh"]))) >= 0.5 and not (twin(r) and twin(r) == twin(o)) and r["source"] not in SYN:
                dup = o; break
        if dup is not None: drops[f"dedupe_near_dup:{r['source']}_vs_{dup['source']}"] += 1; continue
        final.append(r)
        for h in r["_fh"]: idx[h].append(len(final) - 1)
    rows = final
    def hp(r):
        u = int(hashlib.sha1(r["id"].encode()).hexdigest(), 16) / 2**160; pv = r["provenance"]
        return ((u * 0.5 if pv.get("history_bug_kind") in THIN else u) + (0.1 if pv.get("exact_class") != "exact_removed" else 0), r["id"])
    def drop(ids, why):
        nonlocal rows; rows = [r for r in rows if r["id"] not in ids]; drops[why] += len(ids)
    def broken(): return [r for r in rows if isb(r)]
    def enforce():
        b = broken(); nb = len(b)
        for src in sorted({r["source"] for r in b}):
            rs = [r for r in b if r["source"] == src]; sh = HIST_SHARE if src == "version_history" else 0.385; cap = int((nb - len(rs)) * sh / (1 - sh))
            if len(rs) > cap:
                order = sorted(rs, key=hp, reverse=True) if src == "version_history" else sorted(rs, key=lambda r: hashlib.sha1((str(rnd.random()) + r["id"]).encode()).hexdigest())
                v = order[:len(rs) - cap]; ids = {r["id"] for r in v} | ({r["id"].replace(":broken", ":fixed") for r in v} if src == "version_history" else set()); drop(ids, f"cap:source_{src}_40pct"); return True
        kc = collections.Counter(c for r in b for c in kinds(r))
        for c, n in kc.most_common():
            if n > int(0.20 * nb):
                rs = [r for r in b if c in kinds(r)]; hist = sorted([r for r in rs if r["source"] == "version_history"], key=hp, reverse=True); oth = [r for r in rs if r["source"] != "version_history"]; rnd.shuffle(oth)
                k = int(-(-(n - 0.20 * nb) // 0.80)); v = (hist + oth)[:k]
                drop({r["id"] for r in v} | {r["id"].replace(":broken", ":fixed") for r in v if r["source"] == "version_history"}, f"cap:kind_{c}_20pct"); return True
        ub = [r for r in b if kinds(r) == {"unbounded-input-resource"}]
        if len(ub) > int(0.20 * nb):
            hist = sorted([r for r in ub if r["source"] == "version_history"], key=hp, reverse=True); oth = [r for r in ub if r["source"] != "version_history"]; rnd.shuffle(oth)
            v = (hist + oth)[:int(-(-(len(ub) - 0.20 * nb) // 0.80))]; drop({r["id"] for r in v} | {r["id"].replace(":broken", ":fixed") for r in v if r["source"] == "version_history"}, "cap:unbounded_only_20pct"); return True
        return False
    while enforce(): pass
    hbk = {r["id"] for r in broken() if r["source"] == "version_history"}
    orph = {r["id"] for r in rows if not isb(r) and r["source"] == "version_history" and r["id"].replace(":fixed", ":broken") not in hbk}
    if orph: drop(orph, "approve_history_twin_dropped")
    hap = sorted([r for r in rows if not isb(r) and r["source"] == "version_history"], key=lambda r: hashlib.sha1(r["id"].encode()).hexdigest()); mx = int(len(hbk) * TWIN_FRAC)
    if len(hap) > mx: drop({r["id"] for r in hap[mx:]}, "approve_history_minority_cap")
    approve = [r for r in rows if not isb(r)]; bro = broken()
    # ---- val: repo-disjoint, per-slug quota, balanced approve; the jankeesvw author never fills val (audit: val concentrated on one author)
    byrepo = collections.defaultdict(list)
    for r in rows: byrepo[r["_repo"]].append(r)
    tot = collections.Counter(c for r in bro for c in kinds(r)); quota = {c: (max(3, round(0.08 * n)) if n >= 6 else (1 if n >= 3 else 0)) for c, n in tot.items()}
    got = collections.Counter(); val_repos = set(); repos = sorted(byrepo); rnd.shuffle(repos)
    nojv = lambda rs: not any(r["source"] in ("synthetic_lifecycle", "jankeesvw-history") for r in rs)
    gain = lambda rs: sum(1 for r in rs if isb(r) for c in kinds(r) if got[c] < quota[c])
    while True:
        best = max((rp for rp in repos if rp not in val_repos and gain(byrepo[rp]) > 0 and nojv(byrepo[rp])), key=lambda rp: (gain(byrepo[rp]), -len(byrepo[rp])), default=None)
        if best is None: break
        val_repos.add(best)
        for r in byrepo[best]:
            if isb(r):
                for c in kinds(r): got[c] += 1
    val_b = [r for rp in val_repos for r in byrepo[rp] if isb(r)]; val_a = [r for rp in val_repos for r in byrepo[rp] if not isb(r)]
    cands = [r for r in approve if r["_repo"] not in val_repos and r["source"] in ("dell_works_verified", "hancore_clean_approve")]; rnd.shuffle(cands); vrs = set(val_repos)
    for r in cands:
        if len(val_a) >= len(val_b): break
        if r["_repo"] in vrs: continue
        val_a.append(r); vrs.add(r["_repo"])
    val = val_b + val_a; val_repos = {r["_repo"] for r in val}
    dup = lambda a, b: len(a["_fh"] & b["_fh"]) / max(1, min(len(a["_fh"]), len(b["_fh"]))) >= 0.5 if a["_fh"] and b["_fh"] else False
    tr = [r for r in rows if r["_repo"] not in val_repos]; ld = {r["id"] for r in tr if any(dup(r, v) for v in val)}; tr = [r for r in tr if r["id"] not in ld]; st["train_rows_dropped_near_dup_with_val"] = len(ld)
    tb = [r for r in tr if isb(r)]; ta = [r for r in tr if not isb(r)]
    # A2: real clean plugins first (review-clean HANCORE approves, runtime-verified clean Dell-sweep plugins), fixed twins and synthetic last
    # r6 A2: HANCORE-clean first (real review-clean plugins), then a mix of Dell-sweep-verified clean plugins and version-history fixed twins: twins are at most TWIN_APPROVE_SHARE of the approves so the Dell share falls
    # without shifting the approve ratio (target APPROVE_RATIO of train rows)
    need_total = int(round(len(tb) * APPROVE_RATIO / (1 - APPROVE_RATIO)))
    clean = [r for r in ta if r["source"] == "hancore_clean_approve"]; twins = [r for r in ta if r["source"] in ("version_history", "fix_upstream")]; dell = [r for r in ta if r not in clean and r not in twins]
    rnd.shuffle(twins); rnd.shuffle(dell)
    need = max(0, need_total - len(clean)); n_tw = min(len(twins), int(need * TWIN_APPROVE_SHARE)); n_dl = min(len(dell), need - n_tw); n_tw = min(len(twins), need - n_dl)
    keep = clean + dell[:n_dl] + twins[:n_tw]
    st["approve_policy"] = dict(target_ratio=APPROVE_RATIO, need_total=need_total, hancore_clean=len(clean), dell_kept=n_dl, dell_available=len(dell), twin_kept=n_tw, twin_available=len(twins))
    st["cap_approve_trim_by_source"] = dict(collections.Counter(r["source"] for r in ta if r not in keep)); ta = keep
    train = tb + ta; rnd.shuffle(train); rnd.shuffle(val)
    return train, val


def write(train, val):
    for sp, rs in (("train", train), ("val", val)):
        with gzip.open(os.path.join(OUT, sp + ".jsonl.gz"), "wt") as f:
            for r in rs: f.write(json.dumps(dict({k: v for k, v in r.items() if not k.startswith("_")}, split=sp), ensure_ascii=False) + "\n")


def save_counters(stage):
    json.dump(dict(st=dict(st), drops=dict(drops)), open(os.path.join(W, f"counters_{stage}.json"), "w"))
def merge_counters(stages):
    for s in stages:
        p = os.path.join(W, f"counters_{s}.json")
        if os.path.exists(p):
            d = json.load(open(p))
            for k, v in d["st"].items(): st[k] = v if not isinstance(v, (int, float)) else st[k] + v
            for k, v in d["drops"].items(): drops[k] += v
def main():
    P = A.stage
    pk = lambda n: os.path.join(W, n)
    if P in ("pool", "all"):
        pool = build_pool(); pickle.dump(pool, open(pk("pool.pkl"), "wb")); print("pool", len(pool), dict(collections.Counter(c["origin"] for c in pool)), flush=True); save_counters("pool")
    if P in ("render", "all"):
        pool = pickle.load(open(pk("pool.pkl"), "rb")); rows = stage_render(pool); pickle.dump(rows, open(pk("rendered.pkl"), "wb")); print("rendered", len(rows), flush=True); save_counters("render")
    if P in ("gates", "all"):
        rows = pickle.load(open(pk("rendered.pkl"), "rb")); rows, g = stage_gates(rows); pickle.dump((rows, g), open(pk("gated.pkl"), "wb")); print("gated", len(rows), json.dumps(g), flush=True); save_counters("gates")
    if P in ("assemble", "all"):
        merge_counters(["pool", "render", "gates"]); rows, g = pickle.load(open(pk("gated.pkl"), "rb")); rows = stage_rows(rows); pickle.dump(rows, open(pk("guarded.pkl"), "wb"))
        import copy
        d0, s0 = copy.deepcopy(dict(drops)), copy.deepcopy(dict(st)); mapping = {}; hist = []
        for it in range(6):    # kind floor: every kind >= MIN_KIND findings across train+val, else merge into its parent kind (iteration 1) or drop (later); counters are reset every pass
            drops.clear(); drops.update(d0); st.clear(); st.update(s0)
            rr = remap_kinds(rows, mapping) if mapping else rows
            train, val = assemble(rr)
            cnt = collections.Counter(f["category"] for r in train + val for f in tgt(r)["findings"]); low = sorted(k for k, n in cnt.items() if n < MIN_KIND)
            hist.append(dict(iteration=it, rows=len(train) + len(val), low=low)); print("kind-floor pass", it, len(train), len(val), "low:", {k: cnt[k] for k in low}, flush=True)
            if not low: break
            for k in low: mapping[k] = (PARENT.get(k) if it == 0 else None)
            for c in list(mapping):      # chains: a child of a dropped kind is dropped too
                q = mapping[c]
                while q in mapping: q = mapping[q]
                mapping[c] = q
        st["kind_floor"] = dict(mapping=mapping, passes=hist)
        write(train, val)
        json.dump(dict(stats=dict(st), drops=dict(drops), gates=g, train=len(train), val=len(val), llm=LC.stats(), checker=CR.checker_meta(), prompt_sha256=P4.PROMPT_SHA256, policy=CB.POLICY_ID), open(pk("build_stats.json"), "w"), indent=1, default=str)
        print("train", len(train), "val", len(val), json.dumps(dict(drops)), flush=True)
if __name__ == "__main__": main()
