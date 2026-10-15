# omarchy-specialist

## Training data provenance

**No proprietary-model outputs (Anthropic/Claude, OpenAI/GPT, Google/Gemini, xAI/Grok, or any other closed model) were used to train Usuba.**

Usuba v2 training rows come from exactly these sources:
- **Real plugins**: MIT/Apache/BSD/ISC/MPL-licensed community and first-party Omarchy plugin code (see `NOTICE`, `sources/SOURCES.md`).
- **Real reviewer evidence**: HANCORE findings drawn from public GitHub review issues, the Usuba Checker's scripted report, and
  hardware-verified Omarchy 4.0.4 labels (plugin loads or fails on a real machine).
- **Verified fixes**: real upstream fix commits, graded by the Checker/hardware grader. (Model-written fixes were removed from v2.)
- **Review text written only by an open-weights teacher**: **Qwen3.5-397B-A17B, Apache-2.0**
  (https://huggingface.co/Qwen/Qwen3.5-397B-A17B/blob/main/LICENSE), served through OpenRouter. Each teacher review is kept only if it
  agrees with the grader/hardware label, names the real bug, invents no SHAs or plugin names, and parses. Details: `train/v2/distill/METHODS.md`, `TEACHER.md`.
- Everything else uses scripted templated targets built from the grader/Checker findings.

Proprietary models appear in this repo only as **evaluation baselines** (scoreboards, judge) and never as a source of training text.
History: an early v2 attempt used Claude Sonnet 5.5 as teacher; that data was discarded unused (quarantined outside the repo) and never trained on.
Usuba v1 (see `docs/TRAINING_PLAN.md`) was built from real plugins, HANCORE human-written findings, Checker rules and hardware labels; our review of the
v1 build scripts found no proprietary-model output in its training data.


Experiment: fine-tune small open models (Qwen-coder 7B "Santoku", and a 14B) with QLoRA to write valid **Omarchy (Quattro / omarchy-shell) plugins**, and measure them honestly.

## Honest current status
- The original "validator-style" shallow checker (manifest/static checks only) gave **invalid, inflated scores**. Do not trust any numbers derived from it (`functest/old_scores.py` exists only for comparison).
- On the real functional test (`functest/`, 56 holdout tasks, plugins actually loaded and exercised):

| Model | Pass /56 |
|---|---|
| Reference solutions | 51 |
| GPT-5.6 | 29 |
| Opus | 28 |
| Santoku 7B LoRA (`legacy/runs/fix/adapter_b`) | **8** |

The fine-tuned 7B is far behind frontier models. Not production-ready. The tuned 14B (`legacy/runs/fix14/adapter_b14`) is included for further evaluation.

## Layout
- `validator/` – upstream `omarchy-plugin-validate` contract (MIT, see NOTICE).
- `functest/` – real functional test harness (`functest.py`, `runtime.py`, `static_checks.py`), calibration and `results.json`. `functest/cache/` is git-ignored.
- `build_dataset.py`, `build_dataset_v1.py`, `gen_docs.py`, `tools_analyze.py` – dataset build scripts. See `DATASET.md` for the dataset doc.
- `data/` – `train.jsonl`, `holdout.jsonl`, stats.
- `sources/` – source catalog metadata and licenses. Third-party repo clones (`sources/repos/`, ~900MB) are **not** committed; re-clone with `sources/clone.sh`.
- `runs/` – training/generation/eval scripts and outputs (jsonl) per run; LoRA adapters via Git LFS:
  - `legacy/runs/fix/adapter_b` – Santoku 7B LoRA
  - `legacy/runs/fix14/adapter_b14` – tuned 14B LoRA
- `legacy/clean/` – holdout dedupe/rescoring work (in progress).
- `dell-smoke/` – sample plugins for on-device smoke testing.

## Running the functest
```bash
python -m venv .venv && . .venv/bin/activate
python functest/functest.py --help      # entry point
python functest/rescore.py              # rescore generated outputs into results.json
```
Needs the Omarchy shell runtime deps described in `functest/runtime.py`. API-backed generators read keys only from env vars (`OPENROUTER_API_KEY`, `XAI_API_KEY`); no keys are stored in this repo.

Clone with `git lfs install` first to get the adapter weights.

## Functest v2: Dell-faithful environment (Omarchy 4.0.0.alpha "Quattro")

`python functest/dell_env/setup.py` builds the environment under `/opt/ft/`. The test then runs the **real** Omarchy shell
(basecamp/omarchy @ c668141, byte-identical to the reference Dell) under Quickshell in bwrap with a private headless sway.
Pieces:
- the real catppuccin-latte theme, rendered by `omarchy-theme-set-templates`, plus the JetBrainsMono Nerd Font and Omarchy's fonts.conf
- a fake Hyprland IPC and `hyprctl` that replay v0.56.2 reply shapes (`functest/fixtures/hyprland-0.56.2`)
- a PATH of logging shims, one per binary on the Dell; unknown binaries fail to start, as they do on the Dell

Checks added (static: `dell_checks.py`; runtime: `runtime.py`):

| check | static | runtime |
|---|---|---|
| exec'd binary must exist on the Dell | `exec-unknown-binary` | `rt-missing-binary` |
| no undefined/null/NaN/[object Object] in argv or rendered text | `exec-undefined-arg` | `rt-undefined-arg`, `rt-undefined-text` |
| settings read must be declared in manifest defaults | `settings-undeclared` (flag) | |
| bar API / Commons singleton members must exist | `bar-api-unknown` (flag), `singleton-unknown` | |
| shell errors that the no-plugin baseline doesn't have | | `rt-shell-broken`, `rt-plugin-warn` |
| bar widget visible, inside the screen, nonzero ink, contrast ≥1.15:1 (zero size is soft for Hyprland-driven widgets) | | `rt-offscreen`, `rt-invisible` |
| replacement bar actually drawn (soft if it uses GPU layer effects the software renderer can't draw) | | `rt-invisible` |
| gap services (manifest says gaps/flush, ships a gaps setter) must issue `hyprctl keyword general:gaps_*` | | `rt-other` |

Log lines only fail a plugin on TypeError/ReferenceError/syntax/load/missing-file/missing-type errors. "Unable to assign [undefined]",
read-only-property, deprecation, QSettings and binding-loop warnings are soft, because they show up on the Dell in plugins that work. A plugin's own
console warnings are hard only when they name a Dell surface (hyprctl/getoption/omarchy-*/theme); "not signed in"/no-network reports are soft.
Any binary the shell actually launches must exist on stock Omarchy, even when the README documents it (`FT_DOC_DEPS=1` relaxes this).

Anti-tamper: the shell log, probes and screenshots leave the sandbox on the driver's stdout pipe, never as files the
plugin could rewrite. Results: `batch2_results.json` (15 Dell-verified plugins), `recal_registry.jsonl`,
`ref49_results.json`, `calibration.json`.
