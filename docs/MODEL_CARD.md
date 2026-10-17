# Checker Model (Omarchy plugin reviewer; earlier adapters were called Usuba v1/v2): model card

> Scope of record: `docs/MODEL_SCOPE.md` (release 1, advisory; terms: Checker Scripts, Checker Model, System). The text below describes the adapters trained so far, which predate that scope.

Base: Qwen3.5-9B (Apache-2.0), bf16 LoRA (r=32, alpha=64, dropout 0.05, all attention and MLP projections; `train/config.yaml`), then merged and quantised to Q4_K_M GGUF for local use.
Task of the adapters trained so far (previous scope): read an Omarchy (Quickshell/QML) plugin plus the Checker Scripts report and answer with a JSON verdict (`approve`, `changes_requested`) and a list of findings (category, file, line, explanation). Task under the settled scope: triage each Checker Scripts finding, add findings the scripts cannot see, explain and fix (see `docs/MODEL_SCOPE.md`); no adapter has been trained for that yet.
Status: **Usuba Checker Model v0.1.0 (Run 2), released 2026-10-17** (tag `model-v0.1.0`). An early, advisory release, not production-ready. Both Hugging Face repos are public (`osiharris/usuba-checker-adapters` holds the Run 2 adapter and its Q4_K_M GGUF; `osiharris/usuba-checker-data` is the dataset). Weights and adapters: Apache-2.0; code and documentation: MIT. Hashes: `hf/ADAPTERS_CARD.md`.

## Versions
- **Usuba v1**: first adapter (prompt v1, whole-plugin text capped by the harness). Scored in `eval/hancore_holdout/results/usuba-9b-q4km.json`.
- **Usuba v2**: second adapter, trained on prompt v2 with the v2 distilled data. Scored in `holdout-v2-usuba-v2-best-q4km.json`.
- **Run 2** (2026-10-16, data build r7): the current final model, **not** Usuba v2. Qwen3.5-9B LoRA on the scope prompt v4, 221 train / 23 validation rows, 28 steps, final validation loss 0.263, scored on the bf16 merge (the Q4_K_M file is unscored). Its numbers are in `docs/RUN_RECORDS.md`, not in the holdout tables below, which belong to Usuba v1/v2. Released as **v0.1.0**. Weights: public `osiharris/usuba-checker-adapters`.
- Results are not comparable across prompt versions; see the README tables, which are generated from the result files.

## Intended use
- Local pre-review of third-party Omarchy plugins: surface candidate problems for a human reviewer, next to the Checker Scripts output.
- A human decides. The Checker Model is advisory in release 1: the Checker Scripts' verdict is the System verdict, and the model is not a merge, install or security gate.

## Out of scope
- Any automated accept/reject decision, malware or supply-chain vetting (flagging an unpinned remote script or a hard-coded secret in a plugin is in scope; judging whether a publisher is trustworthy is not), predicting runtime behaviour (that is the Checker Scripts' job), or review of code that is not Omarchy/Quickshell plugins.
- Treating a finding's explanation as evidence: findings are model text, and the Checker Scripts and the plugin source are the evidence.

## Evaluation (329-plugin sealed HANCORE holdout: 300 positives, 29 negatives; one run per system)
Numbers and 95% intervals are in the README (generated from the result files). Headline facts:
- Always answering "changes requested" scores 0.912 verdict accuracy (300/329), so accuracy alone says little.
- Usuba v1 (prompt v1): verdict accuracy 0.809, positive recall 0.883, **false alarm 0.931 (27 of 29 clean plugins flagged)**, category recall 0.402, JSON valid 0.909. (0.809 is the current scorer's value from `usuba-9b-q4km.rescored.json`, which the README tables use; the legacy scorer printed 0.812 in `usuba-9b-q4km.json`. Only this one figure differs; the other columns are identical.)
- Usuba v2 (prompt v2): verdict accuracy 0.696, false alarm 0.586, category recall 0.106.
- Only 29 negatives: the false-alarm interval is about +/-0.15. Legacy result files have no per-row data and no invalid/approve split, so their intervals are Wilson intervals from the published rates.
- Not measured: bf16 versus Q4_K_M on the holdout for the shipped model (only 20 Dell plugins for v2), a second seed, and any prompt-v3 run of the Usuba models.
- Hardware key (private, 86 decided plugins): the right-reason bar was not met by v2 (0.10 of flagged vs a 0.60 gate). See `docs/TRAINING_PLAN.md`.

## Known limitations
- **False alarms.** v1 flags nearly every clean plugin.
- **Invented specifics.** v1 invented commit SHAs in 46 of 90 Dell outputs; v2 removed that failure mode on the same key (0 rows) but answers in a generic security-review register with no file or line for 14 of 20 flagged findings.
- **Prompt sensitivity.** The same stock model moves by more than 0.2 accuracy across prompt versions.
- **Truncation.** Prompts cap file length (v2 truncated files); findings in cut-off code cannot be seen.
- **Line numbers.** The v1-v3 prompts carry no line numbers, so line citations of those adapters are unreliable; the r5 renderer (`train/code_blob.py`) and the scope prompt number every line.
- Training labels come from a deterministic Checker Scripts and a hardware key on one reference machine (Omarchy 4.0.4); other versions are untested.

## Quantisation
Q4_K_M GGUF via llama.cpp (`train/export_gguf.py`; about 5.5 GB). All published Usuba v1/v2 holdout rows are Q4_K_M; the Run 2 scores are for the bf16 merge, not for its Q4_K_M file. Server flags used for the exam: `-c 131072 -np 4` (32k tokens per slot), temperature 0.

## Prompt template and decoding
Prompts: `train/prompt.py` (v1), `train/prompt_v2.py`, `train/prompt_v3.py`; the same module builds training rows and eval requests.
Decoding for the exam: temperature 0, `max_tokens` set by `run_eval.py --max-tokens` (recorded in each new result file under `decoding`), no thinking mode.
Output schema (validated by the shared scorer, `eval/hancore_holdout/scoring.py` in usuba-checker-scripts): `{"verdict": "approve"|"changes_requested", "findings": [{"category": str, "file": str|null, "line": int|null, ...}]}` (the verdict values, optional `severity` and `load` are checked against fixed lists in the scorer); an output that fails the schema is counted as **invalid**, not as an approval.

## Licence
- Adapters follow the base model: Apache-2.0 (verified 2026-10-15 on https://huggingface.co/Qwen/Qwen3.5-9B).
- Training data keeps each source plugin's licence (MIT, Apache-2.0, ISC); attribution and licence texts: `NOTICE`, `sources/licenses/`. NOTICE is generated and checked by `tools/gen_notice.py`.
- Code and documents in this repository: MIT.
- Attribution approach has not been reviewed by counsel; do that before any upload.

## Training data provenance
**No proprietary-model outputs (Anthropic/Claude, OpenAI/GPT, Google/Gemini, xAI/Grok or any closed model) were used to train Usuba.**
Training data: real licensed plugins (see NOTICE); HANCORE findings from public GitHub review issues; scripted Checker Scripts reports; hardware-verified
Omarchy 4.0.4 labels; real upstream fix commits graded by the Checker Scripts; and review text written only by the open-weights teacher
**Qwen3.5-397B-A17B (Apache-2.0)** — https://huggingface.co/Qwen/Qwen3.5-397B-A17B/blob/main/LICENSE — filtered against the grader labels.
Teacher license: Apache-2.0 (no restriction on training other models on its outputs). Proprietary models appear only as evaluation baselines.
Full method: `train/v2/distill/METHODS.md`, `train/v2/distill/TEACHER.md`.
