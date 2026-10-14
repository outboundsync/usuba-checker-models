# Usuba v2 training data: distillation methods

## Teacher
Training targets come from an **open-weights teacher served through OpenRouter**, chosen in a 2026-10-14 pilot (`pilot.py`,
results in `$DISTILL_WORK/teacher/pilot.json`). Only models whose published license permits training on outputs were considered:

| Model | License | Model card |
|---|---|---|
| GLM-5.1 (z-ai/glm-5.1) | MIT | https://huggingface.co/zai-org/GLM-5.1 |
| Qwen3.5-397B-A17B (qwen/qwen3.5-397b-a17b) | Apache-2.0 | https://huggingface.co/Qwen/Qwen3.5-397B-A17B/blob/main/LICENSE |
| Kimi K2.6 (moonshotai/kimi-k2.6) | Modified MIT | https://huggingface.co/moonshotai/Kimi-K2.6 |

Chosen teacher: see **TEACHER.md** (model, license name, model-card URL, pilot score).

**Claude Sonnet 5.5 outputs are not training data.** A first pass used Sonnet 5.5 as teacher; Anthropic's terms (D.4) bar using outputs
to train competing models, so all 2059 Sonnet reviews were quarantined (`$DISTILL_WORK/quarantine-sonnet/`, reference only) and no
row in the v2 train/val set comes from them. Sonnet remains only as an evaluation peer in the scoreboards. `batches.py`,
`openrouter.py` and `anthropic_retry.sh` are kept only as the historical Sonnet runner and must not feed `assemble.py`.

## Pipeline (unchanged process; only the teacher changed)
1. `candidates.py`: leak-free whole-file prompts (prompt_v2); exclusions for the 90-plugin Dell-key exam (eval/dellkey) by manifest id,
   near-duplicate code, holdout repos and val repos; SOURCE.txt and checklist.md never enter prompts; rows over 32k Qwen tokens dropped.
2. `guided.py`: Dell-verified broken plugins split into code-visible (failure visible in the source or Checker report) and runtime-only.
   Runtime-only rows are dropped. Code-visible rows get a guided teacher request (the known failure as a note, teacher request only;
   the training prompt stays the leak-free eval prompt). Broken plugins are never reviewed blind.
3. `or_teacher.py`: resumable OpenRouter runner (blind reviews of working plugins and verified fixes + guided reviews), retries,
   spend cap, `data_collection: deny`.
4. `assemble.py` (`TEACHER=<model>`): keep a teacher review only if it parses, agrees with the grader/Dell label, invents no SHAs or
   plugin names, names the actual bug for broken rows (rubric), does not mention the note, and cites only shown files/lines.
   Rejected/missing works rows fall back to the grader-verified templated target; HANCORE rows use cleaned templated targets.
   Approve share trimmed to ~48%; 32k Qwen-token cap re-checked on the final row.

## Retry / nudge policy (Harris, 2026-10-14)
Rejected first-try works rows: up to 2 more blind tries (`--tag retry1`, `--tag retry2`), then one nudged pass (`--tag nudge --nudge`:
the teacher request says the plugin is verified working and asks for an approve review grounded in the code, no invented issues).
Rejected guided rows: one nudged pass stressing the known bug location. Same filters, plus a nudge-leak check. Nudged works rows are
tagged `source=nudged_approve` and capped at 25% of approve rows (excess falls back to the templated target).
