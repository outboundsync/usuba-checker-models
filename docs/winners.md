# Omarchy competition winners: profile, Checker run, learnings

Date: 2026-10-15. Plugins (as given by Harris; I could not verify the "winner" status from the marketplace, whose plugin pages are JS-rendered and returned empty detail fields): `akshar.radio-atlas`, `slcode777.omagotchi`, `io.github.thisisgm.omapods`, `robzolkos.github`.
Cost: $0 (no LLM, no GPU, no Dell, no network beyond two page fetches that returned empty JS shells). Seeds: none, everything is deterministic.

## 1. Sources (all four were already on the box; nothing cloned)
| plugin id | repo | local dir | commit at HEAD (corpus.jsonl) | version | catalog |
|---|---|---|---|---|---|
| akshar.radio-atlas | AksharP5/omarchy-radio-atlas | sweep_repos/aksharp5__omarchy-radio-atlas | 1277cd97 (2026-10-12) | 0.1.9 | github-search |
| slcode777.omagotchi | SLcode777/omagotchi | sweep_repos/slcode777__omagotchi (no .git; tree at 669ea0b7) | 669ea0b7 | 0.1.0 | marketplace-full: Available, unverified, compat passed, 20 stars |
| io.github.thisisgm.omapods | thisisgm/omarchy-pods | sweep_repos/thisisgm__omarchy-pods | fff7fec6 (2026-08-26) | 1.3.6 | marketplace |
| robzolkos.github | robzolkos/omarchy-github | sweep_repos/robzolkos__omarchy-github | 6f361a45 (2026-09-16) | 0.3.0 | github-search |
`/workspace/ref/winners/` was therefore not created. Same-name look-alikes exist in the corpus and must not be confused: vdsabev/omagotchi, higgsfield-ai/omagotchi, mb-jambon/omarchy-pods (id io.github.mb-jambon.omapods), dakota-dits/omarchy-better-omapods.

## 2. Profile
| | radio-atlas | omagotchi | omapods | github |
|---|---|---|---|---|
| kinds / entry points | panel + bar-widget; RadioAtlas.qml, BarWidget.qml; keepLoaded | service + bar-widget; Service.qml, BarWidget.qml (+Panel, RoamWindow, PetSprite) | bar-widget; Panel.qml (+Service.qml) | bar-widget; Panel.qml (+Service, UrlLauncher); activation on-demand |
| production LOC | 7,068 (qml 3,659, shell/py scripts ~2,540, js 633, lua 236) | 2,752 (qml 2,732) | 11,239 (daemon C++ 5,270 + hpp/h 2,904 vendored; qml 2,330) | 2,887 (qml 2,209, bash helper 678) |
| tests (LOC) | 7,243 (py, mjs, qml, shell fixtures with fake mpv/curl/pactl) + CI | none | 3,063 (C++ ctest, js) ; no CI | 1,547 (bash + QML stubs of Quickshell) + CI |
| manifest | schemaVersion, id, version, author, MIT, repository, homepage, keywords; no schema/defaults | no repository/homepage/keywords; no schema | schema (2 keys) + defaults | schema (16 keys, min/max/step) + defaults, aliases |
| Quickshell API | Process/StdioCollector/FileView/Timer, Mpris, Hyprland, qs.Commons+qs.Ui; hyprctl eval (Lua window rule) | Process, FileView, Timer x21, Hyprland module (window positions via IPC socket), execDetached | Process, FileView, IpcHandler, Loader, Timer | Process, StdioCollector, Loader x3, IpcHandler, execDetached |
| helper binaries | radio-fetch, radio-player, radio-mpris (python+GLib), radio-proxy, radio-session, radio-state, radio-window, radio-favicon (all executable, `set -euo pipefail`, flock, mktemp, trap) | tools/gen-sprites.sh (dev only) | `setup` script builds daemon into ~/.local, enables systemd user unit; librepods-ctl | omarchy-github-fetch (bash, gh CLI auth, jq, mktemp+trap) |
| config handling | none declared; state in runtime dir | own settings/state JSON in FileView, atomicWrites, reads capped to 64 KiB (`head -c 65536`) | manifest schema; ctlPath path setting; reads $XDG_STATE_HOME/librepods/status.json | 16 typed settings with bounds |
| error handling | exit codes 2/4, health messages, 15 onExited handlers, curl `--max-time --max-filesize --proto =https` | onExited/exitCode checked, fall back to defaults on unreadable state | daemon-down panel state; hides when disconnected | `emit_state error`, structured JSON state, refresh serialization, URL allowlist (https only, added after a security PR) |
| docs | README (features/install/remove/controls/privacy/troubleshooting/dev), assets/NOTICE.md, screenshots | README with Needs, Dependencies, "What it executes, exactly", Remove; ROADMAP, CREDITS | README (requirements, how it works, remove, tests, licence split), CONTRIBUTING, AGENTS.md, knowledge/ notes, UPSTREAM.md | README (requirements, settings, how it works, local dev) |
| license | MIT (root LICENSE; map data public domain, NOTICE.md) | MIT code+sprites; sounds CC BY 4.0 etc. per file in CREDITS.md | MIT root; daemon/ GPL-3.0 (modified librepods, daemon/LICENSE) | MIT |
| changelog | none (version in manifest) | none | none | none |
| size on disk | 3.4 MB (screenshots) | 3.9 MB (png/wav) | 5.0 MB | 0.4 MB |

HANCORE outcomes (checker-rules/pool.json + findings.json; marketplace reviews are open and cleared for use):
- slcode777/omagotchi: reviewed at 9c15d705, label `broken`, three strong findings from marketplace issue 1651 (unbounded-input-resource, file-safety-symlink-perms, process-lifecycle-timeouts), all on Service.qml:537 (watched FileView materializing the complete user-writable settings/state files). At HEAD the author changed this: `watchChanges:false`, `preload:false`, and reads go through `head -c 65536` with a size check (Service.qml:728/750), documented in README. So the review was acted on.
- thisisgm/omarchy-pods: reviewed at 6f21ddb, label `broken`, categories file-safety-symlink-perms + other, no strong finding.
- aksharp5/omarchy-radio-atlas: reviewed at 4e88a70, label `works`, categories privileged-system and unbounded-input-resource (not strong).
- robzolkos/omarchy-github: not HANCORE-reviewed in our data (label `works`, `reviewed:false`); its own PRs (13, 20, 22, 23) carry bot (Codex) and maintainer review comments, already in data/reviews/reviews.jsonl.

## 3. Winners vs the corpus (5,522 plugins from dell/sweep/corpus.jsonl with a local dir; `profile.py corpus`)
| metric | corpus pct (n=5522) | akshar.radio-atlas | slcode777.omagotchi | io.github.thisisgm.omapods | robzolkos.github |
|---|---|---|---|---|---|
| has_license | 98.8 | Y | Y | Y | Y |
| has_readme | 99.3 | Y | Y | Y | Y |
| has_tests | 48.9 | Y | n | Y | Y |
| has_ci | 19.3 | Y | n | n | Y |
| has_changelog | 16.6 | n | n | n | n |
| has_agent_files | 6.5 | n | n | Y | n |
| has_docs_dir | 24.5 | Y | Y | Y | n |
| manifest.license | 83.0 | Y | Y | Y | Y |
| manifest.repository/homepage | 14.5 | Y | n | n | n |
| manifest.keywords | 3.4 | Y | n | n | n |
| barWidget.schema | 39.8 | n | n | Y | Y |
| barWidget.defaults | 40.2 | n | n | Y | Y |
| uses onExited/exitCode | 76.6 | Y | Y | Y | Y |
| timeouts present | 64.6 | Y | n | Y | Y |
| try/catch | 82.5 | Y | Y | Y | Y |
| set -e/pipefail | 49.9 | Y | Y | Y | Y |
| command -v dep probe | 71.9 | Y | Y | Y | Y |
| mktemp | 28.1 | Y | n | n | Y |
| StdioCollector | 73.0 | Y | Y | Y | Y |
| FileView | 41.7 | Y | Y | Y | n |
| Timer | 88.3 | Y | Y | Y | Y |
| IpcHandler | 54.3 | n | n | Y | Y |

| size metric | corpus median | corpus p90 | akshar.radio-atlas | slcode777.omagotchi | io.github.thisisgm.omapods | robzolkos.github |
|---|---|---|---|---|---|---|
| prod LOC | 1755.5 | 6088.2 | 7068 | 2752 | 11239 | 2887 |
| test LOC | 0.0 | 1557.8 | 7243 | 0 | 3063 | 1547 |
| files | 14.0 | 57.0 | 77 | 154 | 122 | 32 |
| bytes | 346096.5 | 3380219.6 | 3408331 | 3897160 | 5001300 | 409426 |

winner prod-LOC percentile: akshar.radio-atlas=92%, slcode777.omagotchi=69%, io.github.thisisgm.omapods=96%, robzolkos.github=71%
winner test-LOC percentile: akshar.radio-atlas=99%, slcode777.omagotchi=50%, io.github.thisisgm.omapods=95%, robzolkos.github=90%
corpus with license+readme+tests+CI: 16.7%

What they share (all four, or 3 of 4):
1. License file + manifest license + README: near-universal in the corpus (99%), so not a discriminator. Documented execution surface (README says exactly what runs, deps, how to remove) is the real shared trait; 72% of the corpus probes deps with `command -v` or similar, and all four do.
2. Process hygiene: every Process has exit handling (onExited/exitCode), shell helpers use `set -euo pipefail`; mktemp+trap or flock where they write temp files; timeouts and byte caps on network calls (radio-atlas, github, pods).
3. Bounded reads of untrusted/user-writable input (omagotchi 64 KiB cap, radio-atlas curl --max-filesize, github https-only URL allowlist).
4. Tests: 3 of 4 ship tests (corpus 49%), 2 of 4 CI (corpus 19%); only 16.7% of the corpus has license+readme+tests+CI. radio-atlas test LOC is in the 99th percentile; github stubs Quickshell in QML tests.
5. Size is mid to large (prod LOC percentiles 69 to 96), so they are more than weekend widgets, but omagotchi and github are only ~2.8k LOC.
6. They do NOT share: changelog (none), schema/defaults (2 of 4), a repository field in the manifest (1 of 4, corpus 14%). A Checker must not treat those as quality signals.
7. Two ship agent-control or knowledge files (omapods: AGENTS.md, .claude/advloop-rules.md), which our USB-H16 flags; that is a known HANCORE finding family, and it does not make a plugin broken.

Good practice the Checker should reward or at least never penalize: size-capped reads of state files; atomic writes; explicit timeouts and byte caps on curl; https-only URL allowlists before xdg-open; dependency probing with a visible "missing dependency" state; fixed argv arrays instead of interpolated shell strings; README section stating what is executed; separate license note for vendored code; honest unverified/optional features (omapods "Deliberately absent").

## 4. Checker run (branch checker-rules-v2 @ 57018c8, extracted with `git archive`; no GPU/LLM; script run_checker.py, raw output checker_results.json)
Hard checks `usuba.checks.check` (USB-Q/A/B/F/J/S rules + W): **0 findings on all four** (all pass).
Legacy `static_checks.check`: 6 findings, all warnings or false positives (below). HANCORE rules (`hancore_rules_v2.check`, enabled_v3 set; the second number adds experimental rules): radio-atlas 4/8, omagotchi 0/0, omapods 3/6, github 0/1.

False-positive review (I read the code at each cited line):
| finding | verdict | why |
|---|---|---|
| static_checks bad-import "unknown module linux" x5 (omapods daemon/*.qml) | FALSE POSITIVE | `import linux 1.0` is a C++-registered module of the vendored librepods daemon (separate Qt app under daemon/), not a shell entry point; usuba.checks (manifest-scoped) correctly ignores it. Checker should only scan files reachable from manifest entryPoints. |
| static_checks footgun "Style.font.heading/display is VPS-unsafe" (radio-atlas, github) | NOISE | warn only; `heading` and `display` are real members in types.json and appear in 630 QML lines across registry_repos. Rule is stale; drop it or tie it to evidence. |
| USB-H01 radio-player:575 curl no byte cap | FALSE POSITIVE | response goes to /dev/null (click-count ping); a cap is meaningless. Rule should skip `>/dev/null`. Other curls in the plugin use --max-filesize. |
| USB-H24 radio-window:38 "shell eval of variable-expanded string" | FALSE POSITIVE | it is `hyprctl eval` (Lua) not a shell eval, and $width/$height were validated by `^[0-9]+$` at lines 4-9. Model-proposed rule should exclude `hyprctl eval` and honor a preceding regex guard. |
| USB-H06 (experimental) radio-fetch:362,369 and github omarchy-github-fetch:370 `rm -rf "$var"` | FALSE POSITIVE | variables come from `mktemp -d` (github also has `trap ... EXIT`). Rule should skip variables assigned from mktemp in the same script. |
| USB-H18 (dropped) radio-favicon:94,100 curl no timeout | FALSE POSITIVE | run_curl passes `--max-time` and `--max-filesize` (line 76); the curl is in a helper, call sites look bare. |
| USB-H02 radio-mpris:35 readline() | FALSE POSITIVE | reads a local one-line generation counter file, then validated `isdecimal`. |
| USB-H02 radio-mpris:67 recv loop | WEAK / plausible | mpv IPC unix socket from a child the plugin spawned; chunk 64 KiB, buffer unbounded in principle. Low risk, a reasonable low-severity note. |
| USB-H02 omapods hearing-aid-adjustments.py:127 | NOT A PLUGIN DEFECT | recv(512) on an L2CAP socket in the vendored upstream tool, and the flagged "loop" is in vendored code. Should be skipped under paths declared as upstream. |
| USB-H16 omapods AGENTS.md, .claude/advloop-rules.md | TRUE POSITIVE (policy) | files are shipped; low severity. |
| USB-H13 (experimental) omapods daemon/Main.qml x3 | out of scope | daemon app, not shell surface. |
Of the 15 HANCORE-rule hits (experimental included): 3 are true or plausible (H16 x2, mpris recv), 8 are false positives (H01, H24, H06 x3, H18 x2, H02 readline), 4 are vendored/out-of-scope (omapods H02, H13 x3). Rule-tuning learning: add skip conditions for `>/dev/null`, mktemp-assigned vars, regex-guarded vars, `hyprctl eval`, helper-wrapped curl, and vendored paths (UPSTREAM.md / vendor dirs / non-entry subtrees).

## 5. Sealed-set overlap (ids only; script overlap.py, output overlap.txt)
- Dell key (functest/dell_ground_truth.jsonl, only the `id` field read, 116 ids): no exact match for any of the four, and no id from the same authors (the other thisisgm plugins adguard/slack/discord/cliampui are in the corpus with a dell_name but not in this key file).
- eval/hancore_holdout (329 plugins by repo in manifest.jsonl, plugin_ids.txt): none of the four repos is in it.
- BUT: all four are in the checker-rules v2/v3 design pool (checker-rules/pool.json, split `design`, so rule tuning has already seen them: omagotchi broken with strong labels, omapods broken, radio-atlas works, github works/unreviewed). They are therefore not a clean test set for the rules; use them as fixtures/illustrations only, or treat any new rule tuned on them as design-split.
- Training use so far: data/source_usage.json lists akshar.radio-atlas and robzolkos.github as `skip: too large for 32k ctx`, so no build-from-spec rows came from them; omagotchi and omapods are not in source_usage. data/reviews/reviews.jsonl already holds ~dozen review-comment rows from robzolkos/omarchy-github PRs 13/20/22/23 (maintainer + Codex bot) and one omagotchi mention (omacom/omarchy issue 11796). `slcode777.omaconv` in train.jsonl is a different plugin by the same author.

## 6. How to use these (prompt, rules, training), with license limits
Prompt: add a short "good practice" block to the Checker/reviewer prompt: judge a plugin by what is exercised (exit handling, caps, timeouts, https allowlist), do not penalize missing changelog/schema/repository field, treat vendored subtrees (UPSTREAM.md, daemon/) as out of scope, require file:line from the entry-point-reachable tree, and when a heuristic fires on `>/dev/null`, mktemp vars or guarded vars say it is not a bug. Use omagotchi's README "What it executes, exactly" as the model of a dependency/exec inventory the Checker can cross-check against the code.
Rules: implement the skip conditions in section 4; scope static_checks imports to manifest-reachable files; retire the VPS-unsafe footgun; keep H16 low severity. Re-measure on the design split only, and never on the Dell key or hancore_holdout.
Training rows (proposals only; nothing was added; Harris approves):
- akshar.radio-atlas, MIT (code), map data public domain: approve as "works" positive and as good-practice negative examples for per-file rows (radio-fetch, radio-player, radio-favicon, tests/). Exclude assets/countries.json and screenshots; keep LICENSE and copyright notice attached.
- slcode777.omagotchi, MIT code and sprites; sounds CC BY 4.0 and similar: use only .qml/.sh text; exclude sounds/ and anything from CREDITS.md. The strongest pair: reviewed commit 9c15d705 (finding at Service.qml:537) vs HEAD (capped read). That is a ready-made bug_in_published to fixed row with file+line, MIT, text only. Approve.
- io.github.thisisgm.omapods: MIT for root widget files (Panel.qml, Service.qml, Model.js, AirPodsIcon.qml, setup); daemon/ is GPL-3.0 (modified librepods): do NOT use daemon/ in training rows (copyleft and vendored); AGENTS.md/knowledge/ notes are not plugin code. Approve root QML only; as a "works" case it needs the librepods daemon, so label carefully.
- robzolkos.github, MIT: approve Service.qml, Panel.qml, UrlLauncher.qml, omarchy-github-fetch, tests as works examples; the PR 23 diff (openUrl: refuse anything that is not https) is a good before/after security row; PR comments are public GitHub text and already used in data/reviews.
General: MIT requires keeping copyright and license text in dataset provenance (the dataset stores license in meta already). Winner status is not a label of "bug-free": omagotchi was HANCORE-broken at the reviewed commit.

## 7. Replication (everything from the repo)
Inputs: /workspace/sweep_repos/{aksharp5__omarchy-radio-atlas,slcode777__omagotchi,thisisgm__omarchy-pods,robzolkos__omarchy-github} at the commits above; /workspace/wt-retrain-v2/dell/sweep/corpus.jsonl (5,679 rows, 5,522 with local dirs); branch checker-rules-v2 (57018c8); checker-rules/pool.json, findings.json; eval/hancore_holdout/manifest.jsonl; functest/dell_ground_truth.jsonl (ids only). Command: `bash winners/run_all.sh` (from the repo; ~4 minutes, CPU only, no network, no LLM, no seeds, $0). Outputs land in /workspace/usuba-runs/winners/ (winners_profile.json, corpus_profile.json, comparison.md, checker_results.json, overlap output). Scripts: winners/profile.py, run_checker.py, compare.py, overlap.py, run_all.sh. No model was used; if a future step adds an LLM it must be an open-weights model under the $3 budget.
Limits: LOC/API counts are regex-based; "tests" means a tests/ or test-named file; the page JSON for plugins.omarchy.org could not be read (JS-rendered), so catalog fields come from corpus.jsonl; winner status is from Harris, not verified.
