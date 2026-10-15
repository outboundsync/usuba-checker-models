"""Scope prompt v4 for the Checker model (release 1, advisory). NEW prompt, written for the settled scope in docs/MODEL_SCOPE.md.

NOT the same file as ``train/prompt_v4.py``: that one is the r5 prompt of the old scope (verdict + findings, no triage) and stays untouched because the r5 data
builders import it. This module is imported as ``scope.prompt_scope``; its identity is ``PROMPT_ID`` + ``PROMPT_SHA256`` (recorded in every result).

Input  : the plugin source rendered by train/code_blob.py (every line prefixed with its number) + the full Checker scripts report as numbered findings
         (rule id, stage, level, file, line, message).
Output : {"scripts_triage": [...], "added_findings": [...], "verdict": ...}, see scope/schema.py.
"""
import hashlib
import importlib
import json
import os
import sys

PROMPT_ID = "scope-v4"
HERE = os.path.dirname(os.path.abspath(__file__))
TRAIN = os.path.join(os.path.dirname(HERE), "train")


def code_blob_module():
    """The canonical renderer (usuba_checker.code_blob in usuba-checker-scripts, via the train/code_blob.py shim). Loaded lazily so that the schema, post-filter and scorer
    work, and CI runs, without the private sibling checkout; rendering needs it (set USUBA_CHECKER_ROOT)."""
    if TRAIN not in sys.path:
        sys.path.insert(0, TRAIN)
    return importlib.import_module("code_blob")

CATEGORIES = (
    "secrets-credentials", "url-scheme-network", "rich-text-markup-injection", "remote-code-pinning",
    "scope-policy-duplicate", "listing-metadata-docs", "user-config-modification",
)

SYSTEM = """You are the Usuba Checker model. You review an Omarchy (Quickshell/QML) plugin ON TOP of the Checker scripts report: the scripts are deterministic and run first; you never replace them.
You get (1) the plugin source, every line prefixed with its number like `  12| code`, and (2) the full Checker scripts report as numbered findings with rule id, stage (static or runtime), level (fail or warn), file, line and message.
Do three jobs, in this priority:
1. TRIAGE every Checker scripts finding, in report order, exactly once: decision `confirm` (the finding is real) or `dismiss` (false alarm), a one-line reason, and a `quote` copied exactly from the plugin source (without the line-number prefix) that justifies the decision. Echo rule, file and line unchanged from the report. When unsure, confirm. Never dismiss a runtime-stage fail.
2. EXTEND: add findings the scripts cannot see, only in these categories: secrets-credentials, url-scheme-network, rich-text-markup-injection, remote-code-pinning, scope-policy-duplicate, listing-metadata-docs, user-config-modification. Never repeat a Checker scripts finding. Each added finding has category, severity (`blocker` only when a user would be harmed or the plugin must not be published as is, otherwise `warning`), file, line (the number printed at the start of the line), an exact one-line `quote` from that line, a `finding` that explains the problem in plain English, and a `fix` with the concrete replacement code or change. Report nothing you cannot quote. A clean plugin gets an empty list.
3. EXPLAIN and FIX: every added finding carries the concrete patch in `fix`.
Do not predict runtime behaviour (load failures, missing binaries, memory growth): that is the Checker scripts' job. A file marked `(truncated: ...)` or `(omitted: ...)` is not fully shown: do not report defects in the part you cannot see.
Answer with JSON only, no prose, exactly this shape:
{"scripts_triage": [{"rule": str, "file": str, "line": int | null, "decision": "confirm" | "dismiss", "reason": str, "quote": str}],
 "added_findings": [{"category": str, "severity": "blocker" | "warning", "file": str, "line": int, "quote": str, "finding": str, "fix": str}],
 "verdict": "approve" | "changes_requested"}
`verdict` is `changes_requested` if any confirmed fail-level Checker finding or any added blocker exists, otherwise `approve`. The verdict is advisory: the Checker scripts' verdict is the System verdict."""

# category list appended so the label space is explicit
SYSTEM = SYSTEM + "\nAllowed `category` values: " + ", ".join(CATEGORIES) + "."


def render_report(findings):
    """Checker scripts findings -> prompt text. ``findings``: dicts with rule, file, line, message, optional stage/level."""
    if findings is None:
        return "(Checker scripts report unavailable)"
    if not findings:
        return "(no Checker scripts findings)"
    out = []
    for i, f in enumerate(findings, 1):
        out.append("[%d] rule=%s stage=%s level=%s file=%s line=%s\n    %s" % (
            i, f["rule"], f.get("stage", "static"), f.get("level", "fail"), f.get("file") or "-", f.get("line") or 0, f.get("message", "").replace("\n", " ")))
    return "\n".join(out)


def user_msg(code, findings):
    return "## Checker scripts report\n%s\n\n## Plugin source\n%s" % (render_report(findings), code)


def messages(code, findings, target=None):
    m = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_msg(code, findings)}]
    if target is not None:
        m.append({"role": "assistant", "content": json.dumps(target, ensure_ascii=False)})
    return m


def render_files(files):
    return code_blob_module().code_blob(files)


def code_blob_policy():
    return code_blob_module().POLICY_ID


# identity of the instructions only; the renderer policy is recorded next to it in every result (``code_blob_policy()``)
PROMPT_SHA256 = hashlib.sha256((PROMPT_ID + "\n" + SYSTEM).encode()).hexdigest()
