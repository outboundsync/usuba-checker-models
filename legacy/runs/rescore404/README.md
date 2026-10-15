# 2026-10-12 grader refresh + v3 retrain

- Dell is on omarchy 4.0.4-1, but /usr/share/omarchy/shell is byte-identical to c668141 (the old omarchy-dell tree) apart from the harness probe, so the grader was **not** stale. The false built-in failures (ShellIpc / UntypedInput / OverlayWindow) came from diag.py/build_v3.py reading built-ins from the newer /opt/ft/omarchy tree.
- Grader changes: FT_OMARCHY=/opt/ft/omarchy-4.0.4 (rebuilt and verified against dell-ref/omarchy-4.0.4); system_bins pruned to what `command -v` finds on the Dell (54 assumed binaries are absent, e.g. walker, mako, playerctl, hyprlock, alacritty); a ReferenceError inside a pure colour binding is now a warning (limon.todo). fix_manifest now needs a namespaced id. eval_dell: 90/90, no false passes.
- Built-ins (4.0.4 tree, acme ids): 30/36 pass. Failures: agents, lock and polkit write /etc paths (dangerous-write; they are privileged system plugins), tailscale (sudo, and tailscale is not installed on the Dell), system-update (zero size, hidden when no update is pending), spacer (placeholder-ui, trivial by design). elsewhen and remote-session are not in 4.0.4.
- Training: added 6 built-ins (ActiveWindow, image-picker, KeyboardLayout, media, Microphone, Workspaces) with 2 phrasings each, 607 -> 619 rows. Excluded 8 holdout paths, 2 near-duplicate holdout answers and 7 answers over 8192 tokens.
- Human ceiling is 26/49: 18 of the 20 first-party holdout gold answers come from the newer tree and fail on 4.0.4.
- v3 7B: 4/49 (3/32 full plugin, 32 loops); best-of-16: 11/32 by the grader, 9/32 hand-checked (jumpy and afterglow are doubtful). Loops and truncations count as fails.

## Usuba Checker v0.1 rescore (2026-10-13)
`results49_usuba.json`, `SCOREBOARD_USUBA.md` (board_usuba.py). Same 49 prompts and generations, graded by Usuba Checker v0.1 (functest/STANDARD.md). All changed verdicts were hand-checked:
- **Up, row 28 (several models):** the answer writes `~/.config/hypr/looknfeel.lua`. Per Harris, that is now a USB-S01 warning instead of a fail. The human reference also gained this row.
- **Up, rows 46 and 42:** the old grader failed these because of a surface.tablet `NativeWidget.createObject` race in the *upstream* tree, which also fires on the reference answer. The race is now filtered when the answer leaves NativeWidget.qml untouched, so these were old false fails.
- **Down (all real defects):**
  - gemini 32: `engine.search()`, a method Services.Engine does not have.
  - gemini 41: a menu whose handlers only call console.log.
  - grok-4.3 23: uses `Quickshell.config` and an unknown type.
  - grok-build 8, 11, 23: hardcoded "5.2 GB used" and "in a real implementation" simulated data.
  - kimi 0: uses `Qt.labs`.
  - qwen3-coder 42: relies on `onboard`, an X11-only tool.
  - v3_404 18: references `scripts/weather.sh`, which is not shipped.
