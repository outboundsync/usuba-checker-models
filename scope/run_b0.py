#!/usr/bin/env python3
"""B0 harness: any OpenAI-compatible chat model (default: STOCK Qwen3.5-9B on OpenRouter, an open-weights endpoint) through the SAME scope prompt v4, the SAME output
schema validator and the SAME quote post-filter as the Checker model will use. CPU/API only; no GPU, no training.

  python3 -m scope.run_b0 --set dell|s4|holdout --name b0-dell [--model qwen/qwen3.5-9b] [--limit N] [--max-cost 1.0]

Sets (drafts come from scope.build_drafts and live outside git):
  dell     Dell-key plugins (hardware truth; DRAFT S1/S2 labels)        s4   S4 draft (mined upstream bug locations)
  holdout  329-plugin sealed HANCORE holdout (evaluation only; reviewer-category proxy labels, NOT S1-S4)
Writes $USUBA_RUNS/scope-v4/b0/<name>.rows.jsonl (per-plugin, private) and <name>.summary.json (aggregates only; safe to publish).
Spend is tracked in $USUBA_RUNS/scope-v4/spend.json and stops at --max-cost (global cap $5 for this job).
"""
import argparse
import json
import os
import sys
import tarfile
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from scope import checker_findings as CF  # noqa: E402
from scope import postfilter, prompt_scope, schema  # noqa: E402
from scope import scoring as SC  # noqa: E402

RUNS = os.environ.get("USUBA_RUNS", "/workspace/usuba-runs")
BASE = os.path.join(RUNS, "scope-v4")
DRAFTS = os.environ.get("SCOPE_DRAFTS", os.path.join(BASE, "drafts"))
HOLDOUT = os.environ.get("USUBA_HOLDOUT_DIR", "/workspace/usuba-model-checker/eval/hancore_holdout")
GLOBAL_CAP = 5.0
BASE_URL = "https://openrouter.ai/api/v1"
HARNESS = ("SOURCE.txt", "checklist.md")


def load_set(name, limit):
    if name == "dell":
        rows = [json.loads(line) for line in open(os.path.join(DRAFTS, "dell_plugins.jsonl"))]
    elif name == "s4":
        rows = [json.loads(line) for line in open(os.path.join(DRAFTS, "s4_plugins.jsonl"))]
        for r in rows:
            r["findings"] = CF.findings_for(r["files"])
    elif name == "holdout":
        rows = []
        for line in open(os.path.join(HOLDOUT, "manifest.jsonl")):
            m = json.loads(line)
            files = {}
            with tarfile.open(os.path.join(HOLDOUT, m["code_archive"])) as t:
                for mem in t.getmembers():
                    if mem.isfile() and mem.size < 2_000_000:
                        try:
                            files[mem.name.split("/", 1)[-1]] = t.extractfile(mem).read().decode("utf-8")
                        except UnicodeDecodeError:
                            continue
            files = {p: c for p, c in files.items() if p not in HARNESS}
            gt = sorted({c for f in m["findings"] if f.get("strength") in ("strong", "likely") for c in f["categories"]} & set(schema.ADDED_CATEGORIES))
            rows.append(dict(plugin=m["plugin"], set="holdout", hardware=None, files=files, holdout_label=m["label"], gt_focus=gt))
    else:
        raise SystemExit("unknown set")
    if name != "dell":
        for r in rows:
            if r.get("findings") is None and "findings" not in r:
                r["findings"] = CF.findings_for(r["files"])
    return rows[:limit] if limit else rows


def spent_total():
    p = os.path.join(BASE, "spend.json")
    return json.load(open(p)).get("total", 0.0) if os.path.exists(p) else 0.0


_LOCK = threading.Lock()


def add_spend(name, usd):
    with _LOCK:
        p = os.path.join(BASE, "spend.json")
        d = json.load(open(p)) if os.path.exists(p) else dict(total=0.0, runs={})
        d["total"] = round(d["total"] + usd, 6)
        d["runs"][name] = round(d["runs"].get(name, 0.0) + usd, 6)
        with open(p, "w") as f:
            json.dump(d, f, indent=1)


def call(model, msgs, key, max_tokens):
    body = dict(model=model, messages=msgs, temperature=0, max_tokens=max_tokens, reasoning=dict(enabled=False, exclude=True), usage=dict(include=True))
    req = urllib.request.Request(BASE_URL + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                j = json.load(r)
            ch = j["choices"][0]
            return ch["message"].get("content") or "", j.get("usage") or {}, ch.get("finish_reason")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise SystemExit("ABORT: API key rejected (HTTP %d)" % e.code) from e
            msg = e.read().decode("utf-8", "replace")[:200]
            if i == 3:
                return "ERROR HTTP %d %s" % (e.code, msg), {}, "error"
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e:
            if i == 3:
                return "ERROR %s" % type(e).__name__, {}, "error"
        time.sleep(2 * (i + 1))
    return "ERROR exhausted", {}, "error"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["dell", "s4", "holdout"])
    ap.add_argument("--name", required=True)
    ap.add_argument("--model", default="qwen/qwen3.5-9b")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-cost", type=float, default=1.0)
    ap.add_argument("--max-tokens", type=int, default=3000)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--price-in", type=float, default=0.1)    # $/M, only used when the endpoint reports no cost
    ap.add_argument("--price-out", type=float, default=0.15)
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("no $OPENROUTER_API_KEY")
    os.makedirs(os.path.join(BASE, "b0"), exist_ok=True)
    rows_fn = os.path.join(BASE, "b0", a.name + ".rows.jsonl")
    if os.path.exists(rows_fn) and not a.overwrite:
        raise SystemExit("%s exists: use a new --name or --overwrite" % rows_fn)
    plugins = load_set(a.set, a.limit)
    run_spent = [0.0]
    cap = min(a.max_cost, GLOBAL_CAP - spent_total())

    def one(p):
        files = p["files"]
        fs = p["findings"]
        t0 = time.time()
        raw, usage, fin = None, {}, None
        est = 0.02
        with _LOCK:
            skip = fs is None or run_spent[0] + est > cap
            if not skip:
                run_spent[0] += est
        if fs is None:
            raw = "SKIPPED checker-crash"
        elif skip:
            raw = "SKIPPED max-cost"
        else:
            raw, usage, fin = call(a.model, prompt_scope.messages(prompt_scope.render_files(files), fs), key, a.max_tokens)
            c = usage.get("cost")
            c = c if isinstance(c, (int, float)) else usage.get("prompt_tokens", 0) / 1e6 * a.price_in + usage.get("completion_tokens", 0) / 1e6 * a.price_out
            with _LOCK:
                run_spent[0] += c - est
            add_spend(a.name, c)
        out, why = schema.parse_answer(raw, fs, fin)
        flt, stats = (postfilter.apply(out, files, fs) if out is not None else (None, None))
        return dict(plugin=p["plugin"], set=p["set"], hardware=p.get("hardware"), holdout_label=p.get("holdout_label"), gt_focus=p.get("gt_focus"),
                    findings=fs or [], valid=out is not None, invalid_reason=why, raw_out=out, out=flt, stats=stats, secs=round(time.time() - t0, 2),
                    finish_reason=fin, usage=usage, raw=raw)

    with ThreadPoolExecutor(a.workers) as ex:
        rows = list(ex.map(one, plugins))
    with open(rows_fn, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summ = summarize(rows, a)
    with open(os.path.join(BASE, "b0", a.name + ".summary.json"), "w") as f:
        json.dump(summ, f, indent=1)
    print(json.dumps(summ, indent=1))


def labels(path, key="key"):
    if not os.path.exists(path):
        return {}
    return {d[key]: d for d in (json.loads(line) for line in open(path))}


def summarize(rows, a):
    """Aggregates only (no plugin ids, no code, no raw output): this is the part that may be committed."""
    set_name = a.set
    out = dict(name=a.name, set=set_name, model=a.model, prompt=prompt_scope.PROMPT_ID, prompt_sha256=prompt_scope.PROMPT_SHA256, n_plugins=len(rows),
               n_checker_findings=sum(len(r["findings"]) for r in rows), cost_usd=round(sum((r["usage"] or {}).get("cost") or 0 for r in rows), 4),
               status="B0 = stock model, same input/schema/post-filter", generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    out["practical"] = SC.practical(rows)
    out["tracked_T1_T5"] = SC.tracked(rows)
    valid = [r for r in rows if r["valid"]]
    out["postfilter_totals"] = {k: sum(r["stats"][k] for r in valid) for k in valid[0]["stats"]} if valid else {}
    sizes = {}
    meas = dict(practical=out["practical"])
    if set_name == "dell":
        s1 = {k: ("real" if v["label"] == "real" else "false_alarm") for k, v in labels(os.path.join(DRAFTS, "S1_draft.jsonl")).items() if v["label"]}
        s2 = {d["plugin"] for d in (json.loads(line) for line in open(os.path.join(DRAFTS, "S2_draft.jsonl")))}
        out["S1_draft_triage"] = SC.triage_metrics(rows, s1)
        out["S2_draft_clean"] = SC.clean_metrics(rows, s2)
        out["verdict_vs_hardware_model"] = SC.verdict_metrics(rows)
        out["verdict_vs_hardware_system(Checker scripts)"] = SC.system_verdict_metrics(rows)
        out["dismissal_rate_all_findings"] = _dismiss_all(rows)
        meas.update(triage=out["S1_draft_triage"], clean=out["S2_draft_clean"])
        sizes = dict(S1=len(s1), S2=len(s2), S3=0, S4=0)
    elif set_name == "s4":
        s4 = [json.loads(line) for line in open(os.path.join(DRAFTS, "S4_draft.jsonl"))]
        out["S4_draft_bug_recall"] = SC.bug_recall(rows, s4)
        out["dismissal_rate_all_findings"] = _dismiss_all(rows)
        sizes = dict(S1=0, S2=0, S3=0, S4=len(s4))
    else:
        out["holdout_proxy"] = _holdout_proxy(rows)
        sizes = dict(S1=0, S2=0, S3=0, S4=0)
    out["added_findings_summary"] = _added_summary(rows)
    out["dod_set_sizes_used"] = sizes
    out["gates"] = SC.gate_report(meas, sizes)
    return out


def _dismiss_all(rows):
    d = sum(1 for r in rows if r["valid"] for t in r["out"]["scripts_triage"] if t["decision"] == "dismiss")
    n = sum(len(r["findings"]) for r in rows if r["valid"])
    return dict(dismissed=d, findings_in_valid_rows=n, rate=SC.r3(SC.rate(d, n)), wilson=SC.wilson(d, n))


def _added_summary(rows):
    items = SC.added_items(rows)
    cats = {}
    for _, a in items:
        cats[a["category"]] = cats.get(a["category"], 0) + 1
    return dict(kept_after_postfilter=len(items), blockers=sum(a["severity"] == "blocker" for _, a in items), by_category=cats,
                per_plugin=SC.r3(SC.rate(len(items), len(rows))))


def _holdout_proxy(rows):
    """Reviewer-category proxy on the HANCORE holdout. NOT S3 adjudication, NOT M1/M2: a finding counts as a 'category match' when its category is among the plugin's
    strong/likely reviewer categories (restricted to the seven focus categories). Negatives = plugins reviewers found nothing strong in."""
    kept = [(r, a) for r in rows if r["valid"] for a in r["out"]["added_findings"]]
    match = sum(a["category"] in (r["gt_focus"] or []) for r, a in kept)
    pos = [r for r in rows if r["holdout_label"] == "positive"]
    neg = [r for r in rows if r["holdout_label"] == "negative"]
    gt_n = sum(len(r["gt_focus"] or []) for r in rows)
    tp = sum(len(set(a["category"] for a in r["out"]["added_findings"]) & set(r["gt_focus"] or [])) for r in rows if r["valid"])

    def blk(r):
        return (not r["valid"]) or any(a["severity"] == "blocker" for a in r["out"]["added_findings"])
    nb = sum(blk(r) for r in neg)
    return dict(n=len(rows), positives=len(pos), negatives=len(neg), added_kept=len(kept), category_match_precision=SC.r3(SC.rate(match, len(kept))),
                category_match_precision_wilson=SC.wilson(match, len(kept)), focus_category_recall=SC.r3(SC.rate(tp, gt_n)), focus_category_recall_wilson=SC.wilson(tp, gt_n),
                negatives_with_blocker_or_invalid=nb, negatives_blocker_rate=SC.r3(SC.rate(nb, len(neg))), negatives_blocker_rate_wilson=SC.wilson(nb, len(neg)),
                added_per_negative=SC.r3(SC.rate(sum(len(r["out"]["added_findings"]) if r["valid"] else 1 for r in neg), len(neg))),
                caveat="reviewer-category proxy; a real added finding outside the reviewers' categories counts as a miss; not an S3 adjudication")


if __name__ == "__main__":
    main()
