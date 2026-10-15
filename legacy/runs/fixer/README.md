# fixer: stock Qwen3.6-27B + grader-feedback fixer loop (2026-10-13)
49 clean holdout, qwen/qwen3.6-27b via OpenRouter (ZDR on), temp 0, reasoning low, max_tokens 16000. loop.py: gen -> functest (rescore.score_row) -> on fail, grader text (static fails, runtime errors/warnings, truncation/loop notes) sent back as a user turn; up to 3 fix rounds. No reference answers shown. Loops/truncations = fail.

| prompt | grader r0 | r1 | r2 | r3 | hand r0 | hand r3 (firm / lenient) | cost |
|---|---|---|---|---|---|---|---|
| base (holdout system prompt) | 5 | 8 | 12 | 13 | 4 | 4 / 4 | $2.16 |
| hand v1 (sys_hand.txt) | 3 | 4 | 5 | 5 | 3 | 3 / 3 | $2.60 |
| hand v2 (sys_hand2.txt, QML-syntax fix) | 5 | 7 | 9 | 13 | 3 / 4 | 5 / 7 (+1 doubtful) | $2.39 |
| GEPA | running (gepa_chain.sh -> gepa_result.json) | | | | | | |
Reference: GPT-5.6 20, Opus 18, stock 27B 6 (earlier run).

Hand-check, base (13 grader passes -> 4): accept fix_manifest x4 (51,52,53,54). Reject: 0 background (`new SequentialAnimation()` in JS, invalid), 1 background (undefined `_newSource`, self-restarting animation), 2 clipboard (`Qt.clipboard` does not exist, history never fills), 5 notifications (no notification source, DropShadow w/o import), 7 dropbox (explicit simulated fake data), 19 weather (hardcoded 22°C, placeholder settings), 31 portwatch (Process.start()/onFinished/stdout are not Quickshell API, kinds "barWidget"), 45 tablet (console.log stubs), 48 menu (invented `Service.call`). The fixer mostly teaches the model to strip imports/APIs until the grader passes, producing stubs.
Hand v1 (5 -> 3): fix x3 accept; reject 27 vimarchy (undeclared `shell.wm` swallowed by try -> shows nothing), 49 tablet.py (launches foot as "keyboard", `hyprctl reload` undoes the keywords it just set). v1 prompt's Process example led to inline `Process {}` inside JS functions -> 19 syntax errors.
Hand v2 (13 -> 5 firm / 7 lenient): accept fix 51,52,54; 13 power (real data, ships bin/power.sh); 31 portwatch (real ss data, kill). Lenient: 18 weather (real open-meteo, but hardcoded London; forecast array mutated in place so it never refreshes), 2 clipboard (real wl-paste history, but `wtype ctrl+v` types the literal text, cat on unexpanded ~ path). Doubtful: 10 monitor (brightness works; `hyprsunset enable/disable` not real). Reject: 50 (only manifest, no component), 49 tablet.py (onboard/xinput/setxkbmap not on Dell, X11 tools under Wayland, hidden in sh -c), 30 flush-bar (clock placeholder, no flush behaviour), 0 background (invented `hyprctl background add`, name clash), 16 speedtest (`Quickshell.exec` promise API does not exist; 18k chars of rambling).
Grader gaps found: binaries inside `sh -c` strings are not checked; chunk tasks pass with a manifest-only answer; fake/simulated data and invented JS APIs on click paths pass.
