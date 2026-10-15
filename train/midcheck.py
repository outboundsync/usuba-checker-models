#!/usr/bin/env python3
"""Mid-training check: does the model being trained NAME THE REAL BUG AT THE RIGHT file:line on held-out plugins?

Pool = rows of the training pool's val split whose gold answer (the assistant target) has at least one finding with a file and a
line number. Never Dell-key plugins (ids from functest/dell_ground_truth.jsonl, ids only; and every source starting 'dell_' by default)
and never the 329 holdout plugins (eval/hancore_holdout/plugin_ids.txt). A custom pool file (same row format) may be given, e.g. the
dedicated held-out line-citation set.
Score per plugin: file_hit (a predicted finding cites the gold file), line_hit (same file AND |line - gold| <= LINE_TOL, or inside the
gold line..line_end range) = 'names the real bug at the right file:line'. Also json_ok and verdict_ok.
Everything here is pure python (no torch import) except the default generator; run_midcheck never raises (training must not die).
Results: <out_dir>/midcheck.jsonl (one line per run, plus per-plugin details in midcheck_step-XXXXXX.json)."""
import json, os, re, time, traceback, gzip

LINE_TOL = 3
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _lines(path):
    op = gzip.open if str(path).endswith(".gz") else open
    with op(path, "rt") as f:
        return [json.loads(l) for l in f if l.strip()]

def parse_json(txt):
    txt = re.sub(r"<think>.*?</think>", "", txt or "", flags=re.S).strip()
    m = re.search(r"\{.*\}", txt, re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception: return None

def gold_findings(row):
    """[(file, line, line_end)] from the assistant target (the last message)."""
    out = parse_json(row["messages"][-1]["content"]) or {}
    g = []
    for f in out.get("findings") or []:
        if not isinstance(f, dict) or not f.get("file"): continue
        try: ln = int(f["line"])
        except Exception: continue
        try: le = int(f["line_end"]) if f.get("line_end") else None
        except Exception: le = None
        g.append((str(f["file"]), ln, le))
    return g

def _forbidden_ids():
    ids = set()
    p = os.path.join(ROOT, "functest", "dell_ground_truth.jsonl")
    if os.path.exists(p):
        for l in open(p):
            try: ids.add(json.loads(l)["id"].lower())     # ids only; labels are never read
            except Exception: pass
    return ids

def _holdout_names():
    p = os.path.join(ROOT, "eval", "hancore_holdout", "plugin_ids.txt")
    if not os.path.exists(p): return set()
    return {u.strip().lower().rstrip("/").removesuffix(".git").split("github.com/")[-1] for u in open(p).read().split()}

def row_excluded(row, forbidden_ids, holdout, allow_dell_sources=False):
    rid = str(row.get("id", "")).lower(); src = str(row.get("source", "")).lower()
    if not allow_dell_sources and (src.startswith("dell") or str(row.get("orig_source", "")).lower().startswith("dell")): return "dell_source"
    if any(i and i in rid for i in forbidden_ids): return "dell_key_id"
    if any(h and h.replace("/", "__") in rid.replace("/", "__") for h in holdout): return "holdout_plugin"
    return None

def build_pool(path, n=30, forbidden_ids=None, holdout=None, allow_dell_sources=False):
    forbidden_ids = _forbidden_ids() if forbidden_ids is None else forbidden_ids
    holdout = _holdout_names() if holdout is None else holdout
    pool, skipped = [], {}
    for r in _lines(path):
        if r.get("split") not in (None, "val") and "split" in r: continue
        why = row_excluded(r, forbidden_ids, holdout, allow_dell_sources)
        if not why and not gold_findings(r): why = "no_file_line_gold"
        if why: skipped[why] = skipped.get(why, 0) + 1; continue
        pool.append(r)
    pool.sort(key=lambda r: r.get("id", ""))          # deterministic
    return pool[:n], skipped

def score_one(row, response):
    gold = gold_findings(row); out = parse_json(response)
    res = dict(id=row.get("id"), json_ok=out is not None, file_hit=False, line_hit=False, verdict_ok=None, n_gold=len(gold))
    if out is None: return res
    res["verdict_ok"] = out.get("verdict") == (parse_json(row["messages"][-1]["content"]) or {}).get("verdict")
    for f in out.get("findings") or []:
        if not isinstance(f, dict) or not f.get("file"): continue
        pf = str(f["file"]).lstrip("./")
        try: pl = int(f.get("line")) if f.get("line") is not None else None
        except Exception: pl = None
        for gf, gl, ge in gold:
            gfn = gf.lstrip("./")
            if not (pf == gfn or pf.endswith("/" + gfn) or gfn.endswith("/" + pf) or os.path.basename(pf) == os.path.basename(gfn)): continue
            res["file_hit"] = True
            if pl is not None and (abs(pl - gl) <= LINE_TOL or (ge and gl - LINE_TOL <= pl <= ge + LINE_TOL)): res["line_hit"] = True
    return res

def summarize(results):
    n = len(results)
    r = lambda k: round(sum(1 for x in results if x.get(k)) / n, 3) if n else None
    return dict(n=n, line_hit=r("line_hit"), file_hit=r("file_hit"), json_ok=r("json_ok"),
                verdict_ok=round(sum(1 for x in results if x.get("verdict_ok")) / n, 3) if n else None)

def hf_generator(model, tok, max_new=400, enable_thinking=False):
    """Greedy generation with the in-memory (training) model. Restores train state; caller wraps in try/except."""
    import torch
    def gen(msgs):
        ids = tok.apply_chat_template(msgs[:-1] if msgs[-1]["role"] == "assistant" else msgs, tokenize=True, add_generation_prompt=True, enable_thinking=enable_thinking)
        if hasattr(ids, "input_ids"): ids = ids["input_ids"]
        x = torch.tensor([ids], device=next(model.parameters()).device)
        with torch.no_grad():
            y = model.generate(input_ids=x, attention_mask=torch.ones_like(x), max_new_tokens=max_new, do_sample=False, use_cache=True)
        return tok.decode(y[0, x.size(1):], skip_special_tokens=True)
    return gen

def run_midcheck(step, rows, generate, out_dir, log=None, max_secs=1200, tag=None):
    """Never raises. generate(messages)->str. Returns summary dict or None."""
    try:
        t0 = time.time(); results = []
        for r in rows:
            if time.time() - t0 > max_secs: break
            try: resp = generate(r["messages"])
            except Exception as e: resp = ""; print(f"[midcheck] generate failed for {r.get('id')}: {type(e).__name__}", flush=True)
            results.append(score_one(r, resp))
        s = summarize(results); s.update(step=step, tag=tag or f"step-{step}", secs=round(time.time() - t0, 1), planned=len(rows), time=time.time())
        os.makedirs(out_dir, exist_ok=True)
        json.dump(dict(summary=s, results=results), open(os.path.join(out_dir, f"midcheck_{s['tag']}.json"), "w"), indent=1)
        with open(os.path.join(out_dir, "midcheck.jsonl"), "a") as f: f.write(json.dumps(s) + "\n")
        line = json.dumps(dict(midcheck=s))
        print(line, flush=True)
        if log is not None: log.write(line + "\n"); log.flush()
        return s
    except Exception:
        print("[midcheck] failed (ignored):", traceback.format_exc()[-400:], flush=True)
        return None
