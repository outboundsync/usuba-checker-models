# Hand spot-check (30 random rows of verified.jsonl, grader+filters v1, seed 7) — 2026-10-13

Judged by reading the code: REAL = would plausibly do what the prompt asks on Omarchy 4.0.4 using real APIs/binaries.

REAL (10): v3-399 omanews (HN via curl+jq), v3-404 pomodoro, v3-507 VLANs (nmcli), v3-465 DeepL s1 (curl; missing moduleName),
v3-424 blackjack, v3-99 net throughput (sysfs; "per-process" is really per-remote-IP), v3-402 named workspaces (marginal:
modelData.windows/focusedWindow dubious), v3-618 workspaces, v3-422 QR generator (likely qrencode), v3-95 hermes harness (thin).

NOT REAL (20): v3-414 Fastmail (invented REST endpoint, Qt.resolvedUrl("~/...")); v3-593 (Hyprland.windows/minimized invented);
v3-437 overview (no thumbnails, Item root); v3-605 (fcitx5-remote -l is not a list flag); v3-109 (invented Hyprland.windows,
overlays not windows); v3-503 s0 (leaked reasoning prose in answer); v3-549 (hardcoded vault URL list incl. example.com);
v3-392 s1 (invented File{} type); v3-498 (invented voxtyp.service names); v3-441 (invented onClientAdded); v3-83 (guessed paths);
v3-69 ("lock" = notify-send); v3-566 (AdGuard toggle endpoint wrong); v3-599 (execDetached return/readAllStandardOutput invented);
v3-497 (invented hyprsunset --schedule, `date -d "today sunset"`); v3-488 (admitted fake proxy data); v3-598 (execDetached callback);
v3-552 (fake MTA api_key/endpoint, resolvedUrl argv); v3-542 (shell.services.get invented); v3-417 (undefined `settings`).

Real-keep rate: 10/30 = 33% (generous; strict ~25%). Earlier interim check of 10 rows: ~4/10.
After this check, filters v2 were added (File{}, execDetached callback/return, Hyprland.windows/onClientAdded,
readAllStandardOutput, leaked reasoning prose, example.com/api_key/'today sunset'/admitted-proxy). They remove 8 of the 20 bad rows
above (in-sample, so the post-filter real rate (~10/22 = 45%) is optimistic). The final verified.jsonl (55 rows) uses filters v2.
Recommendation: treat verified.jsonl as candidate data needing an LLM/human judge pass, not gold.
