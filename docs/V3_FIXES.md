# v3 fixes: host contract, new rules, date check, audit (2026-10-15)

Branch `v3-fixes`. Inputs: `usuba-runs/builder-skills/REPORT.md` (study of tcballard/build-omarchy-plugins @ e3a45f8, MIT) and `usuba-runs/winners/REPORT.md`. Everything below is reproducible with `v3fixes/run_all.sh` (see Replication).

## 1. Host contract: what was verified
Verified against the shipped Omarchy 4.0.4 shell tree (`functest/dell_env/omarchy-shell-ref.tar.gz`) and real Quickshell 0.3.2 in headless sway:
- `PluginRegistry.validateManifest` rejects a manifest without `schemaVersion === 1`, `id`, `name`, `version`, non-empty `kinds`, object `entryPoints`.
- `shell.qml entryPointUrl` maps kind -> entryPoints key (`bar-widget` -> `barWidget`; `panel`, `overlay`, `menu`, `service`, `bar` keep their names). The entry-point **key** names a **file**. The old prompt wording reversed this.
- The panel loader prefers panel > overlay > menu. Summon calls `item.open(payload)` only when it is a function; hide calls `close` through `invokeIfLoaded`, silently skipped when absent. So a panel/overlay/menu with only `toggle()` loads and is never shown. `qs.Ui` `Panel` supplies both; `KeyboardPanel` and `PopupCard` supply only `close`.
- `required property var shell` fails at load ("Required property shell was not initialized"): the host injects `omarchyPath/shell/manifest/barWidgetRegistry/pluginRegistry/service` after load.
- NOT verified / not claimed: `moduleName` (no evidence in the tree), `keepLoaded` (no further evidence). A nested `ShellRoot` loads fine in the probe, so USB-L02 is a lead (warn), not a load blocker.

## 2. Prompt (train/prompt_v3.py)
- Wording: entry-point key -> file, kind -> key mapping, registry rejection (schemaVersion 1 and required fields).
- New bullets: panel/overlay/menu without open/close (`Panel` base exempt); ShellRoot / own quickshell; `required property` on host-injected names; a missing cap or timeout is a blocker only when you can say who controls the input; large local content is a warning; `Util.shellQuote` / `bash -c` dismissal; capabilities are not defects.
- Manifests in shots carry `schemaVersion 1` and `version`.
- Shot 6 (overlay approved with only `toggle()`) replaced by a clean overlay with `open/close`. New shot 7: panel with only `toggle()` -> `load:panel-lifecycle`. Both shots load in headless Quickshell. All rows must be re-wrapped with `prompt_v3.rebuild` (the prefix is in each row).

## 3. New Checker rules (functest/usuba/lifecycle_rules.py)
Measured on the 70% design split (split = sha1(repo), pool `usuba-runs/checker-rules/pool.json`, 5327 plugins, Dell-key-free; labels are Dell sweep runtime labels). Base broken rate 0.145. The test split was read only after the decision. `eval/hancore_holdout` and Dell key labels were never read.

| rule | design fired (labelled) | broken / works | precision | lift | test fired / broken | decision |
|---|---|---|---|---|---|---|
| L01 open/close missing | 33 | 7 / 16 | 0.25 | 1.72 | 19 / 1 | experimental (test lift 0.4; also fires on working plugins that are only toggled) |
| L02 ShellRoot / own quickshell | 4 | 3 / 1 | 0.75 | 5.17 | 3 / 2 | enabled as warn |
| L03 required property on injected name | 0 | | | | 0 | enabled (host-verified, no corpus hits) |
| N01 kind without entryPoints key | 0 | | | | 0 | enabled (host-verified) |
| N02 registry rejection | 0 | | | | 0 | enabled (host-verified) |
| W11 cargo --git without 40-char --rev | 6 | 0 / 4 | 0.0 | 0.0 | 6 / 1 | experimental |
| W12 unpinned GitHub Actions | 448 | 92 / 267 | 0.23 (file-level strict 0.038, false-hit 0.10) | 1.58 | 158 / 29 | experimental |
| W13 broad NOPASSWD sudoers | 4 | 1 / 2 | 0.25 | 1.72 | 2 / 1 | experimental |
| W14 bundled binaries | 0 | | | | 0 | experimental stub |

Supply-chain patterns (W11-W13) are policy, not load/runtime defects; the Dell runtime labels cannot confirm them, so they stay experimental. `functest/usuba/lifecycle_rules_enabled.json` holds the list and reasons.

Other rule changes:
- Id collision: `hancore_rules_v2` ids renamed `USB-H01..H25` -> `USB-HC01..HC25`; `rules.py` keeps `USB-H01..H07`. `measure_v3.load` maps old hit files on read (`id_rename_map.json`).
- `USB-M05` (un-namespaced id) demoted blocker -> warning (error only for `omarchy.*`); `rescore.py` follows.
- H21-H24 (now HC21-HC24) demoted to experimental (`rules_v2_enabled.json: enabled_v3_fixes`).
- Skip rules from the winners report: `>/dev/null`, mktemp variables, regex-guarded variables, `hyprctl eval`, helper-wrapped curl, vendored paths. Effect (`skip_effect.log`): e.g. HC01 hit files 370 -> 306 (strict precision 0.268 -> 0.261, false hit 0.072 -> 0.064); HC06 418 -> 280 (0.098 -> 0.107, FH 0.062 -> 0.044); HC02 318 -> 305; others within noise.
- `static_checks.py`: bad-import scoped to manifest-reachable QML (flagged plugins 41 -> 12 of 1776 sampled; of the 29 dropped, 12 were Dell-broken, so recall is traded for fewer false labels); `Style.font` warning retired (VPS-unsafe).

## 4. Date check (hancore/retraction_check.py)
HANCORE reviews with a resource-allocation or unbounded-input blocker later withdrawn by the reviewer. Method: scan the marketplace review threads for withdraw/retract verbs (435 comments, 428 withdraw something, 119 resource-kind, 80 of those dated before 2026-10-03), then adjudicate each (finding, later comment) pair with `qwen/qwen3.5-397b-a17b` (temperature 0, reasoning off, data_collection deny). 158 HANCORE findings in our rows; 12 have a candidate; 9 retracted whole (5 resource-kind, all findings dated before the cutoff), 1 partial.
- Whole: agentdeck, omarchy-spotify-bar, omarchy-nbl-scores, omarchy-rog-control, kait2en-omarchy, opencode-usage, humline, omarchy-ptbr-clipboard, clip -> `retraction_drop_ids.txt` (tier1 resource, tier2 other). Partial: omapass -> `retraction_review_ids.txt`.
- The Touch Bar (#9262) and OmaRead (#9174) withdrawals are confirmed in the scan (dated 2026-10-03) but those plugins have no row in the r2 training data, so no row changes.
- The omagotchi thread (issue 1651) has no withdrawal.
- Cost $0.9732, 447 calls (121,581 prompt / 250,152 completion tokens).

## 5. Audit
- No approve row fires N01/N02/L03. Approve rows firing L01 are all Dell-verified working plugins (ids in `audit_approve_lifecycle_ids.txt`, 6 plugins; 1 in r2 train). They contradict prompt P2 as written; drop from train or keep out of the lifecycle-teaching set. This is why L01 is only experimental: a toggle-only panel can be driven by a service.
- Label noise: 20 pool plugins labelled broken whose only static failure was the out-of-scope bad-import; 7 have no other failure reasons or runtime errors (`label_noise_confirmed.json`, `relabel_broken_to_works_candidates.txt`). Includes omapods (the winners report's example).

## 6. Rows (train/v3data)
- `synthetic_rows.jsonl`: 16 synthetic rows (9 broken, 7 approve; ~3% of r2's 523 train rows), each verified by the Checker and, where possible, headless Quickshell; `source: synthetic_lifecycle`.
- `winners_rows.jsonl`: omagotchi before (blocker), before-warning, after; robzolkos PR 23 https-only pair; omapods root files (text sources only; daemon/ GPL excluded). All MIT with copyright in provenance. include_in_train = false for the 3 omagotchi rows: the "after" Dell label is rt-invisible; the "before" blocker concerns an owner-written state file, which prompt v3's trusted-and-small exception treats as a warning, so the blocker and warning variants are both delivered and r3 decides. Max 28,630 tokens.

## Replication
```
cd <repo>; git checkout v3-fixes
bash v3fixes/run_all.sh          # measure (design, then test), skip effect, audit, rows
python -m pytest functest/tests  # 48 tests
OPENROUTER_API_KEY=... python hancore/retraction_check.py   # model qwen/qwen3.5-397b-a17b, temp 0, cached in retraction_raw.jsonl
```
No random seeds are used: the split is `sha1(repo)` (70/30) and the model runs at temperature 0. Inputs: `usuba-runs/checker-rules/pool.json`, `dell/sweep/hancore_reviews.jsonl`, the shipped shell tree tarball. Total spend $0.97 (cap $6).
