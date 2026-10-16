"""ONE OpenRouter client for the data pipeline (audit A5 + Part I). Open-weights models only (qwen/qwen3.5-397b-a17b, openai/gpt-oss-120b).
  * fails CLOSED: call() returns {"_error": ...} on failure, never a pass; callers count it (stats()) and the build aborts above MAX_ERROR_RATE
  * failures are NEVER cached (a failure written once would be scored as a MISS forever)
  * retries 429/5xx/timeouts with backoff, not other 4xx (401 aborts at once); per-call timeout; a locked cost ledger with a hard cap (R_CAP)
  * replay: cache keys are identical to the r2-r4 helper (sha1 of [system,user,temperature,seed,tag,(model)]) so the published cache replays for free
Env: OPENROUTER_API_KEY (never printed), R_WORK (cache + ledger dir), R_CAP (USD cap for THIS run, default 4.5), R_SEED_CACHE (jsonl(.gz) replay cache)."""
import gzip, hashlib, json, os, re, threading, time, urllib.request, urllib.error

QWEN = "qwen/qwen3.5-397b-a17b"; GPT = "openai/gpt-oss-120b"; ALLOWED = {QWEN, GPT}
MAX_ERROR_RATE = 0.01
WORK = os.environ.get("R_WORK", "/tmp/usuba_r_work"); os.makedirs(WORK, exist_ok=True)
CAP = float(os.environ.get("R_CAP", "4.5")); CACHE = os.path.join(WORK, "cache.jsonl"); LEDGER = os.path.join(WORK, "ledger_r5.json")
_lk = threading.Lock(); _cache = {}; _stat = dict(calls=0, hits=0, live=0, errors=0, error_samples=[])
_spent = [json.load(open(LEDGER))["usd"] if os.path.exists(LEDGER) else 0.0]


def _load(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt") as f:
        for l in f:
            try: d = json.loads(l); _cache.setdefault(d["k"], d)
            except (ValueError, KeyError, TypeError): pass   # torn cache line: re-ask


for _p in (os.environ.get("R_SEED_CACHE"), CACHE):
    if _p and os.path.exists(_p): _load(_p)


def spent(): return _spent[0]
def stats(): return dict(_stat, spent_usd=round(_spent[0], 4), cache_entries=len(_cache))
def key(system, user, temperature=0.0, seed=None, tag="", model=None):
    return hashlib.sha1(json.dumps([system, user, temperature, seed, tag] + ([model] if model else [])).encode()).hexdigest()
def error_rate(): return _stat["errors"] / max(1, _stat["calls"])
def assert_error_budget():
    if _stat["calls"] >= 20 and error_rate() > MAX_ERROR_RATE:
        raise SystemExit(f"LLM GATE: error rate {error_rate():.1%} ({_stat['errors']}/{_stat['calls']}) above {MAX_ERROR_RATE:.0%}; aborting (fail closed). samples: {_stat['error_samples'][:3]}")


def call(system, user, tag="", temperature=0.0, max_tokens=6000, effort="none", seed=None, model=None):
    model = model or QWEN
    if model not in ALLOWED: raise ValueError(f"model {model} is not on the open-weights allow-list")
    k = key(system, user, temperature, seed, tag, model if model != QWEN else None)
    with _lk: _stat["calls"] += 1
    if k in _cache:
        with _lk: _stat["hits"] += 1
        return _cache[k]["out"]
    if _spent[0] > CAP: raise SystemExit(f"LLM budget cap {CAP} USD reached")
    req = dict(model=model, max_tokens=max_tokens, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], reasoning={"effort": effort},
               provider={"data_collection": "deny", "sort": "throughput"}, usage={"include": True}, temperature=temperature)
    if seed is not None: req["seed"] = seed
    err = ""
    for att in range(5):
        try:
            r = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(req).encode(),
                                       headers={"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"], "Content-Type": "application/json"})
            j = json.load(urllib.request.urlopen(r, timeout=120))
            t = j["choices"][0]["message"].get("content") or ""
            with _lk:
                _spent[0] += (j.get("usage") or {}).get("cost") or 0.0; json.dump({"usd": _spent[0]}, open(LEDGER, "w"))
            out = json.loads(re.search(r"\{.*\}", t, re.S).group(0))
            with _lk:
                _stat["live"] += 1; _cache[k] = dict(k=k, out=out, model=model, tag=tag); open(CACHE, "a").write(json.dumps(_cache[k]) + "\n")
            return out
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
            if e.code == 401: raise SystemExit("LLM GATE: 401 from OpenRouter (bad key); aborting")
            if e.code < 500 and e.code != 429: break
        except Exception as e: err = type(e).__name__
        time.sleep(2 + att * 3)
    with _lk:
        _stat["errors"] += 1
        if len(_stat["error_samples"]) < 10: _stat["error_samples"].append(err)
    return {"_error": err}
