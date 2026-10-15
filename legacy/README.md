# legacy/ (audit F7)

Older pipelines, moved here (history kept by `git mv`) so the top level only holds what the current Usuba 9B reviewer work uses.

| now | was | what |
|---|---|---|
| `legacy/clean/` | `clean/` | 7B-era cleaned datasets, builders, manifests, registry scan |
| `legacy/qwen25-coder-v3/` | `v3/` | Qwen2.5-Coder "v3" builder datasets. **Renamed**: the old name collided with the reviewer's v3 (`train/v3data`, `prompt_v3`) |
| `legacy/data/` | `data/` | stats of the v1 build |
| `legacy/runs/` | `runs/` | experiment scripts, score tables, logs (53 tracked `.log` files; no raw generations) |

* **Nothing in `train/` imports from here.** `tools/gen_notice.py` reads the manifests under `legacy/clean` and `legacy/qwen25-coder-v3` (NOTICE is generated from them).
* **Scripts inside these folders still use their old relative paths** (for example `clean/build_final.py` expects `clean/` next to `sources/`). They are archived, not maintained: to re-run one,
  put the folder back under its old name in a scratch checkout. They were not edited, to keep the history of what produced the data intact.
* **Hugging Face dataset paths are unchanged** (`clean/…`, `v3/…`, `data/…`): the dataset repo is a separate layout; `hf/MANIFEST.sha256` and `hf/GUARD_FILTER.json` keep those names.
* `scan_public.py`'s reviewed-historical-blob list (`ACCEPTED`) names both the old paths (history) and the new ones (tree).
