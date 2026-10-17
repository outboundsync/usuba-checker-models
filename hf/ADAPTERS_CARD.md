# Usuba Checker adapters: hosting and hashes

The adapters repo `osiharris/usuba-checker-adapters` exists on Hugging Face and is **private** (release prepared, not announced). It holds the **Run 2** adapter (`adapter/`) and its Q4_K_M GGUF (`gguf/`), with the model card; its README is the card of record for Run 2. No adapter weights are stored in this GitHub repository. The earlier adapters (the two Qwen2.5-Coder-7B experiments and the Qwen3.5-9B Usuba v1 / Usuba v2 adapters) are **not** uploaded; only the hashes recorded below tie them to results.
Licence: LoRA adapters follow their base model; Qwen/Qwen2.5-Coder-7B-Instruct and Qwen/Qwen3.5-9B are both Apache-2.0, so the adapters are Apache-2.0. Code and documentation in this repository: MIT.

**Run 2** (training run of 2026-10-16, data build r7; defined in `README.md` and `docs/RUN_RECORDS.md`; it is not "Usuba v2"):

| file | sha256 |
|---|---|
| `adapter/adapter_model.safetensors` (`best`, 346,294,736 bytes) | `79cb47183b6577aa046ae2c89f961bd5538f3353ab3eee48455b026946242bb2` |
| `gguf/usuba-9b-usuba-9b-lora-r7-best-Q4_K_M.gguf` (5,629,108,800 bytes) | `7d2b54a24f335aa31d53a47fca8e0848add83bef8246f0f7f831c0e80c9e4f8e` |

(Both match the checksum files written on the training instance and fetched to the build box.)

SHA-256 of the earlier, not-uploaded `adapter_model.safetensors` files, so results in this repo can be tied to exact weights:

| adapter | base | sha256 |
|---|---|---|
| `qwen25-coder-7b-fix-adapter-b` (early experiment) | Qwen2.5-Coder-7B-Instruct | `08115e7498361a217ec9227edb90a413347d56efbd0f0d0802a4b1acd5caa1bd` |
| `qwen25-coder-7b-fix14-adapter-b14` (early experiment) | Qwen2.5-Coder-7B-Instruct | `153c7a41636176d81b53619e5e69db8c4c404f264271ae018347d0cf183a1533` |
| `usuba-9b-lora/best` (Qwen3.5-9B; Usuba v1 or v2, **identity unresolved**, see note; not Run 2) | Qwen3.5-9B | `88b857d28fd5c02fc7b8ad9d74347c54c5c3dfc5a70885938960578fe009b57a` |

`usuba-9b-lora/best/adapter_config.json` sha256: `9a6e71b2f44a46595b60ac3af801578a685b9b6af89b7e0545fdc9ce6a321c1b`.

**Identity note (audit F2/F5).** Two Qwen3.5-9B adapters exist: **Usuba v1** (Vast run 55864967, finished 2026-10-14, val loss 1.073459 at step 568; scored in `eval/hancore_holdout/results/usuba-9b-q4km.json`) and **Usuba v2** (second training run, scored in `holdout-v2-usuba-v2-best-q4km.json`).
This card previously labelled the single hash above "v2", while `docs/DATA_HOSTING.md` described the same hash as the val-loss-1.0735 / step-568 adapter, which is the v1 run. The repository alone cannot tell which of the two the hash belongs to,
and only one Qwen3.5-9B hash is recorded. Until the hashes of both adapters are recorded from the actual files, **do not cite this hash as a specific version**; it is known not to be Run 2 (Run 2's hash is above). The `adapter_config.json` hash does not distinguish them either.
