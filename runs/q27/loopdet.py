"""Loop detection for generated answers (shared by score49.py and runs/rl/pass_at_k.py)."""
import re, collections, zlib
_TANDEM = re.compile(r"(\S.{1,79}?)\1{7,}", re.S)
def _tandem(t):
    # substring repeated back-to-back >=8 times (e.g. '...AndUnitAndUnitAndUnit...'); unit must contain an alnum char
    for m in _TANDEM.finditer(t):
        if re.search(r"[A-Za-z0-9]", m.group(1)) and len(m.group(0)) >= 120: return True
    return False
def _ngram(t, n=30, k=20):
    # token n-gram (n=30) repeated >=k times covering >=25% of tokens, ignoring separator-only grams
    toks = re.findall(r"\w+|[^\w\s]", t)
    if len(toks) < n * k: return False
    c = collections.Counter(tuple(toks[i:i + n]) for i in range(0, len(toks) - n, 1))
    for g, v in c.most_common(5):
        if v < k: break
        if len({x for x in g if re.match(r"\w", x)}) >= 6 and v * n >= 0.25 * len(toks): return True
    return False
def _compress(t, w=20000, thr=0.06):
    # tail of the answer compresses far too well (catches counter loops like prop785/prop786/... that differ every line).
    # calibration: clean_b/clean_w loops 0.002-0.015; frontier (GPT-5.6, Opus, Gemini, Kimi) min 0.118
    s = t[-w:].encode()
    return len(s) >= 4000 and len(zlib.compress(s, 9)) / len(s) < thr
def loopy(t):
    if _compress(t): return True
    lines = [l for l in t.splitlines() if l.strip()]
    if len(lines) > 50 and collections.Counter(lines).most_common(1)[0][1] > max(30, len(lines) // 5): return True
    return _tandem(t) or _ngram(t)
