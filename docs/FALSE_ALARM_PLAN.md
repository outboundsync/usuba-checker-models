# False-alarm penalty and val-tuned threshold plan (2026-10-15; nothing here has been run, no GPU used)

Why: Usuba v1 flags 0.931 of the 29 clean holdout plugins (see README table), so it is not a usable gate. The data keeps ~45-50% approves on purpose (Harris decision 3); the knobs below
shift the model's operating point without changing the data ratio.

## 1. Training-time option: `false_alarm_penalty` (train/config.yaml, default 1.0 = off)
`train_utils.example_weight()` multiplies the loss weight of every approve-target row by the factor (works with or without `use_example_weight`). Grid for r6: {1.0, 1.5, 2.0, 3.0}; each
is one LoRA run on the same r6 data and seed. Unit-tested (`train/tests/test_train_utils.py`). Not launched.

## 2. Inference-time option: val-tuned decision threshold
The verdict is the first discriminating token of the JSON (`approve` vs `changes_requested`). With logprobs enabled in the server (`llama-server --logprobs` / `logprobs=true, top_logprobs=5`):
1. `s(row) = logP(approve) - logP(changes_requested)` at the verdict token, recorded per row by the eval harness next to the answer (no extra generation).
2. On the **val split only** (repo-disjoint, ~half approves), sweep threshold t over the observed scores. Choose the smallest t whose val false-alarm rate (clean rows answered changes-requested or invalid) is <= 0.30 (target stated before looking); tie-break by higher positive recall. Report the val ROC and the chosen t with a bootstrap CI.
3. Freeze t. Run the HANCORE holdout, the clean set and the Dell key **once** with that t. Report all three side by side (about 56% of r5 rows came from the Dell-sweep pipeline, so Dell-key scores alone must never be the headline).
4. The same sweep is repeated for each penalty in the grid; the (penalty, t) pair is chosen on val and nothing else. If val has fewer than ~80 approves the interval is too wide to pick between neighbouring grid cells: say so and pick the simpler one (smaller penalty).

## 3. What would invalidate it
Tuning t or the penalty on the holdout, the clean set or the Dell key; reporting only the best of the grid on a test set; changing the val split after seeing scores.
