"""Scorer for the Checker model scope (triage / added findings / verdict; gates M1-M5; tracked T1-T5). Pure functions, no network.

Builds on the SHARED scorer (usuba-checker-scripts ``eval/hancore_holdout/scoring.py``): plugin-level verdict metrics go through its ``score_rows``
(three-way verdict, invalid = wrong for both classes, stratified bootstrap CIs) and paired comparisons through its ``mcnemar_exact``.
Item-level metrics (triage decisions, added findings) are clustered by plugin: the bootstrap resamples PLUGINS, not findings, because findings of one plugin are not independent.
Wilson intervals are given next to bootstrap intervals for proportions.

Row format (one per plugin; ``run_b0.py`` writes it):
  plugin, findings (Checker scripts findings: rule,file,line,message,stage,level), valid (bool), invalid_reason, out (post-filtered answer or None), raw_out (parsed answer or None),
  stats (post-filter stats), secs, hardware ("works" | "broken" | None), files_n
Label files:
  S1  {"plugin|rule|file|line": "real" | "false_alarm"}            (Unsure items are simply absent; they never count)
  S2  list of plugin ids                                          (hardware works + Checker pass + hand-reviewed)
  S3  {"plugin|file|line|category": "real" | "not_real" | "unsure"} adjudication of ADDED findings (unsure excluded from precision, reported)
  S4  [{"plugin", "file", "line", "quote"}]                        hand-verified bug locations
"""
import importlib.util
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
GATES = dict(M1_precision=0.60, M1_ci_lower=0.50, M2_clean_blocker_rate=0.15, M2_added_per_clean=0.3, M3_dismiss_real=0.05,
             M5_median_secs=10.0, M5_schema_valid=0.99)
MIN_S = dict(S1=300, S2=150, S3=100, S4=50)


def load_shared():
    """The shared scorer module (usuba-checker-scripts). Raises if the sibling checkout is missing: no silent fallback."""
    cands = [os.environ.get("USUBA_CHECKER_ROOT"), os.path.join(os.path.dirname(os.path.dirname(HERE)), "usuba-checker-scripts")]
    for c in cands:
        p = c and os.path.join(c, "eval", "hancore_holdout", "scoring.py")
        if p and os.path.exists(p):
            spec = importlib.util.spec_from_file_location("usuba_shared_scoring", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise FileNotFoundError("shared scorer not found: set USUBA_CHECKER_ROOT to a usuba-checker-scripts checkout")


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def rate(num, den):
    return None if not den else num / den


def r3(x):
    return None if x is None else round(x, 3)


def cluster_ci(units, stat, n_boot=1000, seed=0, alpha=0.05):
    """Percentile bootstrap CI of ``stat(list_of_units)`` resampling whole units (plugins). None when too few valid resamples."""
    if len(units) < 2:
        return None
    rng = random.Random(seed)
    vals = []
    for _ in range(n_boot):
        v = stat([units[rng.randrange(len(units))] for _ in units])
        if v is not None:
            vals.append(v)
    if len(vals) < max(10, n_boot // 2):
        return None
    vals.sort()
    return [r3(vals[int(alpha / 2 * len(vals))]), r3(vals[min(len(vals) - 1, int((1 - alpha / 2) * len(vals)))])]


def fkey(plugin, f):
    return "%s|%s|%s|%s" % (plugin, f["rule"], f.get("file") or "", int(f.get("line") or 0))


def decisions(row):
    """{finding key: decision} from the post-filtered answer; empty for an invalid row."""
    if not row.get("valid") or not row.get("out"):
        return {}
    return {"%s|%s|%s|%s" % (row["plugin"], t["rule"], t["file"], int(t["line"] or 0)): t["decision"] for t in row["out"]["scripts_triage"]}


def raw_decisions(row):
    if not row.get("valid") or not row.get("raw_out"):
        return {}
    return {"%s|%s|%s|%s" % (row["plugin"], t["rule"], t["file"], int(t["line"] or 0)): t["decision"] for t in row["raw_out"]["scripts_triage"]}


# ---- S1: triage ---------------------------------------------------------------------------------------------------------------------------------
def _triage_units(rows, s1, use_raw=False):
    units = []
    for r in rows:
        dec = raw_decisions(r) if use_raw else decisions(r)
        u = []
        for f in r["findings"]:
            k = fkey(r["plugin"], f)
            if k in s1:
                u.append((s1[k], dec.get(k)))   # (label, decision|None)
        if u:
            units.append(u)
    return units


def _tri_stats(units):
    items = [x for u in units for x in u]
    real = [d for lab, d in items if lab == "real"]
    fa = [d for lab, d in items if lab == "false_alarm"]
    correct = sum(1 for lab, d in items if (lab == "real" and d == "confirm") or (lab == "false_alarm" and d == "dismiss"))   # invalid / missing decision = wrong
    return dict(n=len(items), n_real=len(real), n_false_alarm=len(fa),
                dismiss_of_real=rate(sum(d == "dismiss" for d in real), len(real)),          # M3
                false_alarm_dismissed=rate(sum(d == "dismiss" for d in fa), len(fa)),
                confirm_of_real=rate(sum(d == "confirm" for d in real), len(real)),
                triage_accuracy=rate(correct, len(items)),
                n_no_decision=sum(d is None for _, d in items))


def triage_metrics(rows, s1, n_boot=1000, seed=0):
    """M3 + triage accuracy over S1 labelled findings (invalid rows / missing decisions are wrong, never a dismissal)."""
    units = _triage_units(rows, s1)
    pt = _tri_stats(units)
    res = {k: r3(v) if isinstance(v, float) else v for k, v in pt.items()}
    res["n_plugins"] = len(units)
    nr, nf = pt["n_real"], pt["n_false_alarm"]
    res["dismiss_of_real_wilson"] = wilson(round((pt["dismiss_of_real"] or 0) * nr), nr)
    res["false_alarm_dismissed_wilson"] = wilson(round((pt["false_alarm_dismissed"] or 0) * nf), nf)
    for k in ("dismiss_of_real", "false_alarm_dismissed", "triage_accuracy"):
        res[k + "_ci95"] = cluster_ci(units, lambda us, k=k: _tri_stats(us)[k], n_boot, seed)
    raw = _tri_stats(_triage_units(rows, s1, use_raw=True))
    res["dismiss_of_real_before_postfilter"] = r3(raw["dismiss_of_real"])
    res["ci_method"] = "percentile bootstrap resampling plugins, %d resamples, seed %d" % (n_boot, seed)
    return res


# ---- S3: added findings --------------------------------------------------------------------------------------------------------------------------
def akey(plugin, a):
    return "%s|%s|%s|%s" % (plugin, a["file"], a["line"], a["category"])


def added_items(rows):
    return [(r["plugin"], a) for r in rows if r.get("valid") and r.get("out") for a in r["out"]["added_findings"]]


def _prec_stats(units):
    items = [x for u in units for x in u]
    real = sum(x == "real" for x in items)
    notreal = sum(x == "not_real" for x in items)
    return dict(real=real, not_real=notreal, unsure=sum(x == "unsure" for x in items), unadjudicated=sum(x is None for x in items),
                precision=rate(real, real + notreal))


def added_precision(rows, s3, n_boot=1000, seed=0):
    """M1: precision of ADDED findings against adjudications (unsure and unadjudicated excluded from the denominator, both reported)."""
    units = []
    for r in rows:
        if r.get("valid") and r.get("out"):
            u = [s3.get(akey(r["plugin"], a)) for a in r["out"]["added_findings"]]
            if u:
                units.append(u)
    pt = _prec_stats(units)
    n = pt["real"] + pt["not_real"]
    ci = cluster_ci(units, lambda us: _prec_stats(us)["precision"], n_boot, seed)
    return dict(n_added=sum(len(u) for u in units), n_adjudicated=n, real=pt["real"], not_real=pt["not_real"], unsure=pt["unsure"], unadjudicated=pt["unadjudicated"],
                precision=r3(pt["precision"]), precision_wilson=wilson(pt["real"], n), precision_ci95=ci,
                ci_method="percentile bootstrap resampling plugins, %d resamples, seed %d" % (n_boot, seed))


# ---- S2: clean plugins ---------------------------------------------------------------------------------------------------------------------------
def clean_metrics(rows, s2, n_boot=1000, seed=0):
    """M2 on S2 clean plugins: share that get an added blocker, mean added findings per plugin. An invalid answer on a clean plugin counts as a blocker (wrong, not an approval)."""
    units = []
    for r in rows:
        if r["plugin"] in s2:
            if not (r.get("valid") and r.get("out")):
                units.append((1, 1))   # invalid: counted as a blocker and as one added finding
            else:
                add = r["out"]["added_findings"]
                units.append((int(any(a["severity"] == "blocker" for a in add)), len(add)))

    def st(us):
        return dict(blk=rate(sum(u[0] for u in us), len(us)), per=rate(sum(u[1] for u in us), len(us)))
    pt = st(units)
    nb = sum(u[0] for u in units)
    return dict(n_clean=len(units), clean_with_blocker=nb, blocker_rate=r3(pt["blk"]), blocker_rate_wilson=wilson(nb, len(units)),
                blocker_rate_ci95=cluster_ci(units, lambda us: st(us)["blk"], n_boot, seed),
                added_per_clean=r3(pt["per"]), added_per_clean_ci95=cluster_ci(units, lambda us: st(us)["per"], n_boot, seed))


# ---- S4: bug set ---------------------------------------------------------------------------------------------------------------------------------
def bug_recall(rows, s4, slack=3):
    """Share of S4 hand-verified bug locations hit by an added finding or a confirmed Checker finding at the same file within ``slack`` lines."""
    by = {r["plugin"]: r for r in rows}
    hit = 0
    n = 0
    for g in s4:
        r = by.get(g["plugin"])
        if r is None:
            continue
        n += 1
        locs = []
        if r.get("valid") and r.get("out"):
            locs += [(a["file"], a["line"]) for a in r["out"]["added_findings"]]
            locs += [(t["file"], t["line"]) for t in r["out"]["scripts_triage"] if t["decision"] == "confirm" and t["line"]]
        if any(f == g["file"] and abs((ln or 0) - g["line"]) <= slack for f, ln in locs):
            hit += 1
    return dict(n=n, hit=hit, recall=r3(rate(hit, n)), recall_wilson=wilson(hit, n))


# ---- verdict (shared scorer) ---------------------------------------------------------------------------------------------------------------------
def verdict_metrics(rows, n_boot=1000, seed=0):
    """Model verdict vs HARDWARE truth (broken = positive, works = negative) through the shared scorer; invalid = wrong for both classes."""
    sc = load_shared()
    rr = []
    for r in rows:
        if r.get("hardware") not in ("works", "broken"):
            continue
        v = r["out"]["model_verdict"] if r.get("valid") and r.get("out") else "invalid"
        rr.append(dict(plugin=r["plugin"], label="positive" if r["hardware"] == "broken" else "negative", gt=[], pred=[], verdict=v,
                       invalid_reason=r.get("invalid_reason")))
    if not rr:
        return None
    res = sc.score_rows(rr, n_boot=n_boot, seed=seed)
    return {k: v for k, v in res.items() if k in ("n", "positives", "negatives", "verdict_accuracy", "positive_recall", "negative_false_alarm", "negative_correct_approve",
                                                  "n_invalid", "json_valid", "always_flag_accuracy", "ci95", "ci_method")}


def system_verdict_metrics(rows):
    """Release 1: the System verdict is the Checker scripts' verdict. Accuracy of that verdict vs hardware (what the model cannot make worse)."""
    ok = n = 0
    for r in rows:
        if r.get("hardware") in ("works", "broken"):
            n += 1
            sv = "changes_requested" if any(f.get("level", "fail") == "fail" for f in r["findings"]) else "approve"
            ok += (sv == "changes_requested") == (r["hardware"] == "broken")
    return dict(n=n, correct=ok, accuracy=r3(rate(ok, n)), wilson=wilson(ok, n))


# ---- tracked T1-T5 + practicality (M5) -----------------------------------------------------------------------------------------------------------
def tracked(rows):
    """T1-T5 (definitions in docs/DEFINITION_OF_DONE.md). Tracked, never gating."""
    valid = [r for r in rows if r.get("valid") and r.get("out")]
    st = [r["stats"] for r in valid]
    added_in = sum(s["added_in"] for s in st)
    drop = sum(s["added_dropped_quote"] + s["added_dropped_file"] for s in st)
    dups = sum(s["added_dropped_duplicate"] for s in st)
    kept = sum(s["added_kept"] for s in st)
    n_tri = sum(len(r["raw_out"]["scripts_triage"]) for r in valid)
    ungr = sum(s["confirms_ungrounded"] + s["dismissals_dropped"] for s in st)
    inconsistent = 0
    for r in valid:
        o = r["raw_out"]
        should = any(t["decision"] == "confirm" and f.get("level", "fail") == "fail" for t, f in zip(o["scripts_triage"], r["findings"], strict=False)) or any(
            a["severity"] == "blocker" for a in o["added_findings"])
        inconsistent += (o["verdict"] == "changes_requested") != should
    concrete = sum(1 for r in valid for a in r["out"]["added_findings"] if len(a["fix"]) >= 12 and a["fix"].strip() != a["quote"].strip())
    return dict(
        T1_added_ungrounded_drop_rate=r3(rate(drop, added_in)), T1_n_added_raw=added_in,
        T2_line_accuracy_of_kept=r3(rate(sum(s["lines_ok"] for s in st), kept)), T2_n_kept=kept,
        T3_triage_quote_ungrounded_rate=r3(rate(ungr, n_tri)), T3_n_triage=n_tri,
        T4_verdict_inconsistency_rate=r3(rate(inconsistent, len(valid))), T4_n=len(valid),
        T5_fix_concrete_rate=r3(rate(concrete, kept)), T5_n_kept=kept,
        added_duplicate_of_checker_dropped=dups)


def practical(rows, rerun=None):
    """M5 inputs measurable on any backend: schema-valid rate, median seconds. ``rerun``: second run's raw strings for the determinism check (same order)."""
    n = len(rows)
    v = sum(1 for r in rows if r.get("valid"))
    secs = sorted(r["secs"] for r in rows if r.get("secs") is not None)
    res = dict(n=n, schema_valid=r3(rate(v, n)), schema_valid_wilson=wilson(v, n), median_secs=secs[len(secs) // 2] if secs else None,
               invalid_reasons={})
    for r in rows:
        if not r.get("valid"):
            k = (r.get("invalid_reason") or "?").split(":")[0]
            res["invalid_reasons"][k] = res["invalid_reasons"].get(k, 0) + 1
    if rerun is not None:
        res["deterministic"] = all(a.get("raw") == b for a, b in zip(rows, rerun, strict=True))
    return res


def mcnemar_paired(rows_a, rows_b, s1):
    """M4 helper: paired exact McNemar on triage correctness over S1 items (same items, A vs B)."""
    sc = load_shared()
    ka, kb = [], []
    for ra, rb in zip(rows_a, rows_b, strict=True):
        da, db = decisions(ra), decisions(rb)
        for f in ra["findings"]:
            k = fkey(ra["plugin"], f)
            if k in s1:
                want = "confirm" if s1[k] == "real" else "dismiss"
                ka.append(da.get(k) == want)
                kb.append(db.get(k) == want)
    b, c, p = sc.mcnemar_exact(ka, kb)
    return dict(n=len(ka), a_only=b, b_only=c, p=round(p, 4))


def _paired_cluster(rows_a, rows_b, stat, n_boot=1000, seed=0):
    """CI of stat(A) - stat(B) with the SAME plugins resampled for both systems (rows aligned by index)."""
    if len(rows_a) != len(rows_b):
        raise ValueError("paired rows differ in length")
    rng = random.Random(seed)
    idx = list(range(len(rows_a)))
    a0, b0 = stat([rows_a[i] for i in idx]), stat([rows_b[i] for i in idx])
    diffs = []
    for _ in range(n_boot):
        ix = [rng.choice(idx) for _ in idx]
        a, b = stat([rows_a[i] for i in ix]), stat([rows_b[i] for i in ix])
        if a is not None and b is not None:
            diffs.append(a - b)
    diffs.sort()
    if a0 is None or b0 is None or not diffs:
        return dict(diff=None, ci95=None, excludes_zero=False)
    lo, hi = diffs[int(0.025 * len(diffs))], diffs[min(len(diffs) - 1, int(0.975 * len(diffs)))]
    return dict(diff=r3(a0 - b0), ci95=[r3(lo), r3(hi)], excludes_zero=bool(lo > 0 or hi < 0))


def paired_triage_diff(rows_a, rows_b, s1, n_boot=1000, seed=0):
    """M4 (triage): difference in triage accuracy over S1, plugin-clustered paired bootstrap."""
    return _paired_cluster(rows_a, rows_b, lambda rs: _tri_stats(_triage_units(rs, s1))["triage_accuracy"], n_boot, seed)


def paired_precision_diff(rows_a, rows_b, s3, n_boot=1000, seed=0):
    """M4 (added findings): difference in S3 precision, plugin-clustered paired bootstrap. Findings that only one system emitted must be adjudicated too."""
    def stat(rs):
        return _prec_stats([[s3.get(akey(r["plugin"], a)) for a in r["out"]["added_findings"]] for r in rs if r.get("valid") and r.get("out")])["precision"]
    return _paired_cluster(rows_a, rows_b, stat, n_boot, seed)


def gate_report(m, sizes):
    """Evaluate the gates that the given measurements allow. ``m``: dict with optional keys triage, added, clean, practical. ``sizes``: {S1..S4: n}.
    A gate whose data is below the Definition-of-Done size is reported ``provisional`` (never ``pass``)."""
    out = {}

    def status(ok, enough):
        if ok is None:
            return "not measurable"
        return ("pass" if ok else "fail") if enough else ("provisional-" + ("pass" if ok else "fail"))
    a = m.get("added")
    if a and a["precision"] is not None:
        ci = a["precision_ci95"]
        ok = a["precision"] >= GATES["M1_precision"] and ci is not None and ci[0] >= GATES["M1_ci_lower"]
        out["M1"] = dict(value=a["precision"], ci95=ci, n=a["n_adjudicated"], gate="precision>=0.60 and CI lower>=0.50", status=status(ok, sizes.get("S3", 0) >= MIN_S["S3"]))
    else:
        out["M1"] = dict(status="not measurable", why="no S3 adjudications")
    c = m.get("clean")
    if c and c["n_clean"]:
        ok = c["blocker_rate"] <= GATES["M2_clean_blocker_rate"] and c["added_per_clean"] <= GATES["M2_added_per_clean"]
        out["M2"] = dict(blocker_rate=c["blocker_rate"], added_per_clean=c["added_per_clean"], n=c["n_clean"], gate="blocker rate<=0.15 and added/clean<=0.3",
                         status=status(ok, sizes.get("S2", 0) >= MIN_S["S2"]))
    else:
        out["M2"] = dict(status="not measurable", why="no S2 clean set")
    t = m.get("triage")
    if t and t["n_real"]:
        ok = t["dismiss_of_real"] <= GATES["M3_dismiss_real"]
        out["M3"] = dict(value=t["dismiss_of_real"], wilson=t["dismiss_of_real_wilson"], n_real=t["n_real"], gate="dismisses<=5% of real Checker failures",
                         status=status(ok, sizes.get("S1", 0) >= MIN_S["S1"]))
    else:
        out["M3"] = dict(status="not measurable", why="no S1 real findings")
    out["M4"] = dict(status="not measurable", why="needs Checker model results; use mcnemar_paired, paired_triage_diff and paired_precision_diff against B0")
    p = m.get("practical")
    if p:
        ok = p["schema_valid"] >= GATES["M5_schema_valid"] and p["median_secs"] is not None and p["median_secs"] <= GATES["M5_median_secs"]
        out["M5"] = dict(schema_valid=p["schema_valid"], median_secs=p["median_secs"], deterministic=p.get("deterministic"),
                         gate="schema-valid>=99%, median<=10 s, deterministic (Q4_K_M on a 32 GB laptop is NOT measured by an API run)", status="provisional-" + ("pass" if ok else "fail"))
    return out
