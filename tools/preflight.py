#!/usr/bin/env python3
"""Pre-flight checklist before renting a GPU (audit part K, 16 items) as a runnable script. CPU only, no network, no model.

    python3 tools/preflight.py --data /workspace/usuba-runs/v3-data-r5 [--scripts ../usuba-checker-scripts] [--strict] [--json out.json]

Each item prints PASS / WARN / FAIL / SKIP with the evidence. Exit code 1 if any item FAILs (``--strict``: WARN and SKIP also fail).
A check that cannot find what it needs FAILs ("not found"), it is never silently skipped; SKIP is only used where the item needs
something that cannot exist on this machine (torch for the gradient test), and is flagged.

Item numbers match docs/AUDIT part K:  data 1-6, training 7-12, eval 13-16.
"""
import argparse
import ast
import glob
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.dirname(HERE)
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(MODELS, "train"))
PASS, WARN, FAIL, SKIP = "PASS", "WARN", "FAIL", "SKIP"
TWIN_SOURCES = {"version_history", "fix_upstream", "nudged_approve", "synthetic_lifecycle", "synthetic"}   # approves that are fixed twins / synthetic
MIN_PER_SLUG = 5            # legacy floor for the scored-slug check (item 3, train only)
MIN_PER_KIND = 15           # Harris 2026-10-15: every kind in the label set needs >= 15 findings across train+val, else merge into a parent kind or drop it
DELL_SOURCES_PREFIX = ("dell", "nudged_approve")   # rows from the same Dell-sweep pipeline as the sealed Dell key
DELL_SHARE_WARN = 0.5
APPROVE_BAND = (0.40, 0.55)


class Ctx:
    pass


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def rows_of(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def final_answer(row):
    for m in reversed(row["messages"]):
        if m["role"] == "assistant":
            try:
                return json.loads(m["content"])
            except ValueError:
                return {}
    return {}


def config(c):
    import yaml
    return yaml.safe_load(read(os.path.join(MODELS, "train", "config.yaml")))


def load_rows(c):
    if not hasattr(c, "rows"):
        cfg = config(c)
        c.rows = {}
        for k in ("train", "val"):
            p = os.path.join(c.data, os.path.basename(cfg[k + "_file"]))
            if not os.path.exists(p):
                raise FileNotFoundError(f"{p} (config {k}_file={cfg[k + '_file']})")
            c.rows[k] = rows_of(p)
    return c.rows


def gate_report(c):
    p = os.path.join(c.data, "GATE_REPORT.md")
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    return read(p)


def scripts_mod(c, rel, name):
    import importlib.util
    p = os.path.join(c.scripts, rel)
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.join(c.scripts, "functest"))
    spec.loader.exec_module(m)
    return m


# ---- data ---------------------------------------------------------------------------------------------------------------------------------
def i01_shared_code_blob(c):
    import code_blob
    import inspect
    params = set(inspect.signature(code_blob.code_blob).parameters)
    leak = params & {"label", "cited", "finding", "findings", "gold", "line", "lines_cited", "verdict"}
    if leak:
        return FAIL, f"code_blob() takes label-dependent parameters: {sorted(leak)}"
    ev = read(os.path.join(c.scripts, "eval", "hancore_holdout", "run_eval.py"))
    if "code_blob" not in ev:
        return FAIL, "eval/hancore_holdout/run_eval.py does not use code_blob (train and eval would render different blobs)"
    builders = [p for p in glob.glob(os.path.join(MODELS, "train", "v3data", "build_r*.py")) if "code_blob" in read(p)]
    if not builders:
        return FAIL, "no r5 builder imports code_blob"
    bad = [r["id"] for r in sum(load_rows(c).values(), []) if r["meta"].get("code_blob_policy") != code_blob.POLICY_ID]
    if bad:
        return FAIL, f"{len(bad)} rows rendered with another code_blob policy (e.g. {bad[:3]}); current {code_blob.POLICY_ID}"
    return PASS, f"policy {code_blob.POLICY_ID}; no label parameter; eval + {len(builders)} builder(s) import it; all rows carry the policy"


def i02_approve_mix(c):
    tr = load_rows(c)["train"]
    ap = [r for r in tr if final_answer(r).get("verdict") == "approve"]
    if not ap:
        return FAIL, "no approve rows in train"
    from collections import Counter
    mix = Counter(r["source"] for r in ap)
    hancore = sum(v for k, v in mix.items() if k.startswith("hancore"))
    twin = sum(v for k, v in mix.items() if k in TWIN_SOURCES)
    msg = f"approves {len(ap)}/{len(tr)} ({100 * len(ap) // len(tr)}%): {dict(mix)}"
    if hancore == 0:
        return FAIL, "no HANCORE-style review-clean approve rows; " + msg
    if twin * 2 > len(ap):
        return FAIL, f"fixed twins/synthetic are {twin}/{len(ap)} of the approves; " + msg
    if hancore * 10 < len(ap):
        return WARN, f"HANCORE-clean approves are only {hancore}/{len(ap)}; " + msg
    return PASS, msg


def i03_label_space(c):
    sc = scripts_mod(c, "eval/hancore_holdout/scoring.py", "sc_scoring")
    rows = load_rows(c)
    from collections import Counter
    cnt = Counter()
    for r in rows["train"]:
        for f in final_answer(r).get("findings") or []:
            cnt[f.get("category")] += 1
    m = re.search(r"out-of-scope[^:\n]*:\s*(\[[^\]]*\])", gate_report(c))
    oos = set(ast.literal_eval(m.group(1))) if m else set()
    low = [s for s in sc.SCORED if cnt[s] < MIN_PER_SLUG and s not in oos]
    sysmsg = rows["train"][0]["messages"][0]["content"]
    unlisted = [s for s in sc.SCORED if s not in oos and s not in sysmsg]
    if low:
        return FAIL, f"scored slugs with < {MIN_PER_SLUG} train findings and not declared out of scope: { {s: cnt[s] for s in low} }"
    if unlisted:
        return FAIL, f"in-scope scored slugs missing from the system prompt: {unlisted}"
    note = f"out of scope (declared in GATE_REPORT, score it as undefined/drop from the headline): {sorted(oos)}" if oos else "all 13 scored slugs in scope"
    return (WARN if oos else PASS), note + f"; min in-scope count {min([cnt[s] for s in sc.SCORED if s not in oos] or [0])}"


def i04_llm_gates_fail_closed(c):
    rep = gate_report(c)
    m = re.search(r'"calls":\s*(\d+).*?"errors":\s*(\d+)', rep, re.S)
    if not m:
        return FAIL, "GATE_REPORT.md has no LLM call/error counters"
    calls, errs = int(m.group(1)), int(m.group(2))
    cli = os.path.join(MODELS, "train", "v3data", "llm_client.py")
    if not os.path.exists(cli):
        return FAIL, "train/v3data/llm_client.py (shared fail-closed client) not found"
    src = read(cli)
    if "fail" not in src.lower() or "_error" not in src:
        return WARN, "llm_client.py does not visibly handle _error / fail-closed"
    if "fail-closed" not in rep.lower():
        return FAIL, "GATE_REPORT.md does not state the gates are fail-closed"
    # live calls only: replayed cache hits cannot fail
    if calls and errs * 100 > calls:
        return FAIL, f"{errs}/{calls} live LLM calls errored (> 1%)"
    return PASS, f"fail-closed; run stats calls={calls} errors={errs}"


def i05_one_pinned_checker(c):
    rows = sum(load_rows(c).values(), [])
    shas = {r["meta"].get("checker_git_sha") for r in rows}
    rh = {r["meta"].get("rules_hash") for r in rows}
    if None in shas or len(shas) != 1 or len(rh) != 1:
        return FAIL, f"rows were built by {len(shas)} Checker version(s) / {len(rh)} rules_hash (need exactly one, recorded in every row)"
    sha = shas.pop()
    rt = scripts_mod(c, "functest/refpaths.py", "sc_refpaths")
    root = rt.omarchy_root()                       # raises if the reference tree is missing
    dc = scripts_mod(c, "functest/dell_checks.py", "sc_dell_checks")
    api = dc._api()
    n = sum(len(v) for v in api.values())
    if n == 0:
        return FAIL, "reference API table is empty"
    r = subprocess.run(["git", "-C", c.scripts, "merge-base", "--is-ancestor", c.min_checker, sha], capture_output=True, check=False)
    if r.returncode != 0:
        return WARN, (f"rows built with Checker {sha[:7]} which does not contain the audit fixes ({c.min_checker}); reference tree OK ({n} API members at {root}); "
                      "rebuild the reports, or accept it knowingly (the box had the tree, so no label noise from D2)")
    return PASS, f"one Checker {sha[:7]} (contains {c.min_checker}); reference tree {root} with {n} API members"


def i06_holdout_guard(c):
    import holdout_guard as g
    rows = load_rows(c)
    allr = sum(rows.values(), [])
    ids = g.load_ids()
    bad = [r["id"] for r in allr if g.row_repos(r) & ids]
    if bad:
        return FAIL, f"{len(bad)} rows from sealed-holdout repos: {bad[:5]}"
    unknown = [r["id"] for r in allr if not g.row_repos(r)]
    msg = f"repo guard clean on {len(allr)} rows"
    guard_cls = getattr(g, "Guard", None)
    if guard_cls is not None:
        gd = guard_cls()
        hits = gd.check(allr)   # {row id: reason}
        if hits:
            from collections import Counter
            return FAIL, f"guard rejects {len(hits)} of the final rows by rule {dict(Counter(w.split(':')[0] for w in hits.values()))}: {dict(list(hits.items())[:4])}"
        msg += "; guard clean (repo, id, content share J>=0.5, per-file J>=0.5, same-name, same-author J>=0.3 vs the sealed HANCORE holdout and the Dell key)"
    tr_repos = {x for r in rows["train"] for x in g.row_repos(r)}
    va_repos = {x for r in rows["val"] for x in g.row_repos(r)}
    if tr_repos & va_repos:
        return FAIL, f"repos in both train and val: {sorted(tr_repos & va_repos)[:5]}"
    if unknown:
        return WARN, f"{msg}; {len(unknown)} rows carry no repo field (guard cannot judge them by repo): {unknown[:3]}"
    return PASS, msg + "; train/val repo-disjoint"


# ---- training -----------------------------------------------------------------------------------------------------------------------------
def _has_cancelling_loss(src):
    """AST (not text, so docstrings that explain the old bug do not count): (x * w).sum() / w.sum()"""
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
            a, b = n.left, n.right
            if (isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute) and a.func.attr == "sum" and isinstance(a.func.value, ast.BinOp)
                    and isinstance(a.func.value.op, ast.Mult) and isinstance(b, ast.Call) and isinstance(b.func, ast.Attribute) and b.func.attr == "sum"):
                return True
    return False


def i07_example_weight(c):
    cfg = config(c)
    tu = read(os.path.join(MODELS, "train", "train_utils.py"))
    tl = read(os.path.join(MODELS, "train", "train_lora.py"))
    for name, src in (("train_lora.py", tl), ("train_utils.py", tu)):
        if _has_cancelling_loss(src):
            return FAIL, f"the cancelling (per*w).sum()/w.sum() loss is still in {name}"
    if cfg.get("use_example_weight") is False:
        return PASS, "use_example_weight: false on purpose (weights unmeasured); the corrected loss is in train_utils.weighted_micro_loss"
    try:
        import torch  # noqa: F401
    except ImportError:
        return WARN, "use_example_weight is on but torch is not installed here: gradient test could not run (CI installs CPU torch)"
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", os.path.join(MODELS, "train", "tests", "test_train_utils.py")],
                       capture_output=True, text=True, check=False)
    return (PASS if r.returncode == 0 else FAIL), "weighted-loss gradient test: " + r.stdout.strip().splitlines()[-1]


def i08_config_data(c):
    import train_utils as U
    cfg = config(c)
    rows = load_rows(c)
    exp = cfg.get("expected_rows") or {}
    got = {k: len(v) for k, v in rows.items()}
    if not exp.get("train") or not exp.get("val"):
        return FAIL, f"config expected_rows {exp} not set (the trainer refuses to start); data has {got}"
    if {"train": exp["train"], "val": exp["val"]} != got:
        return FAIL, f"config expected_rows {exp} != data {got}"
    sums = os.path.join(c.data, "SHA256SUMS")
    if not os.path.exists(sums):
        return FAIL, f"{sums} not found"
    want = {ln.split()[1].lstrip("*"): ln.split()[0] for ln in read(sums).splitlines() if ln.strip()}
    for k in ("train_file", "val_file"):
        fn = os.path.basename(cfg[k])
        have = U.sha256_file(os.path.join(c.data, fn))
        if want.get(fn) != have:
            return FAIL, f"{fn}: sha256 {have[:12]} does not match SHA256SUMS ({str(want.get(fn))[:12]})"
    return PASS, f"config points at {cfg['train_file']} / {cfg['val_file']}; counts {got} match; SHA256SUMS verify"


def i09_revision_schedule(c):
    import paths
    import train_utils as U
    cfg = config(c)
    rev = cfg.get("base_revision")
    if not rev or not re.fullmatch(r"[0-9a-f]{40}", str(rev)):
        return FAIL, f"base_revision not a pinned 40-hex commit: {rev!r}"
    if getattr(paths, "BASE_REVISION", rev) != rev:
        return FAIL, "config base_revision != paths.BASE_REVISION (builders and trainer would tokenize differently)"
    n = len(load_rows(c)["train"])
    s = U.schedule(n, cfg["per_device_batch"], cfg["grad_accum"], cfg["epochs"], cfg["warmup_ratio"], eval_every_epochs=cfg.get("eval_every_epochs"),
                   eval_every_steps=cfg.get("eval_every_steps"))
    if not s["eval_steps"]:
        return FAIL, f"no mid-run eval in schedule {s}"
    return PASS, f"revision {rev[:8]} pinned; {n} rows -> {s['steps_per_epoch']} steps/epoch, {s['total_steps']} total, eval at {s['eval_steps']}"


def i10_midcheck(c):
    ln = read(os.path.join(MODELS, "train", "launch_vast.sh"))
    need = ["midcheck.py", "holdout_guard.py", "code_blob.py"]
    miss = [n for n in need if n.split(".")[0] not in ln]
    if miss:
        return FAIL, f"launch_vast.sh bundle does not mention {miss}"
    tl = read(os.path.join(MODELS, "train", "train_lora.py"))
    for n in ast.walk(ast.parse(tl)):
        if isinstance(n, ast.Try) and any(isinstance(x, ast.Import) and any(a.name == "midcheck" for a in x.names) for x in ast.walk(ast.Module(body=n.body, type_ignores=[]))):
            for h in n.handlers:
                if not any(isinstance(x, (ast.Raise,)) or (isinstance(x, ast.Call) and getattr(x.func, "attr", "") == "exit") for x in ast.walk(h)):
                    return FAIL, "train_lora.py swallows a midcheck import/setup failure (handler neither raises nor exits)"
    import midcheck
    pool, skipped = midcheck.build_pool(os.path.join(c.data, os.path.basename(config(c)["val_file"])), n=30)
    neg = sum(1 for r in pool if midcheck.gold_verdict(r) == "approve")
    if neg == 0:
        return FAIL, f"midcheck pool has no negatives (approve rows); skipped {skipped}"
    return PASS, f"midcheck bundled, import failure fatal; pool {len(pool)} rows incl. {neg} negatives (skipped {skipped})"


def i11_run_meta_unique_output(c):
    cfg = config(c)
    tl = read(os.path.join(MODELS, "train", "train_lora.py"))
    if "run_meta.json" not in tl:
        return FAIL, "train_lora.py does not write run_meta.json"
    out = cfg["output_dir"]
    used = set()
    for p in glob.glob(os.path.join(MODELS, "docs", "*.md")) + [os.path.join(MODELS, "README.md")]:
        used |= set(re.findall(r"out/usuba-9b-lora[\w-]*", read(p)))
    if out in used:
        return FAIL, f"output_dir {out} was used by an earlier run (mentioned in docs); pick a new one"
    return PASS, f"run_meta.json written; output_dir {out} unused (earlier: {sorted(used)})"


def i12_supervisor(c):
    ln = read(os.path.join(MODELS, "train", "launch_vast.sh"))
    checks = {"trap that destroys on failure": re.search(r"trap\s+'[^']*destroy", ln), "instance wall-clock limit": "INSTANCE_MAX_HOURS" in ln,
              "terminal NO_RESTART/TRAIN_STOPPED handled": "NO_RESTART" in ln and "TRAIN_STOPPED" in ln, "mktemp for temp files": "mktemp" in ln,
              "no fixed local /tmp bundle path": re.search(r"[\s=\"]/tmp/usuba_train_bundle\.tgz", ln) is None, "host key policy not 'no'": "StrictHostKeyChecking=no" not in ln}
    wd = read(os.path.join(MODELS, "train", "watchdog.sh"))
    checks["stall clock starts at first step (watchdog grace)"] = re.search(r"grace|GRACE", wd) is not None
    checks["host does not restart (single supervisor)"] = "pkill" not in re.sub(r"#.*", "", ln.split("watch)")[-1].split("INSTANCE WALL-CLOCK")[0]) if "watch)" in ln else True
    bad = [k for k, v in checks.items() if not v]
    return (FAIL, "missing: " + "; ".join(bad)) if bad else (PASS, "; ".join(checks))


# ---- eval ---------------------------------------------------------------------------------------------------------------------------------
def i13_eval_scoring(c):
    sc = read(os.path.join(c.scripts, "eval", "hancore_holdout", "scoring.py"))
    ev = read(os.path.join(c.scripts, "eval", "hancore_holdout", "run_eval.py"))
    rs = read(os.path.join(c.scripts, "eval", "hancore_holdout", "rescore.py"))
    checks = {"three-way verdict with invalid": '"invalid"' in sc, "finish_reason stored": "finish_reason" in ev, "run_eval uses scoring": "scoring" in ev,
              "rescore uses scoring": "scoring" in rs, "rescore never overwrites a result": "never overwrites" in rs.lower() or "suffix" in rs.lower()}
    bad = [k for k, v in checks.items() if not v]
    return (FAIL, "missing: " + "; ".join(bad)) if bad else (PASS, "; ".join(checks))


def i14_prompt_and_meta(c):
    ev = read(os.path.join(c.scripts, "eval", "hancore_holdout", "run_eval.py"))
    m = re.search(r"add_argument\(\s*[\"']--prompt[\"'][^)]*\)", ev, re.S)
    if not m or "required=True" not in m.group(0):
        return FAIL, "run_eval.py --prompt is not required (defaults to the v1 prompt)"
    miss = [k for k in ("prompt_sha256", "checker_git_sha", "rules_hash") if k not in ev and k not in read(os.path.join(c.scripts, "functest", "usuba", "provenance.py"))]
    if miss or "report_meta" not in ev and "provenance" not in ev:
        return FAIL, f"result files do not record {miss or 'provenance'}"
    return PASS, "--prompt required; result meta records prompt_sha256 + Checker provenance"


def i15_old_runs_rescored(c):
    allres = glob.glob(os.path.join(MODELS, "eval", "**", "*.json"), recursive=True) + glob.glob(os.path.join(MODELS, "results", "**", "*.json"), recursive=True)
    res = [p for p in allres if not p.endswith(".rescored.json") and "summary" not in os.path.basename(p)]
    NO_GENERATIONS = {"checker-baseline"}      # deterministic Checker output: there is no model text to be invalid
    def scored_file(p):
        r = p[:-5] + ".rescored.json"
        return p if '"n_invalid"' in read(p) else (r if os.path.exists(r) and '"n_invalid"' in read(r) else None)
    scored = [(p, scored_file(p)) for p in res]
    have = [(p, f) for p, f in scored if f]
    exempt = [p for p, f in scored if not f and os.path.basename(p)[:-5] in NO_GENERATIONS]
    rest = [os.path.basename(p) for p, f in scored if not f and p not in exempt]
    ci = [f for p, f in have if '"ci"' in read(f) or "ci95" in read(f) or "ci_" in read(f)]
    if not res:
        return FAIL, "no result JSONs found under eval/ or results/"
    if not have:
        return FAIL, f"0/{len(res)} result files carry n_invalid: old runs are not re-scored with the three-way scorer (tools/rescore_all.py, needs the private raw rows)"
    if rest:
        return WARN, f"{len(have)}/{len(res)} result files have n_invalid ({len(ci)} with CIs, {len(exempt)} exempt: no model text); no raw rows to re-score: {rest}"
    return PASS, f"all {len(res)} result files have n_invalid via the original or a .rescored.json ({len(have)} scored, {len(ci)} with CIs, {len(exempt)} exempt: no model text)"


def i17_composition(c):
    """r6 gate numbers: rows per kind (train+val >= MIN_PER_KIND), approve mix, source mix, Dell-sweep share (the Dell key comes from the same pipeline)."""
    from collections import Counter
    rows = load_rows(c)
    allr = rows["train"] + rows["val"]
    cnt = Counter(f.get("category") for r in allr for f in (final_answer(r).get("findings") or []))
    low = {k: n for k, n in cnt.items() if n < MIN_PER_KIND}
    src = Counter(r["source"] for r in allr)
    dell = sum(v for k, v in src.items() if k.startswith(DELL_SOURCES_PREFIX))
    ap = sum(1 for r in allr if final_answer(r).get("verdict") == "approve")
    msg = (f"{len(allr)} rows; approve {ap} ({100 * ap // max(1, len(allr))}%); Dell-sweep share {dell}/{len(allr)} ({100 * dell // max(1, len(allr))}%): report Dell-key scores next to HANCORE holdout "
           f"and clean-set scores; sources {dict(src)}; findings per kind {dict(sorted(cnt.items()))}")
    if low:
        return FAIL, f"kinds below {MIN_PER_KIND} findings across train+val (merge into a parent kind or drop): {low}; " + msg
    share = ap / max(1, len(allr))
    if not APPROVE_BAND[0] <= share <= APPROVE_BAND[1]:
        return WARN, f"approve share {share:.2f} outside {APPROVE_BAND}; " + msg
    if dell / max(1, len(allr)) > DELL_SHARE_WARN:
        return WARN, f"Dell-sweep share above {DELL_SHARE_WARN:.0%}; " + msg
    return PASS, msg


def i16_headline(c):
    rd = read(os.path.join(MODELS, "README.md"))
    ok = ("0.912" in rd) and re.search(r"false[- ]alarm", rd, re.I) and re.search(r"always answering", rd, re.I)
    return (PASS, "README leads with the always-flag baseline (0.912) and the false-alarm column") if ok else (FAIL, "README lacks the always-flag baseline / false-alarm headline")


ITEMS = [(1, "one shared code_blob, label-independent (A1)", i01_shared_code_blob), (2, "approve mix: real clean + HANCORE approves (A2)", i02_approve_mix),
         (3, "label space vs scored slugs (A3)", i03_label_space), (4, "LLM gates fail closed (A5)", i04_llm_gates_fail_closed),
         (5, "one pinned Checker + reference tree (A7, D2)", i05_one_pinned_checker), (6, "holdout guard on exact train/val rows (A12)", i06_holdout_guard),
         (7, "example weighting fixed or off (A4)", i07_example_weight), (8, "config -> data, SHA256SUMS, row counts (A6)", i08_config_data),
         (9, "base_revision pinned, schedule has mid-run evals (A8, A9)", i09_revision_schedule), (10, "midcheck bundled, pool has negatives (A10)", i10_midcheck),
         (11, "run_meta.json + unique output_dir (H)", i11_run_meta_unique_output), (12, "one supervisor, trap, wall clock, stall grace (A11)", i12_supervisor),
         (13, "eval scoring: invalid-on-negative, finish_reason, rescore (B1-B3)", i13_eval_scoring), (14, "--prompt required, provenance in results (A7)", i14_prompt_and_meta),
         (15, "old runs re-scored, n_invalid and CIs (B4, B5)", i15_old_runs_rescored), (16, "headline = false alarms on clean plugins (K16)", i16_headline),
         (17, "composition: >= 15 findings per kind, approve mix, Dell-sweep share (r6)", i17_composition)]


def run(c, only=None):
    out = []
    for n, title, fn in ITEMS:
        if only and n not in only:
            continue
        try:
            st, msg = fn(c)
        except Exception as e:   # noqa: BLE001 - a crashing check is a FAIL with its error, never a skip
            st, msg = FAIL, f"check crashed: {type(e).__name__}: {e}"
        out.append({"item": n, "title": title, "status": st, "detail": msg})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=os.environ.get("R5_DATA") or os.path.join(os.environ.get("USUBA_RUNS", "/workspace/usuba-runs"), "v3-data-r5"))
    ap.add_argument("--scripts", default=os.environ.get("SCRIPTS_REPO") or next((p for p in (os.path.join(MODELS, "..", "usuba-checker-scripts"), os.path.join(MODELS, "..", "scripts"))
                                                                              if os.path.isdir(p)), os.path.join(MODELS, "..", "usuba-checker-scripts")))
    ap.add_argument("--min-checker", default="8b4b31d", help="scripts commit that every row's Checker must contain (the audit fixes)")
    ap.add_argument("--only", type=int, nargs="*")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    c = Ctx()
    c.data, c.scripts, c.min_checker = os.path.abspath(a.data), os.path.abspath(a.scripts), a.min_checker
    res = run(c, set(a.only) if a.only else None)
    for r in res:
        print(f"[{r['status']:4}] {r['item']:2}. {r['title']}\n         {r['detail']}")
    cnt = {k: sum(1 for r in res if r["status"] == k) for k in (PASS, WARN, FAIL, SKIP)}
    print("\n" + "  ".join(f"{k}={v}" for k, v in cnt.items()))
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"data": c.data, "scripts": c.scripts, "results": res, "sha256_of_config": hashlib.sha256(read(os.path.join(MODELS, "train", "config.yaml")).encode()).hexdigest()}, f, indent=1)
    bad = cnt[FAIL] + (cnt[WARN] + cnt[SKIP] if a.strict else 0)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
