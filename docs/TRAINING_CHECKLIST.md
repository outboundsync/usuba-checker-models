# Training checklist: the full pipeline in order

Tick each step; `[P]` = needs private inputs that are not published (substitute your own, see `docs/REPLICATION.md`), `[$]` = spends money (API or GPU), `[TODO]` = not finished in this release.
Scripts named without a repo prefix are in this repository; `scripts:` means `usuba-checker-scripts`.

## A. Environment
- [ ] 1. Clone both repos side by side; Python 3.10+, `pip install pytest`; run `python3 -m pytest -q` in each (all green).
- [ ] 2. Export `OPENROUTER_API_KEY` only for steps marked `[$]`. Never write keys into files.
- [ ] 3. `python3 sources/fetch_plugin_sources.py` : fetches the pinned third-party plugin repos (`sources/plugin_sources.json`, permissive licences only).
- [ ] 4. Download the dataset snapshot from Hugging Face into the repo root if you want to skip data building (`docs/DATA_HOSTING.md`), then jump to step 15. Note: the public r4 files (`v3_r4_public/`) are a **subset** (464 of 896 train rows, 55 of 138 val rows): rows derived from private device runs are withheld, so training on them will not reproduce the released model exactly.

## B. Source catalogue and licence gate
- [ ] 5. `sources/clone.sh` (per-repo helper) and `sources/SOURCES.md`/`NOTICE`: verify each LICENSE text at the pinned commit; only MIT/Apache/ISC/BSD(/MPL) rows may enter training.
- [ ] 6. `clean/registry/scan.py` : clone verified registry listings at their validated commit, classify LICENSE text, run the Checker (`scan.jsonl`, `selected_ids.json`).

## C. Base corpus
- [ ] 7. `scripts:build_dataset_v1.py`, `scripts:build_dataset.py` (chunking helpers) : seed `data/train.jsonl`, `data/holdout.jsonl`.
- [ ] 8. `clean/score_train.py`, `clean/build_clean.py`, `clean/dedupe.py`, `clean/dedupe2.py`, `clean/fix_assets.py` : Checker-pass filter and holdout de-duplication.
- [ ] 9. `clean/build_pool.py`, `clean/build_chunked.py`, `clean/build_final.py` : pools and `clean/train_final.jsonl` (+ manifest).
- [ ] 10. `v3/build_v3.py`, `v3/gen_notice.py` : v3 7B SFT set and the regenerated `NOTICE`.

## D. Reviewer-text data (teacher: Qwen3.5-397B-A17B, Apache-2.0)
- [ ] 11. `train/v2/distill/candidates.py`, `guided.py` `[P]`, `or_teacher.py` `[$]`, `assemble.py`, `audit.py` `[$]` : see `train/v2/distill/METHODS.md`. Teacher outputs are kept only if they agree with the grader label and invent nothing.
- [ ] 12. Mining inputs from the scripts repo: `scripts:hancore/fetch.py` -> `label_concrete.py`/`label_recover.py` `[$]` `[P]` (review corpus is re-fetched, not shipped); `scripts:train/version_history/01..05_*.py` and `scripts:jankeesvw-history/scripts/01..10_*.py` (fix-pair mining, `[$]` for the LLM judge step).
- [ ] 13. `v3fixes/run_all.sh` : lifecycle rules, skip-condition measurements, synthetic and winners rows (`train/v3data/build_v3_fixes_rows.py`).
- [ ] 14. `train/v3data/reproduce_r3.sh` (r2 -> r3 build; offline replay needs the unpublished LLM cache, otherwise `[$]`) then `train/v3data/reproduce_r4.sh` (final r4, commit 4678af3 of the original repo: 2,787 version-history pairs considered, thin-kind weighting, 40-pair gpt-oss spot check, repo-disjoint val). Outputs and reports: `train/v3data/r4_out/`, `docs/V3_DATA_R4.md`. The offline LLM-reply cache (`llm_cache.jsonl.gz`, 10,950 replies) is **not published** (it quotes private device run records), so a replay needs `[$]` teacher/judge calls (about USD 5) or your own cache.

## E. Assemble and verify the training set
- [ ] 15. `python3 train/build_train_set.py` : deterministic; writes `train/data/manifest.json`. `launch_vast.sh` refuses data that does not match the manifest.
- [ ] 16. Leakage gate: `python3 train/holdout_guard.py train.jsonl.gz val.jsonl.gz` (exit 0 required; also wired into `build_train_set.py` and `assemble_r4.py`, and `python3 -m pytest train/tests/test_holdout_guard.py`) confirms no sealed-holdout plugin (ids in `eval/hancore_holdout/plugin_ids.txt`) appears in any row; confirm every row has `meta.license` in {MIT, Apache-2.0, ISC, BSD-*}; confirm no row mentions a proprietary-model teacher (`build_v3_data.py` banned-word filter). 
- [ ] 17. Upload nothing yet: verify `hf/MANIFEST.sha256` against the files you will publish.

## F. Train (Qwen3.5-9B, bf16 LoRA, 1x H100 80GB)
- [ ] 18. Read `train/README.md`; check `train/config.yaml` (r32, alpha 64, 2 epochs, lr 1e-4, max_len 32768, max_hours 11).
- [ ] 19. `train/launch_vast.sh plan` (no spend). `[$]` `train/dry_run.sh` then `train/resume_test.sh` (and `--reboot` variant) on a real instance.
- [ ] 20. `[$]` `train/launch_vast.sh up --yes` and `nohup train/launch_vast.sh watch ... &`; wait for `FETCH VERIFIED`; then `train/launch_vast.sh down`.
- [ ] 21. `python3 train/export_gguf.py` (Q4_K_M); record GGUF SHA-256.

## G. Evaluate
- [ ] 22. `scripts:eval/hancore_holdout/serve_llama.sh usuba-9b-Q4_K_M.gguf` (32k per slot x 4 = `-c 131072`; never `-c 16384`).
- [ ] 23. `scripts:eval/hancore_holdout/run_eval.py` against the private manifest (check its SHA-256 equals `scripts:eval/hancore_holdout/MANIFEST.sha256`) `[P]`; `rescore.py` for re-scoring. Publish score tables only.

## H. Release (each needs the owner's approval)
- [ ] 24. Copy the final adapter (`best/`) into `hf/` layout, add to `hf/MANIFEST.sha256`; upload datasets and adapters to Hugging Face with the cards in `hf/`.
- [ ] 25. Gate: `python3 tools/scan_public.py` and `gitleaks git --config .gitleaks.toml .` in both repos report 0 findings.
- [ ] 26. Tag `v0.1.0` in both repos; create GitHub release notes (no large attachments).
