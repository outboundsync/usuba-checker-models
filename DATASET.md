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
- The real CLI is bash + `jq` + `find`, so it **runs unmodified on this Debian box** (`validator/omarchy-plugin-validate`). Every example was checked through [`validator/validate.py`](https://github.com/outboundsync/usuba-checker-scripts/blob/main/validator/validate.py), a line-by-line Python port that can also validate in-memory files.
- [`validator/diff_test.sh`](https://github.com/outboundsync/usuba-checker-scripts/blob/main/validator/diff_test.sh) runs the real script and the port side by side on 25 cases: every rule, the edge cases above, and a symlink. Result: **25/25 identical output and exit code.** A separate run on all 31 first-party manifests also matched (all rejected on the reserved `omarchy.*` id, as expected).
- **Gaps (not covered by `omarchy plugin validate`):**
  - Marketplace-only rules: allowed `barWidget.category` values (Fun/Info/Lifestyle get rejected at listing, but the CLI passes them), filing tags, preview image, and the HANCORE security baseline.
  - Runtime QML load behavior: whether `qs.*` / Quickshell imports resolve, KeyboardPanel nesting, etc. You can only see that on a real Omarchy box.
  - PluginRegistry also skips plugins whose id collides with a first-party id. The CLI only checks the `omarchy.` prefix.
- **qmllint**: Debian has no `qt6-declarative-dev-tools` package. I installed PySide6-Essentials in `.venv` (Qt 6 `pyside6-qmllint`) instead. [`validator/qmllint_check.py`](https://github.com/outboundsync/usuba-checker-scripts/blob/main/validator/qmllint_check.py) runs `qmllint --bare --disable-plugins all` and counts only **`[syntax]`** findings, because the Quickshell/`qs.*` modules aren't installed and import/type warnings are expected. The default qmllint plugins hang on real Quickshell files; disabling them fixes the hang. Result (v2.1): **290 QML files across 254 examples, 0 syntax errors.** The build also lints every example and drops any with a syntax error. None were dropped.

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
python3 gen_docs.py           # NOTICE, sources/SOURCES.md, legacy/data/STATS.md
validator/diff_test.sh        # bash vs python validator parity (25/25)
python3 validator/qmllint_check.py data/train.jsonl data/holdout.jsonl
```
Needs `/tmp/omarchy-src` checked out at the snapshot SHA. v1 builder kept as `build_dataset_v1.py`.

## Next step
Run a smoke-test QLoRA on Qwen2.5-Coder-7B-Instruct with the train split, using a rented GPU later and only after approval. Compare it against the **base model + the Quattro plugin skill in context** on the 56 holdout prompts, broken down by kind and task.
- Primary metric: **validator pass rate** (chunk/fix answers are inserted into the real tree).
- Secondary metric: **qmllint syntax-clean rate**.
- Also track the reserved-id rate and kind↔entryPoint consistency.
