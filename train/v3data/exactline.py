"""Exact-line anchoring + the automated 'cited line contains the described construct' check (shared by refine_r2.py, gate_report.py, make_samples.py).
A finding's constructs = backticked identifiers/commands in its prose (bare file refs, numbers and 3-char fragments excluded). A cited line passes when
a construct occurs ON the cited line ('strict'), or in the same statement spanning at most 2 lines (L..L+1, 'two_line'); blank lines and comment lines never pass."""
import re
SPAN = re.compile(r"`([^`\n]{2,120})`")
FILE_RE = r"[\w./@+-]+\.(?:qml|js|mjs|sh|py|lua|json|bash|conf|toml|md|css|service|desktop|txt|yml|yaml)"
STOP = {"import", "function", "return", "const", "string", "number", "false", "break", "continue", "command", "property", "Process", "model", "value", "state", "config", "script", "input", "output", "result", "error", "timer", "index", "label", "color", "width", "height", "source", "target", "default", "bash", "sh", "text", "true", "false", "null", "this", "from", "with", "name", "data", "file", "path", "line", "root", "item", "none", "self", "type", "size", "mode", "list", "open", "read", "args", "args"}
COMMENT = ("//", "#", "/*", "*", "--", ";")
def is_comment(path, line):
    s = line.strip()
    if path.lower().endswith((".md", ".txt", ".json")): return False
    return s.startswith(COMMENT) if not (path.lower().endswith(".qml") and s.startswith("#")) else s.startswith("#")
def spans(finding):
    out = []
    for m in SPAN.finditer(finding):
        sp = m.group(1).strip()
        if re.fullmatch(FILE_RE + r"(:[\d,\- :]+)?", sp) or re.fullmatch(r"[:,\d\- ]+", sp) or re.fullmatch(r"\d[\d,\- ]*", sp): continue
        out.append(sp)
    return out
LOOSE_STOP = {"stock", "omarchy", "plugin", "shell", "quickshell", "hyprland", "manifest", "entrypoints", "stdiocollector", "qt", "qml"}
def loose_spans(finding):
    """fallback when the prose has no backticks: dotted/camelCase/snake_case/call-like identifiers and paths (>=5 chars)"""
    out = []
    for m in re.finditer(r"[A-Za-z_$][\w$]*(?:[./:][A-Za-z_$][\w$]*)+(?:\(\))?|[A-Za-z_][\w]*\(\)|\b[a-z]+[A-Z][A-Za-z0-9]*\b|\b[A-Z][a-z0-9]+[A-Z][A-Za-z0-9]*\b|\b\w+_\w+\b|\b[a-z][a-z0-9]*(?:-[a-z0-9]+)+\b", finding):
        t = m.group(0).rstrip(".:"); t = t[:-2] if t.endswith("()") else t
        if len(t) >= 5 and not re.fullmatch(FILE_RE, t) and t.lower() not in LOOSE_STOP and not re.fullmatch(r"\d[\d.]*", t) and not t.lower().startswith(("e.g", "i.e")) and t not in out: out.append(t)
    return out
def variants(sp):
    v = []
    if "..." in sp or "…" in sp:
        parts = [x.strip() for x in re.split(r"\.\.\.|…", sp) if len(x.strip()) >= 3]
        if parts: v.append(("RX", ".*?".join(re.escape(x) for x in parts)))
    if "(" in sp and sp.index("(") >= 3: v.append(sp[:sp.index("(") + 1])
    v += [sp, sp.rstrip(".").rstrip(","), re.sub(r"\(.*?\)?$", "", sp), re.sub(r"[()]+$", "", sp)]
    v += [t for t in re.split(r"[\s|;&=,{}()\[\]\"'<>]+", sp) if t]
    v += [t.lstrip("-$@") for t in list(v) if isinstance(t, str)]
    out = []
    for c in v:
        if isinstance(c, tuple): out.append(c); continue
        c = c.strip()
        if len(c) >= 4 and c.lower() not in {x.lower() for x in STOP} and (c == sp.strip() or len(c) >= 6 or re.search(r"[._/\-()$:]|\d", c) or (re.search(r"[A-Z]", c) and re.search(r"[a-z]", c))) and not re.fullmatch(r"[\d.:/-]+", c) and c not in out: out.append(c)
    return out
def _in(c, text):
    if isinstance(c, tuple): return bool(re.search(c[1], text))
    if re.fullmatch(r"[\w$]+", c): return bool(re.search(r"(?<![\w$])" + re.escape(c) + r"(?![\w$])", text))
    return c in text
def hits(finding, text):
    """weighted match score of the finding's constructs in `text` (0 = none)"""
    sc = 0.0
    for i, sp in enumerate(spans(finding)):
        w = 1.0 / (1 + i)
        for j, c in enumerate(variants(sp)):
            if _in(c, text): sc += w * (1.0 if j == 0 else 0.6); break
    return sc
def check(finding, lines, L, path=""):
    """-> 'strict' | 'two_line' | 'fail' | 'blank_or_comment' | 'nocheck' (finding names no checkable construct) | 'out_of_range'"""
    if not isinstance(L, int) or L < 1 or L > len(lines): return "out_of_range"
    loose = False
    if not spans(finding) or not any(variants(s) for s in spans(finding)):
        if not loose_spans(finding): return "nocheck"
        loose = True
    ln = lines[L - 1]
    if not ln.strip() or is_comment(path, ln): return "blank_or_comment"
    h = (lambda t: any(_in(c, t) for c in loose_spans(finding))) if loose else (lambda t: hits(finding, t))
    if h(ln): return "strict"
    if L < len(lines) and h(ln + "\n" + lines[L]) and not lines[L].strip().startswith(("}", ")")): return "two_line"
    return "fail"
def anchor(finding, lines, L0, path="", before=12, after=60, far=150):
    """best line for the finding near L0: highest construct score on a non-blank non-comment line; ties -> nearest at/after L0. None if no candidate."""
    best = None
    if not spans(finding) and loose_spans(finding):   # loose constructs
        ls = loose_spans(finding); cand = [L for L in range(1, len(lines) + 1) if lines[L - 1].strip() and not is_comment(path, lines[L - 1]) and any(_in(c, lines[L - 1]) for c in ls) and abs(L - L0) <= far]
        return min(cand, key=lambda L: (abs(L - L0))) if cand else None
    for L in range(max(1, L0 - before), min(len(lines), L0 + after) + 1):
        ln = lines[L - 1]
        if not ln.strip() or is_comment(path, ln): continue
        s = hits(finding, ln)
        if not s: continue
        key = (-round(s, 3), abs(L - L0) if L >= L0 else abs(L - L0) + 1.5)
        if best is None or key < best[0]: best = (key, L)
    if best: return best[1]
    for L in sorted(range(max(1, L0 - far), min(len(lines), L0 + far) + 1), key=lambda x: abs(x - L0)):   # wider fallback, nearest hit
        ln = lines[L - 1]
        if ln.strip() and not is_comment(path, ln) and hits(finding, ln): return L
    return None
def candidates(finding, lines, path="", cap=30):
    return [L for L in range(1, len(lines) + 1) if lines[L - 1].strip() and not is_comment(path, lines[L - 1]) and hits(finding, lines[L - 1])][:cap]
REF = r"[\w./@+-]*:\d+(?:[-–—]\d+)?(?:\s*[,;]\s*(?:and\s+)?`?:?\d+(?:[-–—]\d+)?`?)*"
def strip_line_refs(t):
    """remove stale 'file:12-34' / ':40-43' / 'lines 38-56' references from prose (the cited line lives in the structured field)"""
    t = re.sub(r"(?<=\d)[–—](?=\d)", "-", t)
    def par(m):   # parenthetical made only of refs / arrows / punctuation -> removed
        inner = m.group(1); rest = re.sub(r"`?" + REF + r"`?|`?\d+(?:-\d+)?`?|→|->|,|;|\band\b|\bplus\b|`", "", inner)
        return "" if not rest.strip() else m.group(0)
    t = re.sub(r"\(([^()]*)\)", par, t)
    t = re.sub(r"\s+(?:at|in|on|from|via|near|see|to)\s+`?" + REF + r"`?(?=[\s,.;:)]|$)", "", t)               # 'at `:90`' -> ''
    t = re.sub(r"`(" + FILE_RE + r"|[\w./@+-]+)(?::\d+(?:-\d+)?(?:\s*[,;]\s*\d+(?:-\d+)?)*)`", r"`\1`", t)            # `file:12-34` -> `file`
    t = re.sub(r"(?<![`\w])([\w./@+-]+\.\w{1,5}):\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*", r"\1", t)                         # bare file.ext:12
    t = re.sub(r"(`[^`\n]+`)(?:\s*[,/]\s*(?:and\s+)?`?:?\d+(?:-\d+)?`?)+", r"\1", t)                                   # `x` , `197`, `212`
    t = re.sub(r",?\s*(?:and\s+)?`:\d+(?:-\d+)?`", "", t)
    t = re.sub(r"\s*\blines? \d+(?:-\d+)?\b", "", t)
    t = re.sub(r"\s+([,.;:])", r"\1", t); t = re.sub(r"\s{2,}", " ", t)
    return t.strip()
ARTIFACT = re.compile(r"`?[\w./-]*:\d+|\b(?:at|in|on|from)\s*(?:[,.;]|and\b|passes\b|for\b|with\b|then\b)|\bat\s*$|\d[-–]\d|\(\s*\)|\bat and\b|`\d+`")
def has_artifact(t): return bool(ARTIFACT.search(t)) or t.count("`") % 2 == 1
FILEBLK = re.compile(r"\n\n### (.+?)\n```\n(.*?)\n```(?=\n\n### |\Z)", re.S)
def parse_files(u):
    """plugin files from the last user message (robust to ``` fences inside README/markdown files)"""
    i = u.find("## Plugin source"); s = u[i + len("## Plugin source"):] if i >= 0 else u
    return {m.group(1): m.group(2) for m in FILEBLK.finditer(s)}
