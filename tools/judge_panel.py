#!/usr/bin/env python3
"""PROVISIONAL open-weights judge panel for labelling (S1 findings, S3 added findings, S2 candidates).

Every item goes to three distinct open-weights models through OpenRouter. Votes, majority label, agreement and a human-review flag are recorded.
All output is PROVISIONAL: a panel label is a triage signal, never ground truth. Items the panel disagrees on, or that any judge marks unsure,
are flagged `needs_human`. Nothing here is used for training labels without a human pass.

Rules enforced in code:
  * no Anthropic/Claude judge, no proprietary OpenAI judge (only openai/gpt-oss-*); anything else must be on the OPEN_OK list (open weights)
  * three DISTINCT models (distinct families are checked by the id prefix)
  * hard spend cap (default $8, `--budget`), tracked from OpenRouter `usage.cost`, persisted in a ledger so re-runs and parallel runs add up; no call is
    started once the ledger plus an estimate for the call would pass the cap
  * zero data retention routing; the key is read from $OPENROUTER_API_KEY and never printed or stored

Input  JSONL, one item per line:
  {"id": "...", "kind": "S1|S3|S2", "plugin": "owner/repo or id", "rule": "USB-HC10" (S1/S3), "claim": "what the Checker/draft says is wrong",
   "file": "path", "line": 12, "context": "code around the finding (S1/S3) or a digest of the plugin (S2)", "evidence": "optional hardware/runtime evidence"}
Labels: S1/S3 -> real | false_alarm | unsure      S2 -> clean | not_clean | unsure
Output (--out DIR): votes.jsonl (one record per item), summary.json, review_queue.jsonl (flagged items), ledger.json

  python3 tools/judge_panel.py items.jsonl --out runs/panel1 [--budget 8] [--limit N] [--workers 6] [--dry-run]
"""

import argparse
import collections
import hashlib
import itertools
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

DEFAULT_PANEL = ["qwen/qwen3.5-397b-a17b", "openai/gpt-oss-120b", "deepseek/deepseek-v3.2"]
OPEN_OK = ("qwen/", "openai/gpt-oss-", "deepseek/", "z-ai/glm", "moonshotai/kimi", "meta-llama/", "mistralai/mistral-large", "minimax/")
LABELS = {"S1": ("real", "false_alarm", "unsure"), "S3": ("real", "false_alarm", "unsure"), "S2": ("clean", "not_clean", "unsure")}
URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_CTX = 9000
PRICE_FALLBACK = {"qwen/qwen3.5-397b-a17b": (5e-7, 3.6e-6), "openai/gpt-oss-120b": (1.5e-7, 6e-7), "deepseek/deepseek-v3.2": (2.6e-7, 8e-7)}

SYSTEM = (
    "You are one member of a panel of independent reviewers of third-party plugins for the Omarchy Quickshell desktop shell (QML, JS, shell and Python code). "
    "Your label is a provisional triage signal that a human will audit. Judge only from the evidence given; if it is not enough, answer unsure. "
    'Reply with ONE JSON object and nothing else: {"label": "...", "confidence": 0.0-1.0, "reason": "one or two sentences"}.'
)

TASK = {
    "S1": "A static Checker flagged the plugin code below. Is the finding REAL (the code really has this defect or risk on a normal user's machine) or a FALSE_ALARM (the pattern is harmless or guarded in context)? Labels: real | false_alarm | unsure.",
    "S3": "A drafted finding was ADDED to the plugin's review. Is the finding REAL (supported by the code) or a FALSE_ALARM (not supported, harmless or already guarded)? Labels: real | false_alarm | unsure.",
    "S2": "This plugin is a candidate for the CLEAN set: it loads on real hardware, passes the static Checker, and should have no security problem, destructive command, hidden network or data exfiltration, privilege escalation or unsafe file handling. Is it clean? Labels: clean | not_clean | unsure.",
}


def check_models(models):
    if len(set(models)) != len(models):
        sys.exit("panel models must be distinct")
    fam = [m.split("/")[0] for m in models]
    if len(set(fam)) != len(fam):
        sys.exit(f"panel must use distinct model families, got {fam}")
    for m in models:
        ml = m.lower()
        if ml.startswith("anthropic/") or "claude" in ml:
            sys.exit(f"refusing {m}: Anthropic/Claude models may not be judges (provider terms)")
        if ml.startswith("openai/") and not ml.startswith("openai/gpt-oss-"):
            sys.exit(f"refusing {m}: only open-weights OpenAI models (gpt-oss) allowed")
        if not ml.startswith(OPEN_OK):
            sys.exit(f"refusing {m}: not on the open-weights allow list {OPEN_OK}")


def build_prompt(item):
    kind = item["kind"]
    parts = [TASK[kind], "", f"Plugin: {item.get('plugin', '?')}"]
    if item.get("rule"):
        parts.append(f"Rule: {item['rule']}")
    if item.get("claim"):
        parts.append(f"Claim: {item['claim']}")
    if item.get("file"):
        parts.append(f"Location: {item['file']}" + (f":{item['line']}" if item.get("line") else ""))
    if item.get("evidence"):
        parts.append(f"Runtime evidence: {str(item['evidence'])[:1500]}")
    parts += [
        "",
        "Code / context:",
        "```",
        str(item.get("context", ""))[:MAX_CTX],
        "```",
        "",
        f"Answer with JSON; label must be one of {' | '.join(LABELS[kind])}.",
    ]
    return "\n".join(parts)


def parse_vote(text, kind):
    """-> (label, confidence, reason) or None when unparseable / label not allowed"""
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
    except (ValueError, OSError, TypeError):
        return None
    lab = str(o.get("label", "")).strip().lower().replace("-", "_").replace(" ", "_")
    if lab not in LABELS[kind]:
        return None
    try:
        conf = max(0.0, min(1.0, float(o.get("confidence", 0.5))))
    except (ValueError, OSError, TypeError):
        conf = 0.5
    return lab, conf, str(o.get("reason", ""))[:400]


class Ledger:
    """persistent spend ledger: total USD per ledger file, thread-safe, cap enforced BEFORE each call"""

    def __init__(self, path, cap):
        self.path, self.cap, self.lock = path, cap, threading.Lock()
        try:
            self.d = json.load(open(path))
        except (ValueError, OSError, TypeError):
            self.d = {"spent": 0.0, "calls": 0, "by_model": {}}

    def reserve_ok(self, est):
        with self.lock:
            return self.d["spent"] + est <= self.cap

    def add(self, model, cost):
        with self.lock:
            self.d["spent"] += cost
            self.d["calls"] += 1
            self.d["by_model"][model] = self.d["by_model"].get(model, 0.0) + cost
            tmp = self.path + ".tmp"
            json.dump(self.d, open(tmp, "w"), indent=1)
            os.replace(tmp, self.path)


def call_openrouter(model, prompt, key, max_tokens=2500, timeout=180):
    body = dict(
        model=model,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=max_tokens,
        reasoning={"effort": "low"},
        provider={"zdr": True, "data_collection": "deny"},
        usage={"include": True},
    )
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (fixed https URL)
        j = json.load(r)
    msg = j["choices"][0]["message"]
    return msg.get("content") or "", float((j.get("usage") or {}).get("cost") or 0.0), j["choices"][0].get("finish_reason")


def est_cost(model, prompt):
    pi, po = PRICE_FALLBACK.get(model, (1e-6, 4e-6))
    return len(prompt) / 3.5 * pi + 1500 * po


def vote_one(model, item, prompt, ledger, cache, key, call=call_openrouter, retries=2):
    ck = hashlib.sha256((model + "\0" + prompt).encode()).hexdigest()
    if ck in cache:
        return dict(cache[ck], cached=True)
    err = None
    for attempt in range(retries + 1):
        if not ledger.reserve_ok(est_cost(model, prompt)):
            return dict(model=model, label=None, error="budget cap reached", cost=0.0)
        try:
            text, cost, fin = call(model, prompt, key)
            ledger.add(model, cost)
            v = parse_vote(text, item["kind"])
            if v:
                return dict(model=model, label=v[0], confidence=v[1], reason=v[2], cost=cost, finish=fin)
            err = f"unparseable output (finish={fin})"
        except urllib.error.HTTPError as e:
            err = f"http {e.code}"
            if e.code in (401, 402, 403):
                break
        except (OSError, ValueError, KeyError, IndexError, TypeError) as e:  # network, timeout, bad json: record and retry
            err = type(e).__name__ + ": " + str(e)[:120]
        time.sleep(2 * (attempt + 1))
    return dict(model=model, label=None, error=err, cost=0.0)  # a failed call is an ABSTAIN, never a vote


def aggregate(item, votes):
    kind = item["kind"]
    valid = [v for v in votes if v.get("label")]
    cnt = collections.Counter(v["label"] for v in valid)
    top = cnt.most_common()
    majority = top[0][0] if top and (len(top) == 1 or top[0][1] > top[1][1]) and top[0][1] * 2 > len(votes) else "no_majority"
    unanimous = len(valid) == len(votes) and len(cnt) == 1
    reasons = []
    if len(valid) < len(votes):
        reasons.append("missing_vote")
    if len(cnt) > 1:
        reasons.append("disagreement")
    if any(v["label"] == "unsure" for v in valid):
        reasons.append("unsure_vote")
    if majority == "unsure":
        reasons.append("majority_unsure")
    if majority == "no_majority":
        reasons.append("no_majority")
    if valid and sum(v.get("confidence", 0) for v in valid) / len(valid) < 0.6:
        reasons.append("low_confidence")
    return dict(
        id=item["id"],
        kind=kind,
        plugin=item.get("plugin"),
        rule=item.get("rule"),
        provisional=True,
        votes=votes,
        majority=majority,
        unanimous=unanimous,
        n_valid=len(valid),
        needs_human=bool(reasons),
        review_reasons=reasons,
    )


def fleiss_kappa(rows, labels):
    """rows: list of Counter per item with equal number of raters n"""
    rows = [r for r in rows if sum(r.values()) >= 2]
    if not rows:
        return None
    N = len(rows)
    P_i = [(sum(c * c for c in r.values()) - sum(r.values())) / (sum(r.values()) * (sum(r.values()) - 1)) for r in rows]
    tot = sum(sum(r.values()) for r in rows)
    p_j = [sum(r.get(lab, 0) for r in rows) / tot for lab in labels]
    Pe = sum(p * p for p in p_j)
    Pbar = sum(P_i) / N
    return None if Pe >= 1 else round((Pbar - Pe) / (1 - Pe), 4)


def cohen_kappa(a, b, labels):
    pairs = [(x, y) for x, y in zip(a, b, strict=True) if x and y]
    if not pairs:
        return None, None, 0
    n = len(pairs)
    po = sum(x == y for x, y in pairs) / n
    pe = sum((sum(x == lab for x, _ in pairs) / n) * (sum(y == lab for _, y in pairs) / n) for lab in labels)
    return po, (None if pe >= 1 else round((po - pe) / (1 - pe), 4)), n


def summarize(recs, models, ledger):
    out = dict(provisional=True, panel=models, n_items=len(recs), spent_usd=round(ledger.d["spent"], 4), calls=ledger.d["calls"])
    out["by_kind"] = {}
    for kind in sorted({r["kind"] for r in recs}):
        rs = [r for r in recs if r["kind"] == kind]
        labs = LABELS[kind]
        k = dict(
            n=len(rs),
            majority=dict(collections.Counter(r["majority"] for r in rs)),
            unanimous_rate=round(sum(r["unanimous"] for r in rs) / len(rs), 4),
            needs_human=sum(r["needs_human"] for r in rs),
            needs_human_rate=round(sum(r["needs_human"] for r in rs) / len(rs), 4),
        )
        k["fleiss_kappa"] = fleiss_kappa([collections.Counter(v["label"] for v in r["votes"] if v.get("label")) for r in rs], labs)
        pw = {}
        for a, b in itertools.combinations(models, 2):
            va = [next((v["label"] for v in r["votes"] if v["model"] == a), None) for r in rs]
            vb = [next((v["label"] for v in r["votes"] if v["model"] == b), None) for r in rs]
            po, ka, n = cohen_kappa(va, vb, labs)
            pw[f"{a} | {b}"] = dict(n=n, agreement=None if po is None else round(po, 4), cohen_kappa=ka)
        k["pairwise"] = pw
        k["per_model_label_counts"] = {
            m: dict(collections.Counter(v["label"] for r in rs for v in r["votes"] if v["model"] == m and v.get("label"))) for m in models
        }
        k["failed_calls"] = {m: sum(1 for r in rs for v in r["votes"] if v["model"] == m and not v.get("label")) for m in models}
        out["by_kind"][kind] = k
    return out


def load_items(path, limit=0):
    items = []
    for ln, line in enumerate(open(path, encoding="utf-8")):
        if not line.strip():
            continue
        it = json.loads(line)
        if it.get("kind") not in LABELS or not it.get("id"):
            sys.exit(f"{path}:{ln + 1}: item needs id and kind in {list(LABELS)}")
        items.append(it)
    ids = [i["id"] for i in items]
    if len(set(ids)) != len(ids):
        sys.exit("duplicate item ids")
    return items[:limit] if limit else items


def run(items, models, out, budget, workers=6, key=None, call=call_openrouter):
    os.makedirs(out, exist_ok=True)
    ledger = Ledger(os.path.join(out, "ledger.json"), budget)
    cpath = os.path.join(out, "cache.jsonl")
    cache = {}
    if os.path.exists(cpath):
        for line in open(cpath):
            try:
                d = json.loads(line)
                cache[d["ck"]] = d["vote"]
            except (ValueError, OSError, TypeError):
                continue  # a torn last line from an interrupted run is simply re-asked
    clock = threading.Lock()

    def task(pair):
        item, model = pair
        prompt = build_prompt(item)
        v = vote_one(model, item, prompt, ledger, cache, key, call)
        if v.get("label") and not v.get("cached"):
            with clock, open(cpath, "a") as f:
                f.write(json.dumps(dict(ck=hashlib.sha256((model + "\0" + prompt).encode()).hexdigest(), vote=v)) + "\n")
        return item["id"], v

    res = collections.defaultdict(dict)
    with ThreadPoolExecutor(workers) as ex:
        for iid, v in ex.map(task, [(i, m) for i in items for m in models]):
            res[iid][v["model"]] = v
    recs = []
    for it in items:
        votes = [dict(res[it["id"]][m], model=m) for m in models]
        for v in votes:
            v.pop("cached", None)
        recs.append(aggregate(it, votes))
    with open(os.path.join(out, "votes.jsonl"), "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in recs)
    with open(os.path.join(out, "review_queue.jsonl"), "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in recs if r["needs_human"])
    s = summarize(recs, models, ledger)
    json.dump(s, open(os.path.join(out, "summary.json"), "w"), indent=1)
    return recs, s


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("items")
    ap.add_argument("--out", required=True)
    ap.add_argument("--models", default=",".join(DEFAULT_PANEL), help="exactly three distinct open-weights OpenRouter ids")
    ap.add_argument("--budget", type=float, default=8.0, help="hard cap in USD for this output directory's ledger (default 8)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true", help="print the first prompt and a cost estimate, call nothing")
    a = ap.parse_args()
    models = [m.strip() for m in a.models.split(",")]
    if len(models) != 3:
        sys.exit("the panel is exactly three models")
    check_models(models)
    items = load_items(a.items, a.limit)
    est = sum(est_cost(m, build_prompt(i)) for i in items for m in models)
    print(f"{len(items)} items x 3 judges; rough upper-bound cost ${est:.2f} (cap ${a.budget:.2f})", file=sys.stderr)
    if a.dry_run:
        print(build_prompt(items[0]))
        return
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("ABORT: $OPENROUTER_API_KEY not set (a missing key would otherwise look like 'every judge failed')")
    recs, s = run(items, models, a.out, a.budget, a.workers, key)
    print(json.dumps(s, indent=1))
    print(
        f"PROVISIONAL. {s['by_kind'] and sum(k['needs_human'] for k in s['by_kind'].values())} of {len(recs)} items flagged for human review -> {a.out}/review_queue.jsonl",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
