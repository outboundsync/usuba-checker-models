# Checker Model: scope (release 1, advisory)

Settled by Harris, 2026-10-15. This file is the scope of record; where another document disagrees, this one wins (`docs/DEFINITION_OF_DONE.md` is its companion: what "done" means).

## Terms (used exactly, everywhere)
| Term | Means |
|---|---|
| **Checker Scripts** | `usuba-checker-scripts`: the deterministic static + runtime checks. |
| **Checker Model** | the LoRA on Qwen3.5-9B (`usuba-checker-models`). |
| **System** | both: Checker Scripts + Checker Model. |

Do not write "the Checker Scripts" or "Usuba Checker" for a thing that is not unambiguously the Checker Scripts, and do not call the Checker Model "Usuba" in new text (older documents and result files keep the historic names "Usuba v1/v2", which are earlier adapters of the Checker Model).

## What the Checker Model does
It works ON TOP of the Checker Scripts report; it never replaces it.

**Input:** line-numbered plugin code (`train/code_blob.py` rendering, every line prefixed `  12| `) + the full Checker Scripts report (rule id, file, line, message; the prompt also states stage static|runtime and level fail|warn).

**Jobs, in priority order**
1. **TRIAGE** each Checker Scripts finding: `confirm` or `dismiss`, a one-line reason, and a quote from the code.
2. **EXTEND**: findings the scripts cannot see. Focus categories: secrets, url/network, rich-text injection, remote-code pinning, scope/policy, listing/metadata, user-config modification (shared-scorer slugs `secrets-credentials`, `url-scheme-network`, `rich-text-markup-injection`, `remote-code-pinning`, `scope-policy-duplicate`, `listing-metadata-docs`, `user-config-modification`). Each added finding has category, severity `blocker|warning`, file, line, exact quote, finding, fix. Extend never repeats a Checker Scripts finding.
3. **EXPLAIN + FIX** with a concrete patch (carried by the `fix` field of added findings).

**Out of scope:** predicting runtime behaviour (load failures, missing binaries, memory growth). That is the Checker Scripts' job (static + runtime stages). Categories `load:*`, `in-use:*`, `runtime:*` are not outputs of the Checker Model.

## Output schema
```
{"scripts_triage": [{"rule", "file", "line", "decision", "reason", "quote"}],
 "added_findings": [{"category", "severity", "file", "line", "quote", "finding", "fix"}],
 "verdict": "approve" | "changes_requested"}
```
Validator: `scope/schema.py` (exact keys, enums, one line per reason, triage must address every Checker Scripts finding exactly once). An answer that fails the schema is **invalid** and scores as wrong, never as an approval or a dismissal.

Known gap (open for Harris): job 3 asks for a concrete patch for each problem, but `scripts_triage` items have no `fix` field, so a confirmed Checker Scripts finding gets an explanation (`reason`) and no patch; only added findings carry `fix`. Adding an optional `fix` to triage items would be a schema v2 change; it was not made.

## Inference post-filter
Drop any finding or dismissal whose quote is not in the file (`scope/postfilter.py`). A dropped dismissal reverts to `confirm` (the Checker Scripts stand); a dropped added finding disappears. Also: runtime-stage fails cannot be dismissed; an added finding that repeats a Checker Scripts finding (same file and line) is dropped. A quote must have at least 6 non-blank characters.

## Release 1 is ADVISORY
The Checker Scripts' verdict is the System verdict. The Checker Model's `verdict` is reported next to it (`model_verdict`) and scored, but it cannot change the System verdict. Runtime-stage hard-fails cannot be dismissed. Consequence: the worst the Checker Model can do in release 1 is add noise (false added findings) or write a wrong dismissal that a human might believe; it cannot flip the System to approve.

## Not in scope of release 1
Gating (blocking merge/install on the model), runtime prediction, supply-chain/malware vetting, any use of proprietary-model output for training, labels or grading (open-weights only; proprietary models appear only as scored baselines).

## Superseded
`train/prompt_v4.py` (r5) and the r5 dataset (`v3/r5/`) were built for the earlier scope (verdict + findings over load/in-use/review categories, no triage). They are kept for provenance and are not the Checker Model's training format under this scope; the scope prompt is `scope/prompt_scope.py` (`PROMPT_ID = scope-v4`).
