# Usuba Checker adapters: weights withheld

No adapter weights are staged or released from this repository. Final weights will go to Hugging Face after the v3 run.
LoRA adapters follow the licence of their base model (Qwen/Qwen2.5-Coder-7B-Instruct and Qwen/Qwen3.5-9B are both Apache-2.0).

SHA-256 of the withheld `adapter_model.safetensors` files, so results in this repo can be tied to exact weights:

| adapter | base | sha256 |
|---|---|---|
| `qwen25-coder-7b-fix-adapter-b` (early experiment) | Qwen2.5-Coder-7B-Instruct | `08115e7498361a217ec9227edb90a413347d56efbd0f0d0802a4b1acd5caa1bd` |
| `qwen25-coder-7b-fix14-adapter-b14` (early experiment) | Qwen2.5-Coder-7B-Instruct | `153c7a41636176d81b53619e5e69db8c4c404f264271ae018347d0cf183a1533` |
| `usuba-9b-lora/best` (Qwen3.5-9B; **identity unresolved**, see note) | Qwen3.5-9B | `88b857d28fd5c02fc7b8ad9d74347c54c5c3dfc5a70885938960578fe009b57a` |

`usuba-9b-lora/best/adapter_config.json` sha256: `9a6e71b2f44a46595b60ac3af801578a685b9b6af89b7e0545fdc9ce6a321c1b`.

**Identity note (audit F2/F5).** Two Qwen3.5-9B adapters exist: **Usuba v1** (Vast run 55864967, finished 2026-10-14, val loss 1.073459 at step 568; scored in `eval/hancore_holdout/results/usuba-9b-q4km.json`) and **Usuba v2** (second training run, scored in `holdout-v2-usuba-v2-best-q4km.json`).
This card previously labelled the single hash above "v2", while `docs/DATA_HOSTING.md` described the same hash as the val-loss-1.0735 / step-568 adapter, which is the v1 run. The repository alone cannot tell which of the two the hash belongs to,
and only one Qwen3.5-9B hash is recorded. Until the weights are uploaded and the hashes of both adapters are recorded from the actual files, **do not cite this hash as a specific version**. The `adapter_config.json` hash does not distinguish them either.
