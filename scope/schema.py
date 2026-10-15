"""Output schema of the Checker model (scope prompt v4) and its strict validator.

    {"scripts_triage": [{"rule", "file", "line", "decision", "reason", "quote"}],
     "added_findings": [{"category", "severity", "file", "line", "quote", "finding", "fix"}],
     "verdict": "approve" | "changes_requested"}

Pure functions, no I/O. An answer that fails ``validate`` is INVALID and scores as wrong (never as an approval or a dismissal).
Two layers: ``structure_errors`` (shape and enums) and ``coverage_errors`` (the triage list must address every Checker scripts finding exactly once).
"""
import json
import re

TOP_KEYS = ("scripts_triage", "added_findings", "verdict")
TRIAGE_KEYS = ("rule", "file", "line", "decision", "reason", "quote")
ADDED_KEYS = ("category", "severity", "file", "line", "quote", "finding", "fix")
DECISIONS = ("confirm", "dismiss")
SEVERITIES = ("blocker", "warning")
VERDICTS = ("approve", "changes_requested")
# the seven extend-focus categories; slugs are the shared scorer's canonical names (eval/hancore_holdout/scoring.py SCORED)
ADDED_CATEGORIES = (
    "secrets-credentials", "url-scheme-network", "rich-text-markup-injection", "remote-code-pinning",
    "scope-policy-duplicate", "listing-metadata-docs", "user-config-modification",
)
MAX_ADDED = 8
MAX_REASON = 240
MAX_TEXT = 600


def extract_json(txt):
    """First balanced JSON object in ``txt`` that parses (drops <think> blocks and code fences). None if there is none."""
    txt = re.sub(r"<think>.*?</think>", "", txt or "", flags=re.S).strip()
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", txt):
        try:
            obj, _ = dec.raw_decode(txt[m.start():])
        except ValueError:
            continue
        if isinstance(obj, dict) and (set(obj) & set(TOP_KEYS)):
            return obj
    return None


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _nonempty(x, limit):
    return isinstance(x, str) and bool(x.strip()) and len(x) <= limit


def structure_errors(out):
    """Shape/enum violations of a parsed answer (empty list = well formed)."""
    if not isinstance(out, dict):
        return ["not an object"]
    errs = []
    extra = set(out) - set(TOP_KEYS)
    missing = [k for k in TOP_KEYS if k not in out]
    if extra:
        errs.append("unknown top-level keys %s" % sorted(extra))
    if missing:
        errs.append("missing top-level keys %s" % missing)
    if out.get("verdict") not in VERDICTS:
        errs.append("verdict must be one of %s" % (VERDICTS,))
    tri = out.get("scripts_triage")
    if not isinstance(tri, list):
        errs.append("scripts_triage must be a list")
        tri = []
    for i, t in enumerate(tri):
        if not isinstance(t, dict):
            errs.append("scripts_triage[%d] not an object" % i)
            continue
        if set(t) != set(TRIAGE_KEYS):
            errs.append("scripts_triage[%d] keys must be exactly %s" % (i, list(TRIAGE_KEYS)))
            continue
        if not _nonempty(t["rule"], 40):
            errs.append("scripts_triage[%d].rule" % i)
        if not isinstance(t["file"], str):
            errs.append("scripts_triage[%d].file" % i)
        if t["line"] is not None and not (_is_int(t["line"]) and t["line"] >= 0):
            errs.append("scripts_triage[%d].line" % i)
        if t["decision"] not in DECISIONS:
            errs.append("scripts_triage[%d].decision" % i)
        if not _nonempty(t["reason"], MAX_REASON) or "\n" in t["reason"]:
            errs.append("scripts_triage[%d].reason must be one non-empty line <= %d chars" % (i, MAX_REASON))
        if not _nonempty(t["quote"], MAX_TEXT):
            errs.append("scripts_triage[%d].quote" % i)
    add = out.get("added_findings")
    if not isinstance(add, list):
        errs.append("added_findings must be a list")
        add = []
    if len(add) > MAX_ADDED:
        errs.append("added_findings has more than %d items" % MAX_ADDED)
    for i, a in enumerate(add):
        if not isinstance(a, dict):
            errs.append("added_findings[%d] not an object" % i)
            continue
        if set(a) != set(ADDED_KEYS):
            errs.append("added_findings[%d] keys must be exactly %s" % (i, list(ADDED_KEYS)))
            continue
        if a["category"] not in ADDED_CATEGORIES:
            errs.append("added_findings[%d].category not one of the focus slugs" % i)
        if a["severity"] not in SEVERITIES:
            errs.append("added_findings[%d].severity" % i)
        if not _nonempty(a["file"], 300):
            errs.append("added_findings[%d].file" % i)
        if not (_is_int(a["line"]) and a["line"] >= 1):
            errs.append("added_findings[%d].line must be an integer >= 1" % i)
        for k in ("quote", "finding", "fix"):
            if not _nonempty(a[k], MAX_TEXT):
                errs.append("added_findings[%d].%s" % (i, k))
    return errs


def finding_key(rule, file, line):
    return (str(rule), str(file or ""), int(line or 0))


def coverage_errors(out, findings):
    """The triage list must address every Checker scripts finding exactly once and nothing else. ``findings``: list of dicts with rule, file, line."""
    want = [finding_key(f["rule"], f.get("file"), f.get("line")) for f in findings]
    got = [finding_key(t["rule"], t["file"], t["line"]) for t in out.get("scripts_triage", []) if isinstance(t, dict) and set(t) == set(TRIAGE_KEYS)]
    errs = []
    if sorted(want) != sorted(got):
        miss = [k for k in want if k not in got]
        extra = [k for k in got if k not in want]
        dup = len(got) - len(set(got))
        errs.append("triage does not match the report: %d missing, %d unknown, %d duplicated" % (len(miss), len(extra), dup))
    return errs


def validate(out, findings=None):
    """All violations (structure + coverage when ``findings`` is given). Empty list = valid."""
    errs = structure_errors(out)
    if not errs and findings is not None:
        errs += coverage_errors(out, findings)
    return errs


def parse_answer(raw, findings=None, finish_reason=None):
    """raw model text -> (out, invalid_reason). Exactly one is None. Truncation, errors and schema violations are INVALID."""
    raw = raw or ""
    if raw.startswith("ERROR "):
        return None, "error"
    if raw.startswith("SKIPPED"):
        return None, "skipped"
    if finish_reason == "length":
        return None, "truncated"
    out = extract_json(raw)
    if out is None:
        return None, "unparseable"
    errs = validate(out, findings)
    if errs:
        return None, "schema: " + errs[0]
    return out, None
