# v2 distillation teacher

- **Model:** Qwen3.5-397B-A17B (OpenRouter `qwen/qwen3.5-397b-a17b`), reasoning effort low, max_tokens 16000, `data_collection: deny`.
- **License:** Apache License 2.0 — https://huggingface.co/Qwen/Qwen3.5-397B-A17B/blob/main/LICENSE (model card: https://huggingface.co/Qwen/Qwen3.5-397B-A17B).
  Apache-2.0 places no restriction on using outputs to train other models.
- **Why:** 2026-10-14 pilot on 30 known-label train plugins (none in the eval/dellkey exam; 12 blind Dell-works, 3 blind verified fixes,
  15 guided code-visible broken), scored with the exact `assemble.judge` filter:

| Teacher (license) | Parsed | Blind agree | Guided agree | Kept (all filters) | Invented SHA/name | Pilot $ |
|---|---|---|---|---|---|---|
| Qwen3.5-397B-A17B (Apache-2.0) | 30/30 | 12/15 | 11/15 | 23/30 | 0 | 0.46 |
| GLM-5.1 (MIT) | 25/30 (5 truncated) | 13/15 | 11/15 | 23/30 | 0 | 1.43 |
| Kimi K2.6 (Modified MIT) | 20/30 (7 no result: >15 min/row, 3 truncated) | 8/15 | 11/15 | 18/30 | 0 | 0.54 |

  Qwen3.5-397B tied GLM-5.1 on kept rows with no truncation at a third of the cost (GLM's projected full run exceeded the $60 cap).
- No proprietary-model outputs are used anywhere in the training data (see METHODS.md, "Training data provenance").
