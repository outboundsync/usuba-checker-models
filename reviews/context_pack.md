

===== README.md =====
# omarchy-specialist

Experiment: fine-tune small open models (Qwen-coder 7B "Santoku", and a 14B) with QLoRA to write valid **Omarchy (Quattro / omarchy-shell) plugins**, and measure them honestly.

## Honest current status
- The original "validator-style" shallow checker (manifest/static checks only) gave **invalid, inflated scores**. Do not trust any numbers derived from it (`functest/old_scores.py` exists only for comparison).
- On the real functional test (`functest/`, 56 holdout tasks, plugins actually loaded and exercised):

| Model | Pass /56 |
|---|---|
| Reference solutions | 51 |
| GPT-5.6 | 29 |
| Opus | 28 |
| Santoku 7B LoRA (`runs/fix/adapter_b`) | **8** |

The fine-tuned 7B is far behind frontier models. Not production-ready. The tuned 14B (`runs/fix14/adapter_b14`) is included for further evaluation.

## Layout
- `validator/` – upstream `omarchy-plugin-validate` contract (MIT, see NOTICE).
- `functest/` – real functional test harness (`functest.py`, `runtime.py`, `static_checks.py`), calibration and `results.json`. `functest/cache/` is git-ignored.
- `build_dataset.py`, `build_dataset_v1.py`, `gen_docs.py`, `tools_analyze.py` – dataset build scripts. See `DATASET.md` for the dataset doc.
- `data/` – `train.jsonl`, `holdout.jsonl`, stats.
- `sources/` – source catalog metadata and licenses. Third-party repo clones (`sources/repos/`, ~900MB) are **not** committed; re-clone with `sources/clone.sh`.
- `runs/` – training/generation/eval scripts and outputs (jsonl) per run; LoRA adapters via Git LFS:
  - `runs/fix/adapter_b` – Santoku 7B LoRA
  - `runs/fix14/adapter_b14` – tuned 14B LoRA
- `clean/` – holdout dedupe/rescoring work (in progress).
- `dell-smoke/` – sample plugins for on-device smoke testing.

## Running the functest
```bash
python -m venv .venv && . .venv/bin/activate
python functest/functest.py --help      # entry point
python functest/rescore.py              # rescore generated outputs into results.json
```
Needs the Omarchy shell runtime deps described in `functest/runtime.py`. API-backed generators read keys only from env vars (`OPENROUTER_API_KEY`, `XAI_API_KEY`); no keys are stored in this repo.

Clone with `git lfs install` first to get the adapter weights.


===== DATASET.md =====
# Omarchy Specialist — seed dataset v2 (public-release license policy; not yet published)

Seed chat-format SFT data for a QLoRA fine-tune of a 7B Qwen coder model that writes valid Omarchy (Quattro / omarchy-shell) **plugins**.
Status: built locally. No GPU spend, nothing published, no outreach, no PRs.

## Snapshot
- **basecamp/omarchy @ `9480d1b6a98156314dbabe6bfef08f39f8b9cd07`** (branch `quattro`, merge of PR #15065, 2026-10-11 14:07 MT). License: MIT, `Copyright (c) David Heinemeier Hansson`.
- Contract sources: `bin/omarchy-plugin-validate` (copied verbatim to `validator/`) and `shell/services/PluginRegistry.qml` (`isSafeEntryPoint`, manifest checks, reserved `omarchy.*` gate at load time).
- Marketplace catalog: `https://plugins.omarchy.org/catalog.json`, generatedAt 2026-10-12T03:38Z (5,411 listings), saved in `sources/catalog.json`.

## Plugin contract (what the validator enforces)
- `manifest.json` at the plugin root, valid JSON, `schemaVersion` must be the **number** 1 (`"1"` is rejected; `1.0` passes).
- Required: `id`, `name`, `version`, `kinds`, `entryPoints`.
- `id`: `^[A-Za-z0-9][A-Za-z0-9._-]*$`, no `..`, not `omarchy.*` (reserved for first-party code).
- `kinds`: a non-empty array. Every kind needs a matching entry point: bar→`bar`, bar-widget→`barWidget`, menu→`menu`, overlay→`overlay`, panel→`panel`, service→`service`. Unknown kinds aren't checked.
- `entryPoints`: an object. Each value must be non-empty, have no newline, not start with `/`, contain no `..`, and point to a file that exists.
- `barWidget.defaultSection`, if set: `left|center|right`.
- No symlinks anywhere in the folder (`.git` is skipped).
- Pass means **silent output and exit 0**.

## Validator fidelity
- The real CLI is bash + `jq` + `find`, so it **runs unmodified on this Debian box** (`validator/omarchy-plugin-validate`). Every example was checked through `validator/validate.py`, a line-by-line Python port that can also validate in-memory files.
- `validator/diff_test.sh` runs the real script and the port side by side on 25 cases: every rule, the edge cases above, and a symlink. Result: **25/25 identical output and exit code.** A separate run on all 31 first-party manifests also matched (all rejected on the reserved `omarchy.*` id, as expected).
- **Gaps (not covered by `omarchy plugin validate`):**
  - Marketplace-only rules: allowed `barWidget.category` values (Fun/Info/Lifestyle get rejected at listing, but the CLI passes them), filing tags, preview image, and the HANCORE security baseline.
  - Runtime QML load behavior: whether `qs.*` / Quickshell imports resolve, KeyboardPanel nesting, etc. You can only see that on a real Omarchy box.
  - PluginRegistry also skips plugins whose id collides with a first-party id. The CLI only checks the `omarchy.` prefix.
- **qmllint**: Debian has no `qt6-declarative-dev-tools` package. I installed PySide6-Essentials in `.venv` (Qt 6 `pyside6-qmllint`) instead. `validator/qmllint_check.py` runs `qmllint --bare --disable-plugins all` and counts only **`[syntax]`** findings, because the Quickshell/`qs.*` modules aren't installed and import/type warnings are expected. The default qmllint plugins hang on real Quickshell files; disabling them fixes the hang. Result (v2.1): **290 QML files across 254 examples, 0 syntax errors.** The build also lints every example and drops any with a syntax error. None were dropped.

## License policy (public model)
- **Train:** first-party Omarchy code (MIT), Harris's own plugins (all six, MIT, `Copyright (c) 2026 Harris Kenny`), and community repos whose LICENSE file **at the pinned commit** is verified MIT, Apache-2.0, BSD-2/3, ISC or MPL-2.0. A verified repo also needs a copyright line, and its manifest/package license fields must not conflict. In practice all 48 community repos in use are MIT (the 6 Omarchy forks are excluded, and other verified repos took their places under the same ranking).
- **Reference only, never in training text:** GPL/AGPL/LGPL, repos with no license, and anything custom, unclear or mixed.
- Licenses were classified from the LICENSE file text (GNU family detected from the title only), not from catalog or GitHub labels. The catalog label disagrees often:
  - 21 repos labeled "See repository" have a real MIT file.
  - XMB-Enhanced is labeled GPL-2.0, but its file is noncommercial. Excluded.
- `NOTICE`: one attribution line for each of the 55 sources (omarchy, 6 house, 48 community) plus vendored omakit. `sources/licenses/`: the 55 full LICENSE texts. Ship both with the dataset and the model.
- Per-source table (stars, commit count, author, core-contributor flag, author plugin count, verified license, catalog label, manifest license, copyright, vendored flags, bucket, examples used): **`sources/SOURCES.md`**.
  - 117 candidates were verified (105 train, 6 fork reference-only, 4 copyleft reference-only, 2 excluded): the 70 top-ranked installable plugins plus 47 bar- and launcher/menu-kind listings added in v2.
  - Core contributor means 10 or more commits to basecamp/omarchy. Rank = stars + 5×min(author plugins, 5) + 50×core.

### Excluded / reference-only
| id | repo | verified license | bucket |
|---|---|---|---|
| evindor.keystroke | https://github.com/evindor/keystroke | MIT | reference-only (fork: LICENSE names only DHH, no fork-author copyright) (catalog `MIT`) |
| grantabell.three-state-bar | https://github.com/GrantAbell/Omarchy-Three-State-Bar | MIT | reference-only (fork: LICENSE names only DHH, no fork-author copyright) (catalog `MIT`) |
| io.github.adamritter.surface-studio | https://github.com/adamritter/omarchy-surface-studio | MIT | reference-only (fork: LICENSE names only DHH, no fork-author copyright) (catalog `See repository`) |
| io.github.grechman.dynamic-bar | https://github.com/grechman/dynamic-bar | GPL-3.0 | reference-only (copyleft) (catalog `GPL-3.0-or-later`) |
| io.github.ilyazar.syncthing | https://github.com/omarchy-QOL/syncshell | MIT | exclude-unclear (license field mismatch) (catalog `MIT AND MPL-2.0 AND OFL-1.1 AND BSD-3-Clause`) |
| io.github.rk4500.adaptive-bar | https://github.com/rk4500/omarchy-adaptive-bar | MIT | reference-only (fork: LICENSE names only DHH, no fork-author copyright) (catalog `See repository`) |
| io.github.sa1ntmar0on.xmb-enhanced | https://github.com/Sa1ntMar0on/XMB-Enhanced | NONCOMMERCIAL | exclude (custom/unclear) (catalog `GPL-2.0`) |
| mscurtescu.island-bar | https://github.com/mscurtescu/omarchy-island-bar | MIT | reference-only (fork: LICENSE names only DHH, no fork-author copyright) (catalog `MIT`) |
| noodlesploder.celeste | https://github.com/NoodleSploder/omarchy-celeste | GPL-3.0 | reference-only (copyleft) (catalog `GPL-3.0-or-later`) |
| olauncher | https://github.com/hisnameismarco/OLauncher | GPL-3.0 | reference-only (copyleft) (catalog `See repository`) |
| omacale.bar | https://github.com/AyushKr2003/omacale | GPL-3.0 | reference-only (copyleft) (catalog `GPL-3.0-only`) |
| voyagen.oma-gradient-topbar | https://github.com/voyagen/oma-gradient-topbar | MIT | reference-only (fork: LICENSE names only DHH, no fork-author copyright) (catalog `MIT`) |

### Flags for the release review
- **Omarchy forks (Harris's decision, Oct 11, 2026): out of training.** island-bar, oma-gradient-topbar, three-state-bar, surface-studio, adaptive-bar and keystroke are now reference-only, with the reason "fork: LICENSE names only DHH, no fork-author copyright". No repo used in the dataset has a LICENSE that names only DHH. stappmus/omarchy-activity-monitor has the same pattern but is not used, because of the size and author caps; extend the rule to it if it is ever pulled in.
- **Vendored code in a used repo:** `mtolhuys/omacrunch/omakit/`, copied from omakit (MIT, same author). It is added to NOTICE.
- **Vendored code in repos the dataset doesn't use** (training only takes plugin-authored `.qml/.json/.js/.py/.sh`, never `vendor/`, `fonts/`, `assets/`, `icons/`, `sdk/` etc.): hass (websockets), ai-usagebar (lobe-icons), radio-atlas, omadock/omamail (fonts), syncshell (excluded), LetsFG.

## Dataset (v2)
- Files:
  - `data/train.jsonl`: 198 examples
  - `data/holdout.jsonl`: 56 examples (22%)
  - Each line is `{messages:[system,user,assistant], task, meta}`. The assistant returns complete files as `### path` + a fenced code block.
- **Context budget (real tokenizer):** every example is tokenized with the **Qwen/Qwen2.5-Coder-7B-Instruct** tokenizer and its chat template (CPU, `transformers` in `.venv`). A plugin goes in whole only if its rendered files are ≤ 30k tokens and ≤ 90 KB; otherwise it's split into file-level tasks. Any example over **32,768 tokens** is dropped (one symlink-fix example built from a 36k-token entry file was dropped; the builder now skips mutation sources whose entry file is over 30 KB). **Tokens: max 23,789, p95 19,051, median 6,963. None over 32k.**
- **Task types:**
  - `build_from_spec`: spec in, full plugin out. First-party ×2 phrasings, house ×3, community ×1.
  - `add_panel`: given a bar-widget manifest, return the real plugin with `Panel.qml` loaded via a Loader.
  - `fix_manifest:*`: 8 mutations × 3, using the real validator error.
  - `chunk_manifest_entry`: write the manifest plus all entry-point files for a spec, given the list of sibling files (house ×2).
  - `chunk_entry_file`: given the manifest, write one oversized entry point (e.g. the 77 KB first-party `Bar.qml` case is handled through manifest+entry).
  - `chunk_add_kind:<kind>`: a multi-kind plugin with one kind removed; add the kind back with its entry point (bar, menu, service, bar-widget).
  - `chunk_component`: given the manifest and sibling list, implement one component file ≤ 40 KB. Up to 12 per house plugin, 4 per first-party, 2 per community.
- **Validation:**
  - Full-plugin answers must pass `validate.py` on their own.
  - Chunked and fix answers are written into the **real plugin tree at the pinned commit** (first-party ids re-namespaced to `acme.*`), and the tree must pass.
  - Every QML file in an answer must also be qmllint syntax-clean.
  - Result: **254/254 validator pass, 254/254 qmllint syntax-clean (290 QML files).**
- **Holdout:**
  - Split by plugin group (a plugin is never in both splits), stratified by primary kind (the rarest kind it declares), about 20% of examples per stratum.
  - Every kind is in both splits (train/holdout): bar-widget 98/22, bar 52/18, service 30/15, menu 29/10, panel 12/3, overlay 11/3.
  - One house plugin (Scriptural, 4 examples) is held out for a house-style eval. The other 5 house plugins are train-only.
- **Harris's plugins:** read from `/workspace/omarchy-*` at local HEAD:
  - omarchy-compliantish `fed3594` (train): 8
  - omarchy-encyclopedic `3b122bf` (train): 6
  - omarchy-enricherino `38c830c` (train): 9
  - omarchy-rocketlauncher `e2e0061` (train): 15
  - omarchy-scriptural `5b478a5` (holdout): 4
  - omarchy-sparklekeys `157f9f8` (train): 13

### By task
| | train | holdout | total |
|---|---|---|---|
| chunk_component | 80 | 10 | 90 |
| build_from_spec | 56 | 27 | 83 |
| chunk_manifest_entry | 28 | 5 | 33 |
| fix_manifest | 19 | 5 | 24 |
| add_panel | 10 | 6 | 16 |
| chunk_add_kind | 4 | 3 | 7 |
| chunk_entry_file | 1 | 0 | 1 |

### By task (detailed)
| | train | holdout | total |
|---|---|---|---|
| chunk_component | 80 | 10 | 90 |
| build_from_spec | 56 | 27 | 83 |
| chunk_manifest_entry | 28 | 5 | 33 |
| add_panel | 10 | 6 | 16 |
| chunk_add_kind:menu | 2 | 1 | 3 |
| fix_manifest:bad_path_absolute | 2 | 1 | 3 |
| fix_manifest:missing_entry | 3 | 0 | 3 |
| fix_manifest:schema_string | 3 | 0 | 3 |
| fix_manifest:missing_entry_file | 3 | 0 | 3 |
| fix_manifest:bad_default_section | 3 | 0 | 3 |
| fix_manifest:symlink | 3 | 0 | 3 |
| fix_manifest:bad_path_dotdot | 2 | 1 | 3 |
| fix_manifest:reserved_id | 0 | 3 | 3 |
| chunk_add_kind:bar | 1 | 1 | 2 |
| chunk_add_kind:service | 1 | 1 | 2 |
| chunk_entry_file | 1 | 0 | 1 |

### By kind (an example counts once per kind it declares)
| | train | holdout | total |
|---|---|---|---|
| bar-widget | 98 | 22 | 120 |
| bar | 52 | 18 | 70 |
| service | 30 | 15 | 45 |
| menu | 29 | 10 | 39 |
| panel | 12 | 3 | 15 |
| overlay | 11 | 3 | 14 |

### By primary kind (rarest kind; holdout strata)
| | train | holdout | total |
|---|---|---|---|
| bar-widget | 82 | 22 | 104 |
| bar | 41 | 11 | 52 |
| menu | 29 | 10 | 39 |
| service | 23 | 7 | 30 |
| panel | 12 | 3 | 15 |
| overlay | 11 | 3 | 14 |

### By origin
| | train | holdout | total |
|---|---|---|---|
| community | 82 | 31 | 113 |
| first-party | 65 | 21 | 86 |
| house | 51 | 4 | 55 |

### House plugins
| | train | holdout | total |
|---|---|---|---|
| (not house) | 147 | 52 | 199 |
| omarchy-rocketlauncher | 15 | 0 | 15 |
| omarchy-sparklekeys | 13 | 0 | 13 |
| omarchy-enricherino | 9 | 0 | 9 |
| omarchy-compliantish | 8 | 0 | 8 |
| omarchy-encyclopedic | 6 | 0 | 6 |
| omarchy-scriptural | 0 | 4 | 4 |

### Origin × kind
| | train | holdout | total |
|---|---|---|---|
| community/bar | 47 | 18 | 65 |
| house/bar-widget | 51 | 4 | 55 |
| first-party/bar-widget | 29 | 13 | 42 |
| community/menu | 27 | 10 | 37 |
| community/service | 13 | 11 | 24 |
| community/bar-widget | 18 | 5 | 23 |
| first-party/service | 17 | 4 | 21 |
| first-party/panel | 9 | 2 | 11 |
| first-party/overlay | 8 | 2 | 10 |
| first-party/bar | 5 | 0 | 5 |
| community/overlay | 3 | 1 | 4 |
| community/panel | 3 | 1 | 4 |
| first-party/menu | 2 | 0 | 2 |

### Full plugin vs chunked
| | train | holdout | total |
|---|---|---|---|
| chunked | 113 | 18 | 131 |
| full/fix | 85 | 38 | 123 |

### By complexity
| | train | holdout | total |
|---|---|---|---|
| large | 159 | 38 | 197 |
| small | 31 | 8 | 39 |
| medium | 8 | 10 | 18 |

## Still uncovered / caveats
- **First-party bar** (`shell/plugins/bar`, 177 KB) appears only as chunked tasks (manifest + 77 KB `Bar.qml`, plus 4 components), all in **train**. **First-party menu** (80 KB) fits whole and is now in **train**. All bar/menu holdout coverage comes from community plugins.
- The first-party `shell/plugins/bar/widgets/*.manifest.json` (8 built-in widgets declared by non-standard manifest filenames) is not used.
- 46 large community repos were skipped instead of chunked. Only oversized first-party, house and community bar/menu plugins get chunked.
- No answer reproduces more than about 90 KB, so the very largest files (e.g. `elsewhen` and `emojis` components over 40 KB) only show up as sibling-list context.
- Validator gaps are unchanged: no checks for marketplace category/tags or runtime QML loading. qmllint checks syntax only, because the Quickshell `qs.*` modules aren't installed.

## Reproduce
```
python3 tools_analyze.py      # verify licenses + validator for sources/repos/*
  .venv/bin/python build_dataset.py   # (needs transformers) rebuild data/*.jsonl (seeded; validates + qmllints every example)
python3 gen_docs.py           # NOTICE, sources/SOURCES.md, data/STATS.md
validator/diff_test.sh        # bash vs python validator parity (25/25)
python3 validator/qmllint_check.py data/train.jsonl data/holdout.jsonl
```
Needs `/tmp/omarchy-src` checked out at the snapshot SHA. v1 builder kept as `build_dataset_v1.py`.

## Next step
Run a smoke-test QLoRA on Qwen2.5-Coder-7B-Instruct with the train split, using a rented GPU later and only after approval. Compare it against the **base model + the Quattro plugin skill in context** on the 56 holdout prompts, broken down by kind and task.
- Primary metric: **validator pass rate** (chunk/fix answers are inserted into the real tree).
- Secondary metric: **qmllint syntax-clean rate**.
- Also track the reserved-id rate and kind↔entryPoint consistency.


===== clean/README.md =====
# clean/ — functest + provenance-cleaned training data (2026-10-12)

Rule (Harris): train only on code merged/reviewed upstream (basecamp/omarchy main, or verified listings in the official
registry plugins.omarchy.org) plus REFERENCE. No synthetic/model-generated rows, no unmerged forks, no unknown provenance,
no frontier (GPT/Claude) outputs. candidates_frontier.jsonl was intentionally NOT produced.

Files
- score_train.py / score_train.json — functest of every gold answer in data/train.jsonl (198 rows). Tree tasks are overlaid on the upstream tree; failures already in the pristine upstream tree are subtracted. House trees are at /workspace/omarchy-<name>.
- build_clean.py → train_clean.jsonl (145 after asset fix) + train_clean_manifest.json (per-row provenance, functest result, drop reasons).
- dedupe2.py → holdout_dupes_all.json (best train match per holdout row), holdout_dupes.json (7 removed, answer line-jaccard >= 0.7), holdout_clean.jsonl (49 rows, has holdout_i). data/holdout.jsonl and functest/results.json are unchanged.
- registry/: catalog_live.json (plugins.omarchy.org/catalog.json, generated 2026-10-12T14:28Z: 5,416 listings, 3,873 verified, 38 builtin),
  scan.py (clones at listingValidatedCommit, classifies LICENSE text, runs functest), selected_ids.json (418 curated), scan.jsonl (results; 1,000 rows incl. 582 from the earlier uncurated pass).
- build_pool.py → pool_registry.jsonl (152 build_from_spec examples) + pool_registry_manifest.json. Clones of kept plugins: /workspace/registry_repos/.

Curation criteria (registry): verified listing; status Available/Manual setup; updated >= 2026-08-15; stars >= 4 (or >= 2 for
panel/service/overlay/bar kinds); max 3 per GitHub owner; LICENSE file text permissive (MIT/Apache/BSD/ISC/MPL) with a copyright line and not a DHH-only fork;
functest pass; >= 2.5k chars of non-manifest code and no placeholder text; <= 90k chars; not a holdout repo; line-jaccard < 0.5 vs every holdout answer, < 0.8 vs train/pool.

Caveats
- "verified" in the registry is the directory's automated snapshot verification, not necessarily human review.
- fix_manifest rows (answer is real, prompt is a synthetic corruption) were dropped as synthetic; restoring them adds 10 passing rows.
- REFERENCE answers = holdout golds; not added to training (would leak the eval).
- runs/fix/train_rft.jsonl (169 rows) is model-generated -> dropped by rule (not scored).
- 107 curated plugins passed but are >90k chars; they need chunking (as build_dataset.py does) to be usable.

## Update 2026-10-12 (round 2)
- Registry "verified" label = reviewed (Harris).
- fix_assets.py: 6 train answers failed only because binary assets (svg/png) can't be in a text answer; re-tested with the upstream
  asset files installed alongside -> all 6 pass. Train functest now 180/198. Remaining 18 failures are real behaviour
  (sudo/pkexec, /etc/pam.d writes in first-party lock/polkit, ~/.config/hypr write, unknown module, fix_manifest trees) and stay excluded.
  score_train.before_assetfix.json keeps the previous scores.
- build_chunked.py → pool_chunked.jsonl (328 rows after final dedupe; 334 built) from the 107 large curated plugins, using build_dataset.chunk_tasks
  with community limits (manifest+entry, entry file, add-kind, 2 largest components). All 107 were already license-OK (0 license exclusions);
  36 chunks dropped for overlapping a holdout answer (overlap >= 0.5). Rows are slices of plugins that pass functest as a whole; individual chunk rows were not re-run.
- build_final.py → train_final.jsonl (593 rows) + train_final_manifest.json (per-row provenance; exact dups and same-task answer near-dups at
  >= 0.9 line-jaccard removed, which also collapses the paraphrase repeats in our own data: 32 rows).
- Third-party code is now in training text: extend ../NOTICE with the registry repos listed in pool_*_manifest.json before any public release.


===== runs/clean/train_hf.py =====
import json,sys,torch,os
from transformers import AutoTokenizer,AutoModelForCausalLM,Trainer,TrainingArguments,DataCollatorForSeq2Seq
from peft import LoraConfig,get_peft_model
from datasets import Dataset
tag,lr,ep,cap=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),int(sys.argv[4])
B="Qwen/Qwen2.5-Coder-7B-Instruct"
tok=AutoTokenizer.from_pretrained(B); assert tok.pad_token_id!=tok.eos_token_id
rows=[json.loads(l) for l in open(os.environ.get("TRAIN","train.jsonl"))]
ex=[]
for r in rows:
  p=tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True)
  full=tok.apply_chat_template(r["messages"],tokenize=False)
  assert full.startswith(p)
  pi=tok(p,add_special_tokens=False).input_ids; ai=tok(full[len(p):],add_special_tokens=False).input_ids
  ids=pi+ai
  if len(ids)>cap: continue
  ex.append({"input_ids":ids,"attention_mask":[1]*len(ids),"labels":[-100]*len(pi)+ai})
e=ex[0]; lab=[x for x in e["labels"] if x!=-100]
print("N",len(ex),"of",len(rows),"label tail",repr(tok.decode(lab[-4:])),"eos in labels",tok.eos_token_id in lab,flush=True)
m=AutoModelForCausalLM.from_pretrained(B,torch_dtype=torch.bfloat16,attn_implementation="sdpa").cuda()
m.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant":False}); m.enable_input_require_grads(); m.config.use_cache=False
m=get_peft_model(m,LoraConfig(r=16,lora_alpha=32,lora_dropout=0.05,target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],task_type="CAUSAL_LM"))
args=TrainingArguments(output_dir="out_"+tag,per_device_train_batch_size=1,gradient_accumulation_steps=4,num_train_epochs=ep,learning_rate=lr,warmup_steps=5,lr_scheduler_type="cosine",logging_steps=1,bf16=True,save_strategy="no",report_to="none",seed=0,remove_unused_columns=False)
tr=Trainer(model=m,args=args,train_dataset=Dataset.from_list(ex),data_collator=DataCollatorForSeq2Seq(tok,padding=True))
tr.train()
json.dump(tr.state.log_history,open(f"loss_{tag}.json","w"),indent=1)
m.save_pretrained("adapter_"+tag); tok.save_pretrained("adapter_"+tag)
print("TRAIN_DONE",tag,torch.cuda.max_memory_allocated()/1e9,flush=True)


===== runs/clean/merge.py =====
import torch,sys
from transformers import AutoTokenizer,AutoModelForCausalLM
from peft import PeftModel
B="Qwen/Qwen2.5-Coder-7B-Instruct"
m=AutoModelForCausalLM.from_pretrained(B,torch_dtype=torch.bfloat16)
m=PeftModel.from_pretrained(m,sys.argv[1]).merge_and_unload()
m.save_pretrained(sys.argv[2],safe_serialization=True); AutoTokenizer.from_pretrained(B).save_pretrained(sys.argv[2]); print("MERGED")


===== runs/clean/gen_m.py =====
import json,sys
from vllm import LLM,SamplingParams
from vllm.lora.request import LoRARequest
def main():
  # usage: gen_v.py file.jsonl n name:adapter_dir [name:adapter_dir ...]  (adapter 'none' = stock)
  rows=[json.loads(l) for l in open(sys.argv[1])][:int(sys.argv[2])]
  llm=LLM(sys.argv[3].split(":")[1],max_model_len=32768,gpu_memory_utilization=0.9)
  tok=llm.get_tokenizer()
  ps=[tok.apply_chat_template(r["messages"][:-1],tokenize=False,add_generation_prompt=True) for r in rows]
  sp=SamplingParams(temperature=0,max_tokens=16000,repetition_penalty=1.05)
  for k,spec in enumerate(sys.argv[3:]):
    name,ad=spec.split(":")
    outs=llm.generate(ps,sp)
    with open(f"gen_{name}.jsonl","w") as f:
      for r,o in zip(rows,outs): f.write(json.dumps({"task":r["task"],"output":o.outputs[0].text,"finish":o.outputs[0].finish_reason})+"\n")
    print("GEN_DONE",name,flush=True)
if __name__=="__main__": main()


===== runs/clean/score49.py =====
#!/usr/bin/env python3
"""Score gens on the 49-prompt clean holdout with the real functest (functest/rescore.py logic).
usage: score49.py name=path.jsonl ...   path may have 49 rows (clean order) or 56 rows (full holdout; filtered by holdout_i)."""
import json, os, sys, collections
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "functest"))
import rescore
clean = [json.loads(l) for l in open(os.path.join(ROOT, "clean/holdout_clean.jsonl"))]
idx = [c["holdout_i"] for c in clean]
out = os.path.join(HERE, "results49.json")
res = json.load(open(out)) if os.path.exists(out) else {"models": {}, "rows": {}}
def loopy(t):
    lines = [l for l in t.splitlines() if l.strip()]
    return len(lines) > 50 and collections.Counter(lines).most_common(1)[0][1] > max(30, len(lines) // 5)
for spec in sys.argv[1:]:
    n, p = spec.split("=", 1)
    g = [json.loads(l) for l in open(p)]
    if len(g) == 56: g = [g[i] for i in idx]
    assert len(g) == 49, (n, len(g))
    for c, x in zip(clean, g): assert x.get("task", c["task"]) == c["task"], (n, c["task"], x.get("task"))
    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(lambda a: rescore.score_row(*a), [(i, rescore.hold[i], x) for i, x in zip(idx, g)]))
    for r, x in zip(rows, g): r["chars"] = len(x["output"]); r["loop"] = loopy(x["output"])
    s = rescore.summarize(rows, {})
    s = {k: v for k, v in s.items() if not k.startswith("old_")}
    s["looping"] = sum(r["loop"] for r in rows); s["median_chars"] = sorted(r["chars"] for r in rows)[24]
    res["rows"][n] = rows; res["models"][n] = s
    print(n, s["new_overall"], s["new_full_plugin"], "trunc", s["truncated"], "loop", s["looping"], flush=True)
    json.dump(res, open(out, "w"), indent=1)


===== runs/clean/pipe.sh =====
#!/bin/bash
# usage: pipe.sh TAG   (train_TAG.jsonl -> adapter_TAG -> merged_TAG -> gen_clean_TAG.jsonl)
set -x; cd /root/w; T=$1
pip install -q "transformers==4.55.2" "peft==0.17.1" datasets accelerate >pip.log 2>&1
TRAIN=train_$T.jsonl python3 train_hf.py $T 1e-4 2 32768 || exit 1
python3 merge.py adapter_$T merged_$T || exit 1
python3 gen_m.py holdout.jsonl 49 clean_$T:merged_$T || exit 1
echo PIPE_DONE


===== runs/rl/PLAN.md =====
# GRPO plan: Omarchy specialist, Qwen2.5-Coder-14B-Instruct

Status: plan only, not run yet. Start from the warm-up SFT checkpoint in `runs/clean14` (merged weights, or base + adapter).

## Why RL
SFT teaches the format, but the model still doesn't learn to *finish*. The 7B clean SFT scored 10/49 on the functest; 40/49 hit the length limit and 10 looped. GRPO optimizes the real target directly (a plugin that loads and passes the functest, delivered in a reasonable length), and it punishes runaway generations.

## Framework
- **TRL `GRPOTrainer`** with `use_vllm=True` (colocate mode), plus PEFT LoRA (r=32, alpha=64, all linear layers) on the SFT-merged 14B. This is the simplest stack and the same HF/PEFT code as `train_hf.py`.
- Fallback if TRL throughput is too low on long completions: **verl** (FSDP + vLLM rollout) on 2 GPUs.
- Pin versions alongside the image we already use (vllm 0.10.x). Do a 2-step dry run before paying for the full run.

## Prompts
- Train: the specs in `clean/train_final.jsonl`, deduped by prompt (~250 unique `build_from_spec`/`add_panel`/`chunk_*`/`fix_manifest`-style asks). Weight build_from_spec at 2x because it's 26 of the 49 holdout prompts.
- Add Harris's future real asks as they come in (store them in `runs/rl/prompts_real.jsonl`; same schema; a functest spec is required to get a reward).
- Never train on `clean/holdout_clean.jsonl` (49). It stays the eval set.
- Curriculum: drop prompts where all 8 samples score 0 or all score 1 (no gradient signal). Re-filter every 50 steps.

## Rollouts
- Group size **G = 8** per prompt. 8 prompts/step gives 64 completions per step.
- Sampling: temperature 0.8, top_p 0.95, max_completion_length **12k tokens** (16k in eval). Shorter during RL is deliberate, because the length pressure is the point.
- KL beta 0.02 against the SFT reference (or beta=0 with a clipped ratio, Dr-GRPO style; try both in the dry run). LR 1e-6 (full) / 5e-6 (LoRA), 1 PPO epoch per batch.

## Reward (range 0 to 1, plus penalties)
Computed by the same `functest/rescore.py` `score_row` logic that score49 uses:
| component | value |
|---|---|
| parses: fenced files extracted, manifest JSON valid | +0.1 |
| plugin loads in the shell harness (qmllint / validator pass, no load errors) | +0.3 |
| functest pass (full plugin: all checks; partial tasks: the task check) | +0.6 (scaled by fraction of checks passed when available) |
| truncated (finish_reason == "length") | -0.5, and the functest component is zeroed |
| loop detected (`loopy()` from score49) | -0.3 |
| length shaping: chars beyond 1.5x the reference answer length | -0.1 per extra 1x, capped at -0.3 |

## Sandboxing
- Run the functest **on the GPU box** in a pool of rootless containers/`bwrap` jails (no network, 60s timeout, tmpfs workdir, 2 GB memory cap). 64 completions per step across ~16 CPU workers should take about 30-60s per step and overlaps with the next rollout batch.
- Fallback: ship completions back to the box over paramiko (`rx.py`), score there, and return rewards. That's simpler but adds latency, so use it only if the harness won't install on the GPU image.
- Preflight: run the reward function on the 49 holdout gens we already have (stock14b, clean_b) and confirm it reproduces the score49 numbers before training.

## Steps and hardware
- **150-250 steps** × 64 completions = 10-16k rollouts. Evaluate on the 49 every 50 steps (greedy, rp 1.05, 16k) and keep the best checkpoint.
- Hardware: **2× H100 80GB** (vLLM rollout on GPU 0, LoRA training on GPU 1 in TRL server mode), or 1× H100 in colocate mode with sleep mode. Long completions dominate the cost: roughly 64 × ~6k tokens per step, so ~2-4 min per step on 2×H100.

## Cost estimate (Vast)
| item | estimate |
|---|---|
| 2×H100 at ~$4-7/h × 10-14 h for 200 steps + evals | $60-100 |
| dry runs, debugging, harness setup (~4 h) | $20-30 |
| one rerun or ablation (beta / length penalty) | $50-100 |
| **total** | **~$150-250**, inside the $150-300 envelope; hard stop at $300 |

Kill criteria: stop if holdout overall doesn't improve over the SFT checkpoint by step 100, or if mean reward collapses or length explodes.

## Success target
Beat the SFT checkpoint on overall/49 and full/32, with truncation under 10/49 and loops at 0. Stretch goal: reach the frontier API range (GPT-5.6 24/49, Opus 23/49).


===== functest/functest.py =====
#!/usr/bin/env python3
"""Combined functional test = static checks + real-shell runtime. `python3 functest.py <plugin_dir>`"""
import json, os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import static_checks, runtime

SKIP_DIRS = {".git", "node_modules", "tests", "test", "__pycache__", "preview", "stubs", "lint", ".github", "fixtures", "docs", "screenshots", "assets"}
def read_dir(d):
    files = {}
    for r, ds, fs in os.walk(d):
        ds[:] = [x for x in ds if x not in SKIP_DIRS]
        for f in fs:
            p = os.path.relpath(os.path.join(r, f), d)
            if os.path.getsize(os.path.join(r, f)) > 2_000_000: continue
            try: files[p] = open(os.path.join(r, f), encoding="utf-8").read()
            except Exception: pass
    return files

def categories(st_fails, rt):
    cats = sorted({c for c, _ in st_fails})
    for e in (rt or {}).get("errors", []):
        if e.startswith("DANGEROUS") or e.startswith("wrote outside"): cats.append("rt-dangerous-write")
        elif "is not a type" in e or "is not installed" in e or "module" in e.lower() and "not" in e: cats.append("rt-unresolved-type/import")
        elif re.search(r"(TypeError|ReferenceError|is not a function|is not defined|undefined)", e): cats.append("rt-js-error")
        elif re.search(r"(Expected token|Syntax|Unexpected token|Unexpected)", e): cats.append("rt-qml-syntax")
        elif re.search(r"(Cannot assign|Invalid property|Non-existent|Unable to assign|does not have a property|Invalid attached)", e): cats.append("rt-bad-property")
        elif "rejected" in e: cats.append("rt-manifest-rejected")
        elif "never registered" in e or "failed to load" in e or "load failed" in e: cats.append("rt-load-failed")
        elif "never instantiated" in e or "not instantiated" in e or "not created" in e or "not active" in e: cats.append("rt-not-instantiated")
        elif "zero size" in e: cats.append("rt-zero-size")
        else: cats.append("rt-other")
    return sorted(set(cats))

def test(files=None, src_dir=None, run_runtime=True):
    if src_dir: files = read_dir(src_dir)
    sf, sw = static_checks.check(files)
    rt = None
    man_ok = True
    try: m = json.loads(files.get("manifest.json", "")); man_ok = isinstance(m, dict) and "id" in m
    except Exception: man_ok = False
    if run_runtime and man_ok:
        rt = runtime.run(src_dir=src_dir) if src_dir else runtime.run(files=files)
        timing = ("never instantiated", "not instantiated", "not created", "not active", "IPC unreachable", "harness timeout")
        if rt.get("errors") and all(any(t in e for t in timing) for e in rt["errors"]):
            rt2 = runtime.run(src_dir=src_dir) if src_dir else runtime.run(files=files)   # async-load timing retry
            rt2["retried"] = True
            if len(rt2.get("errors", [])) <= len(rt["errors"]): rt = rt2
    elif run_runtime: rt = {"pass": False, "errors": ["no valid manifest.json"]}
    if rt and isinstance(man_ok, bool) and man_ok:
        ep = (m.get("entryPoints") or {}).get("barWidget") if isinstance(m.get("entryPoints"), dict) else None
        src = files.get(ep or "", "")
        for e in list(rt.get("errors", [])):
            if "zero size" in e and re.search(r"^\s*(visible|implicitWidth|width)\s*:[^\n]*(\?|&&|\|\||>|<|===|!==)", src, re.M):
                rt["errors"].remove(e); rt.setdefault("soft", []).append(e + " (conditionally hidden by design)")
        rt["pass"] = not rt["errors"]
    ok = not sf and (rt is None or rt.get("pass"))
    return {"pass": ok, "static_fails": sf, "static_flags": sw, "runtime": rt, "categories": categories(sf, rt)}

if __name__ == "__main__":
    r = test(src_dir=sys.argv[1])
    print(json.dumps({k: v for k, v in r.items()}, indent=1)[:6000])


===== functest/rescore.py =====
#!/usr/bin/env python3
"""Rescore runs/smoke-2026-10-11/gen_*.jsonl with the functional test.
Full-plugin tasks (build_from_spec, add_panel): the model's files ARE the plugin.
Tree tasks (chunk_*, fix_manifest): model files are overlaid on the real upstream plugin tree at the holdout commit
(sources/repos/<id>, or Omarchy's first-party dir); failures already present in the untouched upstream tree
(baseline) are subtracted, so only regressions caused by the model count."""
import json, os, re, sys, glob, hashlib, collections
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "validator"))
import functest
from build_parse import parse
RUN = os.path.join(ROOT, "runs/smoke-2026-10-11")
hold = [json.loads(l) for l in open(os.path.join(ROOT, "data/holdout.jsonl"))]
FULL = ("build_from_spec", "add_panel")
REPO_FOR = {"https://github.com/salted-sorbet/salted.bar": "salted.bar", "https://github.com/RohitKaushal7/omarchy-beam": "dev.reuk.beam",
            "https://github.com/pxllbt/better-bar": "pix.bar", "https://github.com/TECHNOCRAFT27/floating-waybar": "floating-waybar",
            "https://github.com/varlet99/omarchy-tablet": "surface.tablet", "https://github.com/jankeesvw/omarchy-time-machine": "jankeesvw.time-machine",
            "https://github.com/scottjones/omarchy-flush-bar": "scottjones.flush-bar"}
def tree_dir(h):
    m = h["meta"]
    if m["origin"] == "first-party": return "/opt/ft/omarchy/" + m["plugin_path"]
    return os.path.join(ROOT, "sources/repos", REPO_FOR[m["repo"]])
CACHE = os.path.join(HERE, "cache"); os.makedirs(CACHE, exist_ok=True)

def norm(e): return re.sub(r"\d+", "N", re.sub(r"/opt/ft/runs/\w+", "", e))

def build_tree(h, files):
    task = h["task"].split(":")[0]
    base = functest.read_dir(tree_dir(h))
    prompt = h["messages"][1]["content"]
    pm = re.search(r"```json\n(.*?)\n```", prompt, re.S)
    if task == "fix_manifest":
        base.pop("manifest.json", None)                    # model must supply the fixed manifest
    elif pm and task != "chunk_manifest_entry":
        base["manifest.json"] = pm.group(1) + "\n"        # the manifest as given in the prompt
    if task == "chunk_manifest_entry":
        # model writes manifest + entry file(s): drop upstream versions of those
        ref = parse(h["messages"][2]["content"])
        for p in ref: base.pop(p, None)
    t = dict(base); t.update({p: c for p, c in files.items() if ".." not in p and not p.startswith("/")})
    return base, t

_baseline = {}
def baseline(i, h):
    if i in _baseline: return _baseline[i]
    ref = parse(h["messages"][2]["content"])
    _, t = build_tree(h, ref)                              # upstream tree + reference answer = known-good state
    r = functest.test(files=t)
    _baseline[i] = ({tuple(x) for x in r["static_fails"]}, {norm(e) for e in (r["runtime"] or {}).get("errors", [])}, r)
    return _baseline[i]

def score_row(i, h, g):
    task = h["task"].split(":")[0]
    files = parse(g["output"])
    if not files: return dict(task=h["task"], pass_=False, categories=["no-files-parsed"], finish=g["finish"])
    if task in FULL:
        key = hashlib.sha1(json.dumps(files, sort_keys=True).encode()).hexdigest()
        cp = os.path.join(CACHE, key + ".json")
        if os.path.exists(cp): r = json.load(open(cp))
        else:
            r = functest.test(files=files); json.dump(r, open(cp, "w"))
    else:
        bs, br, _ = baseline(i, h)
        _, t = build_tree(h, files)
        key = hashlib.sha1(json.dumps(t, sort_keys=True).encode()).hexdigest()
        cp = os.path.join(CACHE, key + ".json")
        if os.path.exists(cp): r = json.load(open(cp))
        else:
            r = functest.test(files=t); json.dump(r, open(cp, "w"))
        r = json.loads(json.dumps(r))
        r["static_fails"] = [x for x in r["static_fails"] if tuple(x) not in bs]
        if r["runtime"]:
            r["runtime"]["errors"] = [e for e in r["runtime"]["errors"] if norm(e) not in br]
            r["runtime"]["pass"] = not r["runtime"]["errors"]
        r["categories"] = functest.categories(r["static_fails"], r["runtime"])
        r["pass"] = not r["static_fails"] and (r["runtime"] is None or r["runtime"]["pass"])
    rt = r.get("runtime") or {}
    return dict(task=h["task"], pass_=bool(r["pass"]), categories=r["categories"], finish=g["finish"],
                static_fails=[f"{a}: {b}"[:200] for a, b in r["static_fails"]][:8],
                runtime_errors=[e[:240] for e in rt.get("errors", [])][:8], runtime_checks=rt.get("checks"),
                soft=[e[:160] for e in rt.get("soft", [])][:4], files=sorted(files)[:12])

def summarize(rows, old):
    full = [r for r in rows if r["task"].split(":")[0] in FULL]
    per = collections.defaultdict(lambda: [0, 0])
    for r in rows: t = r["task"].split(":")[0]; per[t][0] += r["pass_"]; per[t][1] += 1
    cats = collections.Counter(c for r in rows if not r["pass_"] for c in r["categories"])
    return dict(new_overall=f"{sum(r['pass_'] for r in rows)}/{len(rows)}", new_full_plugin=f"{sum(r['pass_'] for r in full)}/{len(full)}",
                old_overall=old.get("validate_pass"), old_full_plugin=old.get("full_plugin_pass"),
                per_task={k: f"{a}/{b}" for k, (a, b) in per.items()}, failure_categories=dict(cats.most_common()),
                truncated=sum(r["finish"] == "length" for r in rows))

if __name__ == "__main__":
    names = sys.argv[1:] or sorted(os.path.basename(f)[4:-6] for f in glob.glob(os.path.join(RUN, "gen_*.jsonl")))
    old = json.load(open(os.path.join(RUN, "summary.json")))
    # old shallow scores for models missing from summary.json: recompute from scores_*.json
    def old_for(n):
        if n in old: return old[n]
        p = os.path.join(RUN, f"scores_{n}.json")
        if not os.path.exists(p): return {}
        s = json.load(open(p)); f = [r for r in s if r["task"].split(":")[0] in FULL]
        return {"validate_pass": f"{sum(r['pass_'] for r in s)}/{len(s)}", "full_plugin_pass": f"{sum(r['pass_'] for r in f)}/{len(f)}"}
    # baselines first (sequential per tree; cheap)
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda i: baseline(i, hold[i]), [i for i, h in enumerate(hold) if h["task"].split(":")[0] not in FULL]))
    out_path = os.path.join(HERE, "results.json")
    results = json.load(open(out_path)) if os.path.exists(out_path) else {"models": {}, "rows": {}}
    for n in names:
        if n == "REFERENCE": gens = [{"output": h["messages"][2]["content"], "finish": "stop"} for h in hold]
        else: gens = [json.loads(l) for l in open(os.path.join(RUN, f"gen_{n}.jsonl"))]
        with ThreadPoolExecutor(8) as ex:
            rows = list(ex.map(lambda a: score_row(*a), [(i, hold[i], g) for i, g in enumerate(gens)]))
        results["rows"][n] = rows
        results["models"][n] = summarize(rows, old_for(n))
        print(n, json.dumps({k: results["models"][n][k] for k in ("old_overall", "new_overall", "old_full_plugin", "new_full_plugin")}), flush=True)
        json.dump(results, open(out_path, "w"), indent=1)


===== functest/runtime.py (first 6000 chars) =====
#!/usr/bin/env python3
"""Runtime functional test: install one plugin into a throwaway HOME and boot the REAL Omarchy shell
(omarchy-src shell/, Quickshell master @4f508be on Qt 6.11.3) on a headless sway (wlroots) compositor,
inside a bubblewrap sandbox (read-only /, private /tmp, no network). Enable it via shell.json exactly like
`omarchy plugin enable`, summon it through the shell's own IPC (`shell summon <id>`), then probe registry /
loader / bar-geometry state through one harness-only IPC function (ftProbe). Log lines attributable to the
plugin's directory (or the shell's per-plugin failure messages) are collected as load/runtime errors.
"""
import json, os, re, shutil, subprocess, tempfile, hashlib, time

QS = "/opt/qs611/bin/qs"
OMARCHY = "/opt/ft/omarchy"
SWAY_SOCK = "/opt/ft/swayrt/wayland-1"
RUNS = "/opt/ft/runs"
ENV_BASE = {
    "LD_LIBRARY_PATH": "/opt/wl/lib/x86_64-linux-gnu:/opt/qt/6.11.3/gcc_64/lib",
    "QML_IMPORT_PATH": "/opt/qs611/qml", "QT_QPA_PLATFORM": "wayland", "WAYLAND_DISPLAY": SWAY_SOCK,
    "OMARCHY_PATH": OMARCHY, "PATH": f"/opt/ft/stubbin:{OMARCHY}/bin:/usr/local/bin:/usr/bin:/bin",
    "LANG": "C.UTF-8", "QT_QUICK_BACKEND": "software", "XDG_SESSION_TYPE": "wayland",
}
SENTINELS = {".config/hypr/hyprland.conf": "# sentinel hyprland\nsource = ~/.config/hypr/looknfeel.conf\n",
             ".config/hypr/looknfeel.conf": "# sentinel looknfeel\n", ".config/hypr/looknfeel.lua": "-- sentinel\n",
             ".config/hypr/bindings.conf": "# sentinel bindings\nbind = SUPER, Return, exec, alacritty\n",
             ".config/hypr/monitors.conf": "# sentinel monitors\n", ".bashrc": "# sentinel bashrc\n"}
ALLOWED_WRITE = re.compile(r"^(\.cache/|\.local/state/|\.local/share/(?!omarchy)|\.config/omarchy/plugins/|\.config/omarchy/shell\.json$|\.config/(?!hypr/|omarchy/|systemd/|autostart/|environment\.d/)[^/]+/)")

DRIVER = r'''#!/bin/bash
cd "$FT_DIR"
"$QS" -p "$OMARCHY_PATH/shell" > "$FT_DIR/qs.log" 2>&1 &
QPID=$!
ipc() { timeout 4 "$QS" ipc -p "$OMARCHY_PATH/shell" call shell "$@" 2>>"$FT_DIR/ipc.err"; }
for i in $(seq 1 40); do sleep 0.25; ipc ping >/dev/null && break; kill -0 $QPID 2>/dev/null || break; done
sleep 2.5
ipc ftProbe "$FT_ID" > "$FT_DIR/probe0.json"
if [ -n "$FT_SUMMON" ]; then ipc summon "$FT_ID" '{}' > "$FT_DIR/summon.txt"; fi
sleep 2.5
ipc ftProbe "$FT_ID" > "$FT_DIR/probe1.json"
sleep 2
ipc ftProbe "$FT_ID" > "$FT_DIR/probe2.json"
kill -0 $QPID 2>/dev/null && echo alive > "$FT_DIR/alive"
kill $QPID 2>/dev/null; sleep 0.3; kill -9 $QPID 2>/dev/null; wait $QPID 2>/dev/null
echo $? > "$FT_DIR/qs.rc"
'''

ERR_PAT = re.compile(r"(Error|error|failed|is not a type|not installed|Cannot|Unable to|Invalid|Expected token|Unexpected|undefined|is not a function|Non-existent|Type .* unavailable|is not defined|No such|Unknown|not found|cannot)")
SOFT_PAT = re.compile(r"(Read of .* failed: File does not exist|summon: no live bar widget|IpcHandler at|another handler is registered for target|Host \S+ not found|Network access is disabled|Connection refused|Temporary failure in name resolution|Name or service not known|QNetworkReply|Process failed to start, likely because the binary could not be found|Binding loop detected|QFont::|Could not connect to DBus|pipewire|polkit)")

def _hash(p):
    try: return hashlib.sha1(open(p, "rb").read()).hexdigest()
    except Exception: return None

def _snapshot(home):
    out = {}
    for r, ds, fs in os.walk(home):
        for f in fs:
            p = os.path.join(r, f); rel = os.path.relpath(p, home)
            try: st = os.lstat(p); out[rel] = (st.st_size, st.st_mtime_ns)
            except Exception: pass
    return out

def install_files(dst, files):
    for p, c in files.items():
        if ".." in p or p.startswith("/"): continue
        fp = os.path.join(dst, p); os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w") as f: f.write(c)

def shell_config(pid, kinds):
    cfg = json.load(open(f"{OMARCHY}/config/omarchy/shell.json"))
    cfg.setdefault("plugins", [])
    if "bar-widget" in kinds:
        cfg["bar"]["layout"].setdefault("right", []).insert(0, {"id": pid})
    if "bar" in kinds: cfg["bar"]["id"] = pid
    if any(k in kinds for k in ("panel", "overlay", "menu", "service")):
        cfg["plugins"].append({"id": pid})
    return cfg

def run(files=None, src_dir=None, timeout=40, keep=False):
    """files: {relpath: text} or src_dir: a plugin folder. Returns dict."""
    os.makedirs(RUNS, exist_ok=True)
    S = tempfile.mkdtemp(dir=RUNS, prefix="r")
    home = os.path.join(S, "home"); os.makedirs(home)
    res = {"errors": [], "soft": [], "checks": {}}
    try:
        if src_dir:
            man = json.load(open(os.path.join(src_dir, "manifest.json")))
        else:
            man = json.loads(files["manifest.json"])
        pid = str(man.get("id")); kinds = man.get("kinds") or []
        if not isinstance(kinds, list): kinds = []
        res["id"], res["kinds"] = pid, kinds
        pdir = os.path.join(home, ".config/omarchy/plugins", re.sub(r"[^A-Za-z0-9._-]", "_", pid) or "x")
        if src_dir: shutil.copytree(src_dir, pdir, symlinks=True, ignore=shutil.ignore_patterns(".git"))
        else: os.makedirs(pdir); install_files(pdir, files)
        for rel, txt in SENTINELS.items():
            fp = os.path.join(home, rel); os.makedirs(os.path.dirname(fp), exist_ok=True); open(fp, "w").write(txt)
        json.dump(shell_config(pid, kinds), open(os.path.join(home, ".config/omarchy/shell.json"), "w"), indent=1)
        before = _snapshot(home)
        rt = os.path.join(S, "rt"); os.makedirs(rt, mode=0o700)
        open(os.path.join(S, "driver.sh"), "w").write(DRIVER)
        summon = any(k in kinds for k in ("panel", "overlay", "menu", "bar-widget"))
        env = dict(ENV_BASE, HOME=home, XDG_RUNTIME_DIR=rt, FT_DIR=S, FT_ID=pid, QS=QS, FT_SUMMON="1" if summon else "",
                   XDG_CONFIG_HOME=os.path.join(home, ".config"), XDG_CACHE_HOME=os.path.join(home, ".cache"),
                   

===== functest/static_checks.py (first 4000 chars) =====
#!/usr/bin/env python3
"""Static checks for an Omarchy (Quickshell) plugin given as {relpath: text}.
Returns (fails, flags): fails are hard failures, flags are advisory.
Each item is (category, detail)."""
import json, re, os, posixpath

QT6_MODULES = {
    "QtQuick", "QtQuick.Controls", "QtQuick.Controls.Basic", "QtQuick.Controls.Fusion",
    "QtQuick.Controls.Material", "QtQuick.Controls.Universal", "QtQuick.Controls.Imagine",
    "QtQuick.Controls.impl", "QtQuick.Templates", "QtQuick.Layouts", "QtQuick.Window", "QtQuick.Effects",
    "QtQuick.Shapes", "QtQuick.Particles", "QtQuick.Dialogs", "QtQuick.LocalStorage", "QtQuick.VectorImage",
    "QtQuick.Pdf",
    "QtQml", "QtQml.Models", "QtQml.WorkerScript", "QtCore", "QtMultimedia", "QtPositioning", "QtLocation",
    "Qt5Compat.GraphicalEffects", "Qt.labs.platform", "Qt.labs.folderlistmodel", "Qt.labs.settings",
    "Qt.labs.qmlmodels", "Qt.labs.animation", "Qt.labs.sharedimage", "Qt.labs.wavefrontmesh", "QtTest",
    "QtWebSockets", "QtSvg",
}
QS_MODULES = set("""Quickshell Quickshell.Bluetooth Quickshell.DBusMenu Quickshell.Hyprland Quickshell.I3
Quickshell.Io Quickshell.Networking Quickshell.Services.Greetd Quickshell.Services.Mpris
Quickshell.Services.Notifications Quickshell.Services.Pam Quickshell.Services.Pipewire Quickshell.Services.Polkit
Quickshell.Services.SystemTray Quickshell.Services.UPower Quickshell.Wayland Quickshell.Widgets
Quickshell.WindowManager Quickshell.X11""".split())
OMARCHY_MODULES = {"qs.Commons", "qs.Ui"}   # the only Omarchy-provided QML modules (shell/Commons, shell/Ui qmldir)
QT5_ONLY = {"QtGraphicalEffects": "Qt5 QtGraphicalEffects (Qt6 = Qt5Compat.GraphicalEffects / QtQuick.Effects)",
            "QtQuick.Controls.Styles": "Qt5-only Controls 1 styles", "QtQuick.Extras": "Qt5-only QtQuick.Extras",
            "QtQuick.PrivateWidgets": "Qt5-only", "QtQuick.Dialogs.qml": "Qt5-only", "QtWebKit": "Qt5-only"}

ALLOWED_ENTRY_EXT = (".qml",)
IMPORT_RE = re.compile(r'^\s*import\s+([^\s;]+)(?:\s+([\d.]+))?(?:\s+as\s+\w+)?', re.M)

# JS / Node / browser / fake-host idioms that cannot exist in a Quickshell QML runtime
JS_FAKE = [
    (r"^(?!.*typeof\s+require).*\brequire\s*\(\s*['\"]", "node require()"), (r"\bchild_process\b", "node child_process"),
    (r"^\s*import\s+[\w{}*,\s]+\s+from\s+['\"]", "ES module import"), (r"^(?!.*typeof\s+module)\s*module\.exports\b", "CommonJS exports"),
    (r"\bdocument\.(getElementById|querySelector|createElement|body)", "browser DOM"),
    (r"\bwindow\.(addEventListener|localStorage)", "browser window API"), (r"\bprocess\.env\b", "node process.env"),
    (r"\bQNetworkAccessManager\b|\bQProcess\b|\bQFile\b|\bQTimer\b", "C++ Qt class used from QML/JS"),
    (r"\bimport\s+omarchy\b|\bfrom\s+['\"]omarchy['\"]|\bOmarchy\.(api|shell|notify|exec|register)", "made-up omarchy JS/QML API"),
    (r"\bQuickshell\.clipboard\b", "Quickshell.clipboard is not a real API"),
    (r"\bStyle\.font\.size\s*\(", "Style.font.size() is not a real API"),
    (r"\bfetch\s*\(\s*['\"`]http", "browser fetch()"),
]
# Shell-out / write danger: target paths
DANGER_PATHS = r"(\.config/hypr\b|/etc/|/usr/(lib|share|local|include)/|/boot/|/var/(lib|log)/|\.bashrc|\.zshrc|\.profile\b|\.config/omarchy/(current|themes|hooks)|\.local/share/omarchy|/sys/|/dev/sd)"
WRITE_VERBS = r"(>>?|\btee\b|\bcp\b|\bmv\b|\brm\b|\bsed\s+-i|\bln\s+-s|\bdd\b|\bchmod\b|\bchown\b|\binstall\b|\btruncate\b|setText|write_text|writeFile|open\([^)]*['\"][wa]\+?['\"])"
DANGER_CMDS = [(r"curl[^\n|]*\|\s*(ba|z)?sh\b|wget[^\n|]*\|\s*(ba|z)?sh\b", "curl|sh"),
               (r"\brm\s+-rf?\s+(~|\$HOME|/)(\s|$|['\"])", "rm -rf of home/root"),
]
FAKE_DATA = [(r"[\"']Item [1-3][\"']", "'Item 1/2/3' placeholder data"), (r"[Ll]orem ipsum", "lorem ipsum"),
             (r"[\"']John Doe[\"']|[\"']Jane Doe[\"']", "fake person"), (r"\bfoo\b.*\bbar\b.*\bbaz\b", "foo/bar/baz"),
             (r"Math\.random\(\)\s*\*\s*\d+.*(speed|usage|percent|temp|cpu|mbps|download|upload)", "random numbers as data")

===== train_final stats =====
rows 593; tasks Counter({'chunk_component': 254, 'build_from_spec': 181, 'chunk_manifest_entry': 84, 'chunk_add_kind:bar-widget': 27, 'chunk_add_kind:service': 15, 'chunk_entry_file': 15, 'add_panel': 7, 'chunk_add_kind:overlay': 5, 'chunk_add_kind:bar': 2, 'chunk_add_kind:panel': 2, 'chunk_add_kind:menu': 1}); answer chars median 23748 max 90043 p90 64225

===== training example task=build_from_spec =====
[{"role": "system", "content": "You are an Omarchy plugin expert. You write complete, valid Omarchy (Quattro / omarchy-shell, Quickshell QML) plugins. Manifests use schemaVersion 1, a namespaced id that never uses the reserved omarchy.* namespace, name, version, kinds (bar-widget|panel|overlay|menu|service|bar) with a matching safe relative entryPoints path for every kind, and no symlinks. Return every file in full as '### path' followed by a fenced code block."}, {"role": "user", "content": "I want an Omarchy bar-widget plugin named Omarchy BBS (id `io.github.thoughtlesslabs.omarchy-bbs`): A native, encrypted community BBS for Omarchy users. Give me every file."}, {"role": "assistant", "content": "### manifest.json\n```json\n{\n  \"schemaVersion\": 1,\n  \"id\": \"io.github.thoughtlesslabs.omarchy-bbs\",\n  \"name\": \"Omarchy BBS\",\n  \"version\": \"0.11.5\",\n  \"author\": \"thoughtlesslabs\",\n  \"license\": \"MIT\",\n  \"description\": \"A native, encrypted community BBS for Omarchy users\",\n  \"kinds\": [\"bar-widget\"],\n  \"entryPoints\": {\n    \"barWidget\": \"BarWidget.qml\"\n  },\n  \"barWidget\": {\n    \"displayName\": \"Omarchy BBS\",\n    \"description\": \"Open the native Omarchy community board\",\n    \"category\": \"Social\",\n    \"allowMultiple\": false,\n    \"defaultSection\": \"right\"\n  }\n}\n```\n\n### BarWidget.qml\n```qml\nimport QtQuick\nimport Quickshell\nimport Quickshell.Io\nimport qs.Commons\nimport qs.Ui\n\nBarWidget {\n  id: root\n  moduleName: \"io.github.thoughtlesslabs.omarchy-bbs\"\n  readonly property string launcherPath: Qt.resolvedUrl(\"bin/omarchy-bbs\").toString().replace(\"file://\", \"\")\n  readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false\n  readonly property bool popoutSwitchClosing: panelLoader.item ? panelLoader.item.popoutSwitchClosing === true : false\n  property int unreadCount: 0\n  property int mentionCount: 0\n  property bool updateAvailable: false\n  property string latestVersion: \"\"\n  property bool detached: false\n\n  function command(action) {\n    if (!root.bar) return \"\"\n    return Util.shellQuote(root.launcherPath) + \" \" + action\n  }\n\n  function open() { if (panelLoader.item) panelLoader.item.open() }\n  function close() { if (panelLoader.item) panelLoader.item.close() }\n  function toggle() {\n    if (root.detached) root.reattach()\n    else if (panelLoader.item) panelLoader.item.toggle()\n  }\n  function detach() {\n    root.close()\n    root.detached = true\n    Qt.callLater(function() { detachedView.open() })\n  }\n  function reattach() {\n    root.detached = false\n    root.open()\n  }\n  function closeForPopoutSwitch() { if (panelLoader.item) panelLoader.item.closeForPopoutSwitch() }\n  function launch(action) { if (root.bar) root.bar.run(root.command(action)) }\n  function refreshStatus() {\n    if (!statusProcess.running && root.launcherPath !== \"\") {\n      statusProcess.command = [root.launcherPath, \"status\", \"--notify\"]\n      statusProcess.running = true\n    }\n  }\n  function installUpdate() {\n    if (root.bar) root.bar.run(\"omarchy plugin update io.github.thoughtlesslabs.omarchy-bbs --yes\")\n  }\n  function injectPanel() {\n    if (!panelLoader.item) return\n    panelLoader.item.bar = root.bar\n    panelLoader.item.anchorItem = button\n    panelLoader.item.hostWidget = root\n    panelLoader.item.launcherPath = root.launcherPath\n  }\n\n  implicitWidth: button.implicitWidth\n  implicitHeight: button.implicitHeight\n  onBarChanged: injectPanel()\n\n  Loader {\n    id: panelLoader\n    active: true\n    source: Qt.resolvedUrl(\"Panel.qml\")\n    visible: false\n    onLoaded: {\n      root.injectPanel()\n      Qt.callLater(root.injectPanel)\n    }\n  }\n\n  FloatingWindow {\n    id: detachedWindow\n    visible: root.detached\n    title: \"Omarchy BBS\"\n    color: Color.background\n    implicitWidth: Style.space(760)\n    implicitHeight: Style.space(820)\n    minimumSize: Qt.size(Style.space(520), Style.space(520))\n    onVisibleChanged: if (!visible) root.detached = false\n\n    BbsView {\n      id: detachedView\n      anchors.fill: parent\n      anchors.margins: Style.space(14)\n      bar: root.bar\n      hostWidget: root\n      launcherPath: root.launcherPath\n      detached: true\n      onCloseRequested: root.detached = false\n      onReattachRequested: root.reattach()\n    }\n  }\n\n  Timer {\n    interval: 60000\n    repeat: true\n    running: true\n    triggeredOnStart: true\n    onTriggered: root.refreshStatus()\n  }\n\n  Process {\n    id: statusProcess\n    stdout: StdioCollector {\n      waitForEnd: true\n      onStreamFinished: {\n        try {\n          var result = JSON.parse(String(text || \"{}\"))\n          if (result.ok) {\n            root.unreadCount = Number(result.unread || 0)\n            root.mentionCount = Number(result.alert_mentions === undefined ? (result.mentions || 0) : result.alert_mentions)\n            root.updateAvailable = result.update_available === true\n            root.latestVersion = String(result.latest_version || \"\")\n          }\n        } catch (e) {}\n      }\n    }\n  }\n\n  IpcHandler {\n    target: \"omarchy.bbs\"\n    function state(): string { return JSON.stringify({loaded: !!panelLoader.item, opened: root.opened, detached: root.detached, hasBar: !!root.bar, launcher: root.launcherPath, panel: root.detached ? detachedView.diagnostic() : (panelLoader.item ? panelLoader.item.diagnostic() : null)}) }\n    function open(): void { root.open() }\n    function openThread(threadId: int): void { if (panelLoader.item) panelLoader.item.openToThread(threadId) }\n    function openReply(threadId: int, replyId: int): void { if (panelLoader.item) panelLoader.item.openToReply(threadId, replyId) }\n    function close(): void { root.close() }\n    function show(): void { root.open() }\n    function hide(): void { root.close() }\n    function toggle(): void { root.toggle() }\n    function detach(): void { root.detach() }\n    function reattach(): void { root.reattach() }\n  }\n\n  BarIconButton {\n    id: button\n    anchors.fill: parent\n    bar: root.bar\n    text: \"\\uf086\"\n    tooltipText: root.mentionCount > 0 ? \"Omarchy BBS \u00b7 \" + root.mentionCount + \" mention\" + (root.mentionCount === 1 ? \"\" : \"s\") : (root.unreadCount > 0 ? \"Omarchy BBS \u00b7 new board activity\" : \"Open Omarchy BBS\")\n    active: root.opened || root.detached || root.mentionCount > 0\n    onPressed: function(b) {\n      root.toggle()\n    }\n  }\n\n  Rectangle {\n    visible: root.mentionCount > 0\n    width: Style.space(6)\n    height: width\n    radius: width / 2\n    color: Color.accent\n    anchors.right: parent.right\n    anchors.top: parent.top\n    anchors.rightMargin: Style.space(2)\n    anchors.topMargin: Style.space(2)\n  }\n}\n```\n\n### BbsView.qml\n```qml\nimport QtQuick\nimport QtQuick.Controls as Controls\nimport Quickshell\nimport Quickshell.Io\nimport qs.Commons\nimport qs.Ui\n\nItem {\n  id: root\n\n  signal closeRequested()\n  signal detachRequested()\n  signal reattachRequested()\n\n  property var bar: null\n  property var hostWidget: null\n  property bool detached: false\n  property string launcherPath: \"\"\n  property string screen: \"loading\"\n  property string handle: \"\"\n  property string role: \"member\"\n  property string errorMessage: \"\"\n  property string noticeMessage: \"\"\n  property string pendingAction: \"\"\n  property string pendingInput: \"\"\n  property bool requestTimedOut: false\n  property var queuedRequest: null\n  property var currentThread: ({})\n  property var currentProfile: ({})\n  property var preferences: ({handle: \"\", bio: \"\", mention_notifications: true, reply_notifications: true, new_post_notifications: false, desktop_notifications: true})\n  property var boardCategories: [\"general\", \"projects\", \"help\", \"showcase\", \"meta\"]\n  property string categoryFilter: \"all\"\n  property string composeCategory: \"general\"\n  property int currentPage: 1\n  property int totalPages: 1\n  property int visibleUnreadCount: 0\n  property int replyPage: 1\n  property int replyPages: 1\n  property int selectedPostIndex: 0\n  property int selectedReplyIndex: -1\n  property int selectedMentionIndex: 0\n  property int selectedActivityIndex: 0\n  property int selectedReportIndex: 0\n  property int replyTargetId: 0\n  property int focusReplyId: 0\n  property string replyTargetHandle: \"\"\n  property bool replyComposerOpen: false\n  property string editorKind: \"\"\n  property int editorId: 0\n  property string reportKind: \"\"\n  property int reportId: 0\n  property string returnScreen: \"threads\"\n  property string moderationReturn: \"thread\"\n  property string moderatorCategory: \"general\"\n  readonly property var barIdentity: hostWidget || root\n  readonly property alias focusTarget: keyCatcher\n  readonly property real implicitContentHeight: content.implicitHeight\n  readonly property color foreground: bar ? bar

===== training example task=chunk_component =====
[{"role": "system", "content": "You are an Omarchy plugin expert. You write complete, valid Omarchy (Quattro / omarchy-shell, Quickshell QML) plugins. Manifests use schemaVersion 1, a namespaced id that never uses the reserved omarchy.* namespace, name, version, kinds (bar-widget|panel|overlay|menu|service|bar) with a matching safe relative entryPoints path for every kind, and no symlinks. Return every file in full as '### path' followed by a fenced code block."}, {"role": "user", "content": "Omarchy plugin `io.github.jondkinney.omapop` (service, bar-widget). Manifest:\n```json\n{\n  \"schemaVersion\": 1,\n  \"id\": \"io.github.jondkinney.omapop\",\n  \"name\": \"Omapop\",\n  \"version\": \"0.4.11\",\n  \"author\": \"Jon Kinney\",\n  \"license\": \"MIT\",\n  \"description\": \"Select text with the mouse and a small bar of actions appears beside it: cut, copy, paste, search, open links, reveal paths, and extensions written as YAML snippets, shell scripts or JavaScript. Supports a reviewed subset of the PopClip Extensions Directory (https://www.popclip.app/extensions/).\",\n  \"kinds\": [\n    \"service\",\n    \"bar-widget\"\n  ],\n  \"entryPoints\": {\n    \"service\": \"Service.qml\",\n    \"barWidget\": \"BarWidget.qml\"\n  },\n  \"service\": {\n    \"displayName\": \"Omapop\",\n    \"description\": \"Watches for mouse text selections through a small Hyprland Lua engine, reads the Wayland primary selection, and shows the action bar. The compositor is the only place that sees mouse-button releases and the cursor, so the trigger has to live there.\",\n    \"defaults\": {},\n    \"schema\": []\n  },\n  \"barWidget\": {\n    \"displayName\": \"Omapop\",\n    \"description\": \"Manage extensions and settings; right click to pause or resume the selection bar.\",\n    \"category\": \"Utilities\",\n    \"allowMultiple\": false,\n    \"defaultSection\": \"right\",\n    \"defaults\": {\n      \"searchEngine\": \"google\",\n      \"searchUrl\": \"\",\n      \"dragThreshold\": 6,\n      \"hideDistance\": 220,\n      \"longPress\": false,\n      \"requireTerminalShift\": true,\n      \"maxSelectionKiB\": 256,\n      \"excludedApps\": \"\",\n      \"terminalClasses\": \"Alacritty,kitty,foot,footclient,com.mitchellh.ghostty,Ghostty,org.wezfurlong.wezterm,xterm,konsole,org.kde.konsole,org.gnome.Terminal,gnome-terminal-server,Terminal,st-256color,tilix,wezterm\",\n      \"commandKey\": \"ctrl\",\n      \"shortcut\": \"\",\n      \"showBarIcon\": true,\n      \"position\": \"auto\",\n      \"assumeEditable\": false,\n      \"accessibilityProbe\": true,\n      \"directoryRefresh\": true,\n      \"extensionDownloads\": false\n    },\n    \"schema\": [\n      {\n        \"key\": \"searchEngine\",\n        \"type\": \"enum\",\n        \"label\": \"Search engine\",\n        \"defaultValue\": \"google\",\n        \"options\": [\n          \"google\",\n          \"duckduckgo\",\n          \"bing\",\n          \"brave\",\n          \"kagi\",\n          \"startpage\",\n          \"ecosia\",\n          \"yahoo\",\n          \"yandex\",\n          \"baidu\",\n          \"naver\",\n          \"other\"\n        ],\n        \"description\": \"Used by the built-in Search action. Choose 'other' to use the custom URL below.\"\n      },\n      {\n        \"key\": \"searchUrl\",\n        \"type\": \"string\",\n        \"label\": \"Custom search URL\",\n        \"defaultValue\": \"\",\n        \"description\": \"Used when the engine is 'other'. Put *** where the selected text goes, e.g. https://example.com/search?q=***\"\n      },\n      {\n        \"key\": \"dragThreshold\",\n        \"type\": \"integer\",\n        \"label\": \"Drag threshold (px)\",\n        \"defaultValue\": 6,\n        \"min\": 1,\n        \"max\": 100,\n        \"description\": \"How far the pointer must move between press and release for the gesture to count as a drag selection.\"\n      },\n      {\n        \"key\": \"position\",\n        \"type\": \"enum\",\n        \"label\": \"Bar position\",\n        \"defaultValue\": \"auto\",\n        \"options\": [\n          \"auto\",\n          \"above\",\n          \"below\"\n        ],\n        \"description\": \"Auto puts the bar above the pointer, or below it when the drag went downwards, so it never covers the selection.\"\n      },\n      {\n        \"key\": \"assumeEditable\",\n        \"type\": \"boolean\",\n        \"label\": \"Assume unknown fields are editable\",\n        \"defaultValue\": false,\n        \"description\": \"When neither the accessibility bus nor the window class says whether the selection is in an editable field, treat it as editable anyway. Off by default, so page text in a browser never offers Cut, Paste or text-replacing actions. Browsers report their fields once they are restarted with accessibility on (see the README).\"\n      },\n      {\n        \"key\": \"accessibilityProbe\",\n        \"type\": \"boolean\",\n        \"label\": \"Detect editable fields via accessibility\",\n        \"defaultValue\": true,\n        \"description\": \"Keeps a small AT-SPI helper running and turns on the session accessibility flag. It checks editable fields and text-selection ranges at the gesture's starting point, so selecting the same text can work without a fresh primary-selection event. Browser and Electron apps may need a restart.\"\n      },\n      {\n        \"key\": \"hideDistance\",\n        \"type\": \"integer\",\n        \"label\": \"Hide when pointer moves away (px)\",\n        \"defaultValue\": 220,\n        \"min\": 40,\n        \"max\": 2000,\n        \"description\": \"The bar disappears once the pointer is this far from it.\"\n      },\n      {\n        \"key\": \"longPress\",\n        \"type\": \"boolean\",\n        \"label\": \"Show on long press\",\n        \"defaultValue\": false,\n        \"description\": \"Off by default. Hold the left button for half a second without moving to offer Paste, even without a selection or field detection. No Shift is needed in terminals.\"\n      },\n      {\n        \"key\": \"requireTerminalShift\",\n        \"type\": \"boolean\",\n        \"label\": \"Require Shift in terminals\",\n        \"defaultValue\": true,\n        \"description\": \"Hold Shift while selecting in terminal windows to show Omapop. Prevents stale popups when Herdr, tmux or another terminal app copies and clears its own selection. Applies at plain shell prompts too; long press and the keyboard shortcut still work.\"\n      },\n      {\n        \"key\": \"maxSelectionKiB\",\n        \"type\": \"integer\",\n        \"label\": \"Largest selection read (KiB)\",\n        \"defaultValue\": 256,\n        \"min\": 4,\n        \"max\": 4096,\n        \"description\": \"Selections larger than this are ignored.\"\n      },\n      {\n        \"key\": \"excludedApps\",\n        \"type\": \"string\",\n        \"label\": \"Excluded apps\",\n        \"defaultValue\": \"\",\n        \"description\": \"Comma-separated window classes where the bar never appears (see hyprctl clients).\"\n      },\n      {\n        \"key\": \"terminalClasses\",\n        \"type\": \"string\",\n        \"label\": \"Terminal window classes\",\n        \"defaultValue\": \"Alacritty,kitty,foot,footclient,com.mitchellh.ghostty,Ghostty,org.wezfurlong.wezterm,xterm,konsole,org.kde.konsole,org.gnome.Terminal,gnome-terminal-server,Terminal,st-256color,tilix,wezterm\",\n        \"description\": \"Windows whose paste shortcut is Ctrl+Shift+V and which cannot cut.\"\n      },\n      {\n        \"key\": \"commandKey\",\n        \"type\": \"enum\",\n        \"label\": \"Extensions' 'command' key maps to\",\n        \"defaultValue\": \"ctrl\",\n        \"options\": [\n          \"ctrl\",\n          \"super\"\n        ],\n        \"description\": \"Global default for macOS Command shortcuts. Each installed extension can override this from its gear menu.\"\n      },\n      {\n        \"key\": \"extensionDownloads\",\n        \"type\": \"boolean\",\n        \"label\": \"Allow extension installs\",\n        \"defaultValue\": false,\n        \"description\": \"Allow installing reviewed directory extensions, including bundled Linux ports. Every installation asks for confirmation; new extensions start disabled.\"\n      },\n      {\n        \"key\": \"directoryRefresh\",\n        \"type\": \"boolean\",\n        \"label\": \"Keep the extension catalogue up to date\",\n        \"defaultValue\": true,\n        \"description\": \"Once a week, fetch the published listing for 'Available extensions'. This contacts popclip.app and cannot change Omapop's approved packages or versions. Update also works by hand.\"\n      },\n      {\n        \"key\": \"shortcut\",\n        \"type\": \"string\",\n        \"label\": \"Keyboard shortcut\",\n        \"defaultValue\": \"\",\n        \"description\": \"Optional Hyprland bind that shows the bar for the current selection, e.g. SUPER + SHIFT + P. Leave empty for none.\"\n      },\n      {\n        \"key\": \"showBarIcon\",\n        \"t

===== training example task=chunk_component =====
[{"role": "system", "content": "You are an Omarchy plugin expert. You write complete, valid Omarchy (Quattro / omarchy-shell, Quickshell QML) plugins. Manifests use schemaVersion 1, a namespaced id that never uses the reserved omarchy.* namespace, name, version, kinds (bar-widget|panel|overlay|menu|service|bar) with a matching safe relative entryPoints path for every kind, and no symlinks. Return every file in full as '### path' followed by a fenced code block."}, {"role": "user", "content": "Omarchy plugin `kenhara.encyclopedic` (bar-widget). Manifest:\n```json\n{\n  \"schemaVersion\": 1,\n  \"id\": \"kenhara.encyclopedic\",\n  \"name\": \"Encyclopedic\",\n  \"version\": \"0.1.22\",\n  \"author\": \"Harris Kenny\",\n  \"license\": \"MIT\",\n  \"description\": \"Look it up. Unofficial Grokipedia / xAI encyclopedia client; not affiliated.\",\n  \"kinds\": [\n    \"bar-widget\"\n  ],\n  \"entryPoints\": {\n    \"barWidget\": \"BarWidget.qml\"\n  },\n  \"keywords\": [\n    \"encyclopedic\",\n    \"grokipedia\",\n    \"grok\",\n    \"grok encyclopedia\",\n    \"wikipedia\",\n    \"wiki\",\n    \"encyclopedia\",\n    \"lookup\",\n    \"search\",\n    \"article\",\n    \"citation\",\n    \"heinlein\",\n    \"stranger in a strange land\",\n    \"xai\",\n    \"knowledge base\",\n    \"full text search\",\n    \"unofficial wikipedia\",\n    \"ai encyclopedia\",\n    \"witness\",\n    \"fw\",\n    \"look it up\",\n    \"fair witness\"\n  ],\n  \"barWidget\": {\n    \"displayName\": \"Encyclopedic\",\n    \"description\": \"Look it up. Public Grokipedia full-text search. Unofficial; not affiliated with xAI or Grokipedia.\",\n    \"category\": \"Productivity\",\n    \"allowMultiple\": false,\n    \"defaultSection\": \"right\",\n    \"defaults\": {\n      \"resultLimit\": 8\n    },\n    \"schema\": [\n      {\n        \"key\": \"resultLimit\",\n        \"type\": \"integer\",\n        \"label\": \"Result limit\",\n        \"description\": \"Max search results to request (1\u201320). Default 8.\",\n        \"min\": 1,\n        \"max\": 20,\n        \"step\": 1,\n        \"defaultValue\": 8\n      }\n    ],\n    \"aliases\": [\n      \"encyclopedic\",\n      \"grokipedia\",\n      \"grok\",\n      \"grok encyclopedia\",\n      \"wikipedia\",\n      \"wiki\",\n      \"encyclopedia\",\n      \"lookup\",\n      \"search\",\n      \"heinlein\",\n      \"xai\",\n      \"knowledge base\",\n      \"full text search\",\n      \"fw\",\n      \"look it up\",\n      \"fair witness\"\n    ]\n  }\n}\n```\nSibling files:\n- BarWidget.qml (4 KB)\n- WitnessStore.qml (29 KB)\n- scripts/search.py (27 KB)\n\nImplement `Panel.qml` in full."}, {"role": "assistant", "content": "### Panel.qml\n```qml\nimport QtQuick\nimport Quickshell\nimport qs.Commons\nimport qs.Ui\n\n// Nested details panel for Encyclopedic (loaded by BarWidget \u2014 not a separate kind).\n// KeyboardPanel shell (Compliantish/Rocketlauncher).\n// LOOK UP + MATCH hero + RELATED. No vendor chrome.\nPanel {\n  id: root\n  moduleName: \"kenhara.encyclopedic\"\n  manageIpc: false\n\n  property var anchorItem: null\n  property var hostWidget: null\n  property var store: null\n\n  readonly property var barIdentity: hostWidget || root\n  readonly property color contentForeground: bar ? bar.foreground : Color.foreground\n  readonly property string contentFontFamily: bar ? bar.fontFamily : \"monospace\"\n  readonly property color themeBackground: {\n    try {\n      if (typeof Color !== \"undefined\" && Color.popups && Color.popups.background)\n        return Color.popups.background\n      if (typeof Color !== \"undefined\" && Color.background)\n        return Color.background\n    } catch (e) {}\n    return Qt.rgba(0.1, 0.1, 0.12, 1)\n  }\n  readonly property color surfaceColor: Qt.rgba(\n    contentForeground.r, contentForeground.g, contentForeground.b, 0.06)\n  readonly property color dimForeground: Qt.darker(contentForeground, 1.45)\n  readonly property color fwAccent: Qt.rgba(0.43, 0.78, 0.91, 1.0)\n\n  readonly property var liveStore: store\n\n  // FW-19: focus query when panel opens (skip while a lookup is in flight)\n  onOpenedChanged: {\n    if (root.opened && !(liveStore && liveStore.loading))\n      Qt.callLater(function() { if (queryEdit) queryEdit.forceActiveFocus() })\n  }\n\n  function switchPanel(direction) {\n    if (root.bar && typeof root.bar.switchPanelFrom === \"function\")\n      return root.bar.switchPanelFrom(root.barIdentity, direction)\n    return false\n  }\n\n  readonly property int panelBaseHeight: Style.space(680)\n\n  KeyboardPanel {\n    id: panel\n    anchorItem: root.anchorItem\n    owner: root.barIdentity\n    bar: root.bar\n    open: root.opened\n    focusTarget: keyCatcher\n    contentWidth: panel.fittedContentWidth(Style.space(400))\n    contentHeight: panel.fittedContentHeight(root.panelBaseHeight)\n    popoutSwitching: root.popoutSwitching\n    popoutSwitchClosing: root.popoutSwitchClosing\n\n    PanelKeyCatcher {\n      id: keyCatcher\n      anchors.fill: parent\n\n      onCloseRequested: root.close()\n      onTabRequested: function(direction) { root.switchPanel(direction) }\n\n      Flickable {\n        id: flick\n        anchors.fill: parent\n        anchors.margins: Style.space(16)\n        contentWidth: width\n        contentHeight: contentCol.implicitHeight\n        clip: true\n        boundsBehavior: Flickable.StopAtBounds\n\n        Column {\n          id: contentCol\n          width: flick.width\n          spacing: Style.space(14)\n          opacity: liveStore && liveStore.loading ? 0.72 : 1.0\n\n          Behavior on opacity {\n            NumberAnimation { duration: 160; easing.type: Easing.OutCubic }\n          }\n\n          // Header\n          Column {\n            width: parent.width\n            spacing: Style.space(6)\n\n            Row {\n              spacing: Style.space(8)\n              Text {\n                text: \"\\uf002\"\n                color: root.fwAccent\n                font.family: root.contentFontFamily\n                font.pixelSize: Style.font.body\n                anchors.verticalCenter: parent.verticalCenter\n              }\n              Text {\n                text: \"ENCYCLOPEDIC\"\n                color: root.fwAccent\n                font.family: root.contentFontFamily\n                font.pixelSize: Style.font.body\n                font.bold: true\n                font.letterSpacing: 3.2\n                anchors.verticalCenter: parent.verticalCenter\n              }\n            }\n\n            Text {\n              text: \"look it up\"\n              color: root.contentForeground\n              opacity: 0.5\n              font.family: root.contentFontFamily\n              font.pixelSize: Style.font.body\n              width: parent.width\n            }\n\n            Text {\n              visible: !!(liveStore && liveStore.lookedUpAt && String(liveStore.lookedUpAt).length)\n              text: liveStore ? (\"looked up \" + liveStore.lastUpdatedText) : \"\"\n              textFormat: Text.PlainText\n              color: root.contentForeground\n              opacity: 0.35\n              font.family: root.contentFontFamily\n              font.pixelSize: Style.font.caption\n              width: parent.width\n            }\n          }\n\n          // One search / paste field\n          Column {\n            width: parent.width\n            spacing: Style.space(6)\n\n            Rectangle {\n              width: parent.width\n              height: Math.max(Style.space(52), queryEdit.implicitHeight + Style.space(20))\n              radius: 10\n              color: root.surfaceColor\n              border.width: 1\n              border.color: Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.14)\n\n              TextEdit {\n                id: queryEdit\n                anchors.left: parent.left\n                anchors.right: parent.right\n                anchors.top: parent.top\n                anchors.margins: Style.space(10)\n                color: root.contentForeground\n                font.family: root.contentFontFamily\n                font.pixelSize: Style.font.body\n                wrapMode: TextEdit.Wrap\n                selectByMouse: true\n                text: liveStore ? liveStore.queryInput : \"\"\n                onTextChanged: if (liveStore) liveStore.queryInput = text\n                Keys.onReturnPressed: function(event) {\n                  if (event.modifiers & Qt.ShiftModifier) {\n                    event.accepted = false\n                    return\n                  }\n                  event.accepted = true\n                  if (liveStore) liveStore.lookUp()\n                }\n\n                Text {\n                  anchors.fill: parent\n                  visible: !queryEdit.text.length\n                  text: \"search or paste a topic\u2026\"\n                  color: root.contentForeground\n                  opacity: 0.32\n                  font.famil

===== score table =====
{
"stock_7b": {
"new_overall": "3/49",
"new_full_plugin": "0/32",
"per_task": {
"build_from_spec": "0/26",
"add_panel": "0/6",
"chunk_manifest_entry": "0/3",
"chunk_component": "1/6",
"chunk_add_kind": "2/3",
"fix_manifest": "0/5"
},
"truncated": 0,
"looping": 0,
"median_chars": 1731,
"failure_categories": {
"rt-other": 23,
"rt-load-failed": 17,
"rt-not-instantiated": 12,
"no-files-parsed": 10,
"placeholder-ui": 8,
"entry-not-qml": 5,
"fake-api": 5,
"no-qml": 5,
"rt-qml-syntax": 5,
"not-shell-surface": 4,
"rt-unresolved-type/import": 3,
"fake-data": 2,
"qt5-api": 2,
"bad-import": 2,
"rt-bad-property": 2,
"rt-zero-size": 1,
"dangerous-write": 1,
"rt-manifest-rejected": 1,
"rt-js-error": 1
}
},
"gpt-5.6-sol": {
"new_overall": "24/49",
"new_full_plugin": "15/32",
"per_task": {
"build_from_spec": "9/26",
"add_panel": "6/6",
"chunk_manifest_entry": "2/3",
"chunk_component": "2/6",
"chunk_add_kind": "2/3",
"fix_manifest": "3/5"
},
"truncated": 0,
"looping": 0,
"median_chars": 20465,
"failure_categories": {
"rt-other": 19,
"rt-load-failed": 15,
"rt-js-error": 3,
"rt-bad-property": 2,
"dangerous-write": 1,
"rt-dangerous-write": 1,
"no-files-parsed": 1,
"rt-not-instantiated": 1
}
},
"claude-opus-5.5": {
"new_overall": "23/49",
"new_full_plugin": "14/32",
"per_task": {
"build_from_spec": "9/26",
"add_panel": "5/6",
"chunk_manifest_entry": "2/3",
"chunk_component": "0/6",
"chunk_add_kind": "2/3",
"fix_manifest": "5/5"
},
"truncated": 4,
"looping": 0,
"median_chars": 14274,
"failure_categories": {
"rt-load-failed": 15,
"rt-other": 13,
"no-files-parsed": 7,
"rt-bad-property": 4,
"rt-js-error": 2,
"no-qml": 1,
"dangerous-write": 1,
"rt-not-instantiated": 1
}
},
"stock_7b_rp1.0": {
"new_overall": "4/49",
"new_full_plugin": "1/32",
"per_task": {
"build_from_spec": "1/26",
"add_panel": "0/6",
"chunk_manifest_entry": "0/3",
"chunk_component": "1/6",
"chunk_add_kind": "2/3",
"fix_manifest": "0/5"
},
"truncated": 4,
"looping": 2,
"median_chars": 1940,
"failure_categories": {
"rt-other": 25,
"rt-load-failed": 19,
"rt-not-instantiated": 12,
"fake-api": 9,
"entry-not-qml": 6,
"rt-qml-syntax": 6,
"placeholder-ui": 6,
"no-qml": 5,
"no-files-parsed": 5,
"rt-unresolved-type/import": 4,
"bad-import": 3,
"not-shell-surface": 3,
"qt5-api": 2,
"rt-manifest-rejected": 2,
"rt-bad-property": 2,
"fake-data": 1,
"rt-zero-size": 1,
"rt-js-error": 1
}
},
"clean_b": {
"new_overall": "10/49",
"new_full_plugin": "1/32",
"per_task": {
"build_from_spec": "1/26",
"add_panel": "0/6",
"chunk_manifest_entry": "0/3",
"chunk_component": "1/6",
"chunk_add_kind": "3/3",
"fix_manifest": "5/5"
},
"truncated": 40,
"looping": 10,
"median_chars": 60810,
"failure_categories": {
"no-qml": 26,
"rt-load-failed": 24,
"rt-other": 22,
"rt-not-instantiated": 13,
"no-files-parsed": 8,
"rt-qml-syntax": 2,
"rt-bad-property": 1
}
},
"stock14b": {
"new_overall": "6/49",
"new_full_plugin": "1/32",
"per_task": {
"build_from_spec": "0/26",
"add_panel": "1/6",
"chunk_manifest_entry": "0/3",
"chunk_component": "1/6",
"chunk_add_kind": "2/3",
"fix_manifest": "2/5"
},
"truncated": 1,
"looping": 0,
"median_chars": 1916,
"failure_categories": {
"rt-other": 34,
"rt-manifest-rejected": 29,
"bad-import": 27,
"fake-api": 24,
"rt-load-failed": 9,
"rt-unresolved-type/import": 7,
"placeholder-ui": 5,
"fake-data": 4,
"qt5-api": 2,
"rt-bad-property": 2,
"no-qml": 2,
"rt-js-error": 2,
"rt-not-instantiated": 1,
"rt-qml-syntax": 1,
"rt-zero-size": 1
}
}
}

===== clean_b finish reasons =====
Counter({'length': 40, 'stop': 9})

===== failing output task=build_from_spec finish=length chars=80411 loop=True =====
### manifest.json
```json
{
  "schemaVersion": 1,
  "id": "acme.background",
  "name": "Background",
  "version": "0.1.0",
  "author": "Acme",
  "license": "MIT",
  "description": "Desktop background renderer with click handling and transitions.",
  "kinds": [
    "service"
  ],
  "entryPoints": {
    "service": "Service.qml"
  }
}
```

### Service.qml
```qml
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import qs.Ui

// Background service: renders the desktop wallpaper, handles clicks, and
// animates transitions between images.
//
// The wallpaper is drawn into a full-screen Wayland layer surface, which sits
// behind the compositor's own layer shell surfaces. This keeps the wallpaper
// visible through fullscreen windows and above the lock screen, and it avoids
// the flicker of a transient full-screen window.
Item {
  id: root

  property string home: Quickshell.env("HOME")
  property string configHome: Quickshell.env("XDG_CONFIG_HOME", home + "/.config")

  // Wallpaper directory, resolved from the environment or ~/.config/background.
  property string wallpaperDir: {
    var dir = Quickshell.env("OMARCHY_BACKGROUND_DIR")
    if (dir) return dir
    dir = configHome + "/background"
    try {
      var stat = Quickshell.stat(dir)
      if (stat && stat.isDir) return dir
    } catch (e) {}
    return configHome + "/background"
  }

  // Wallpaper image, resolved from the environment or ~/.config/background/current.
  property string wallpaperPath: {
    var path = Quickshell.env("OMARCHY_BACKGROUND_IMAGE")
    if (path) return path
    path = configHome + "/background/current"
    try {
      var stat = Quickshell.stat(path)
      if (stat && stat.isFile) return path
    } catch (e) {}
    return ""
  }

  // Wallpaper image to transition to, set by the client before the next frame.
  property string nextWallpaperPath: ""

  // Wallpaper image being displayed, updated on the next frame after a
  // transition completes.
  property string currentWallpaperPath: wallpaperPath

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition
...[middle cut]...
en a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath: ""

  // Wallpaper image that was being displayed before the last transition
  // started, so the client can tell when a transition has finished.
  property string previousWallpaperPath

===== failing output task=build_from_spec finish=length chars=71546 loop=True =====
### manifest.json
```json
{
  "schemaVersion": 1,
  "id": "acme.background",
  "name": "Background",
  "version": "0.1.0",
  "author": "Omarchy",
  "license": "MIT",
  "description": "Desktop background renderer with click handling and transitions.",
  "kinds": [
    "service"
  ],
  "entryPoints": {
    "service": "Service.qml"
  }
}
```

### Service.qml
```qml
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import qs.Ui

// Background service: renders the desktop wallpaper, handles clicks, and
// animates transitions between images.
//
// The wallpaper is drawn into a full-screen Wayland layer surface, which sits
// above the compositor's root layer but below the shell's own layer surfaces
// (so it does not obscure the bar or popups). The layer is sized to the
// compositor's output size, so it covers the whole screen regardless of the
// monitor layout.
//
// Clicks are handled by the compositor's own click handler, which sends a
// wl_shell_surface.activate event to the focused app window when the pointer
// is over the background. This is the same mechanism the shell uses for the
// bar, so clicking on the background activates whatever window has focus.
Item {
  id: root

  property var shell: null
  property var manifest: null

  // Wallpaper directory. Falls back to the user's home directory if none is
  // configured.
  readonly property string wallpaperDir: {
    const value = String(setting("wallpaperDir", ""))
    return value.length > 0 ? value : Quickshell.env("HOME")
  }

  // Wallpaper image. Falls back to the default image shipped with the plugin.
  readonly property string wallpaperPath: {
    const value = String(setting("wallpaper", ""))
    if (value.length > 0) return value
    const url = Qt.resolvedUrl("assets/default.jpg")
    return url.toString().replace(/^file:\/\//, "")
  }

  // Transition duration in milliseconds. Defaults to 500ms.
  readonly property int transitionDuration: Math.max(100, Number(setting("transitionDuration", 500)))

  // Whether the transition should be animated. Defaults to true.
  readonly property bool animateTransitions: setting("animateTransitions", true) !== false

  // Wallpaper images currently being displayed and queued for display. The
  // first item is the one currently visible; the second is the next one, which
  // is faded in during the transition. The third item is the one after that,
  // which is loaded in advance so the transition can start immediately.
  property var images: []

  // The index of the image currently being displayed. -1 means there is no
  // image yet (the first load is still in progress).
  property int currentImageIndex: -1

  // The index of the image that is fading in. -1 means the transition is not
  // running.
  property int nextImageIndex: -1

  // The opacity of the next image, from 0 (completely transparent) to 1
  // (completely opaque). Only used while the transition is running.
  property real nextImageOpacity: 0

  // The time at which the transition started, in seconds since the epoch.
  property double transitionStartedAt: 0

  // The time at which the next image was loaded, in seconds since the epoch.
  property double nextImageLoadedAt: 0

  // The time at which the next image was requested, in seconds since the epoch.
  property double nextImageRequestedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload de
...[middle cut]...
t which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload delay.
  property double previousImageUnloadRequestedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload delay.
  property double previousImageUnloadCompletedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload delay.
  property double previousImageUnloadRequestedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload delay.
  property double previousImageUnloadCompletedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload delay.
  property double previousImageUnloadRequestedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload delay.
  property double previousImageUnloadCompletedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload delay.
  property double previousImageUnloadRequestedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload delay.
  property double previousImageUnloadCompletedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload delay.
  property double previousImageUnloadRequestedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload delay.
  property double previousImageUnloadCompletedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload delay.
  property double previousImageUnloadRequestedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload delay.
  property double previousImageUnloadCompletedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload delay.
  property double previousImageUnloadRequestedAt: 0

  // The time at which the previous image was unloaded, in seconds since the
  // epoch. Used to enforce the minimum unload

===== failing output task=build_from_spec finish=length chars=58913 loop=False =====
### manifest.json
```json
{
  "schemaVersion": 1,
  "id": "acme.clipboard",
  "name": "Clipboard",
  "version": "0.1.0",
  "author": "Omarchy",
  "license": "MIT",
  "description": "A clipboard manager to view and paste history.",
  "kinds": [
    "overlay"
  ],
  "keepLoaded": true,
  "entryPoints": {
    "overlay": "Overlay.qml"
  }
}
```

### Overlay.qml
```qml
import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

// The clipboard overlay: a list of recent items, pasted from the system
// clipboard, and a text field to type into.
//
// The list is read from ~/.local/state/omarchy/clipboard.json, which the
// shell writes on every paste. It is kept in memory only; there is no IPC
// between this overlay and the shell itself.
Item {
  id: root

  property var shell: null
  property var manifest: null
  property bool opened: false
  property string anchorEdge: "top"
  property string anchorAlign: "center"
  property int anchorMargin: Style.space(12)
  property int contentWidth: 560
  property int contentHeight: 480
  property int maxItems: 100
  property int maxText: 1024 * 1024
  property string filterText: ""
  property int selectedIndex: -1
  property bool insertMode: false
  property bool insertActive: false
  property bool insertSaved: false
  property string insertSavedText: ""
  property string insertSavedSelection: ""
  property string insertSavedCursor: ""
  property string insertSavedAnchor: ""
  property string insertSavedFocus: ""
  property string insertSavedSelectionStart: ""
  property string insertSavedSelectionEnd: ""
  property string insertSavedSelectionDirection: ""
  property string insertSavedSelectionGranularity: ""
  property string insertSavedSelectionUnit: ""
  property string insertSavedSelectionType: ""
  property string insertSavedSelectionState: ""
  property string insertSavedSelectionRect: ""
  property string insertSavedSelectionRectX: ""
  property string insertSavedSelectionRectY: ""
  property string insertSavedSelectionRectWidth: ""
  property string insertSavedSelectionRectHeight: ""
  property string insertSavedSelectionRectTop: ""
  property string insertSavedSelectionRectLeft: ""
  property string insertSavedSelectionRectRight: ""
  property string insertSavedSelectionRectBottom: ""
  property string insertSavedSelectionRectCenterX: ""
  property string insertSavedSelectionRectCenterY: ""
  property string insertSavedSelectionRectCenter: ""
  property string insertSavedSelectionRectSize: ""
  property string insertSavedSelectionRectArea: ""
  property string insertSavedSelectionRectAspectRatio: ""
  property string insertSavedSelectionRectRatio: ""
  property string insertSavedSelectionRectRatioString: ""
  property string insertSavedSelectionRectRatioStringNormalized: ""
  property string insertSavedSelectionRectRatioStringNormalizedWithUnit: ""
  property string insertSavedSelectionRectRatioStringNormalizedWithUnitAndUnit: ""
  property string insertSavedSelectionRectRatioStringNormalizedWithUnitAndUnitAndUnit: ""
  property string insertSavedSelectionRectRatioStringNormalizedWithUnitAndUnitAndUnitAndUnit: ""
  property string insertSavedSelectionRectRatioStringNormalizedWithUnitAndUnitAndUnitAndUnitAndUnit: ""
  property string insertSavedSelectionRectRatioStringNormalizedWithUnitAndUnitAndUnitAndUnitAndUnitAndUnit: ""
  property string insertSavedSelectionRectRatioStringNormalizedWithUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnit: ""
  property string insertSav
...[middle cut]...
dUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAndUnitAnd