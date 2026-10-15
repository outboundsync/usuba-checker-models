# r5 samples (12)

## 1. hancore_clean:ziouf/omarchy-adaptive-brightness:2dd87df4cf [hancore_clean_approve, approve]

label: ```{"verdict": "approve", "load": "works", "findings": []}```

provenance: `{"kind": "hancore-reviewed-clean", "repo": "ziouf/omarchy-adaptive-brightness", "commit": "2dd87df4cfb494ca2006038400578e3e9474f616", "approved": true, "listed": false, "weak_outcomes": ["closed_no_fix"], "license": "see repo (public plugin)", "category_orig": []}`

user (head): ```
## Checker report
[USB-W07 warn experimental] panel/Panel.qml: line 353: a variable is interpolated into a shell/Lua command string (`"bash", "-c", "omarchy-hyprland-monitor-scaling " +`)
[USB-W01 warn experimental] scripts/lib.sh: runs `cam_probe`, which is not part of a stock Omarchy install and is not listed as a dependency in the README/manifest

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "ziouf.adaptive-brightness",
   4|   "name": "Adaptive Brightness",
   5|   "version": "1.0.0",
   6|   "author": "ziouf",
   7|   "license": "MIT",
   8|   "description": "Adaptive screen brightness from ambient light: IIO light sensor when the machine has one, built-in webcam as fallback. Min/max bounds slider in the Display panel, toggle row, launcher entry, systemd user service.",
   9|   "kinds": [
  10|     "service"
  11|   ],
  12|   "entryPoints": {
  13|     "service": "Service.qml"
  14|   }
  15| }
  16| 
```

### Service.qml
```
   1| import QtQuick
   2| 
   3| // The engine lives in the systemd user service (scripts/loop), not here.
   4| // This service entry only marks the plugin as loaded so the shell accepts
   5| // it; UI integration happens in the Display panel clone (see panel/).
   6| Item {}
   7| 
```

### install-services.sh
```
   1| #!/usr/bin/env bash
   2| # Install the adaptive-brightness user service. The unit points at the
   3| # plugin's scripts under ~/.config/omarchy/plugins/, so install the plugin
   4| 
```

## 2. hancore_clean:jacob-vincent-mink/omarchy-npu-waveform:63fc18ad7b [hancore_clean_approve, approve]

label: ```{"verdict": "approve", "load": "works", "findings": []}```

provenance: `{"kind": "hancore-reviewed-clean", "repo": "jacob-vincent-mink/omarchy-npu-waveform", "commit": "63fc18ad7b6084dc07b843fcb9919bcd32567388", "approved": true, "listed": true, "weak_outcomes": ["closed_no_fix"], "license": "see repo (public plugin)", "category_orig": []}`

user (head): ```
## Checker report
[USB-W05 heuristic/medium] power-reader/install.sh: line 4: privileged/system-level action `sudo`. Fix: keep the plugin unprivileged; document manual root steps in the README instead of escalating from the shell
[USB-W10 warn experimental] Telemetry.qml: reads command output or a file with no size cap
[USB-HC15 warn] power-reader/install.sh:4: privileged or system-level action (`sudo (`)
[USB-HC15 warn] power-reader/install.sh:22: privileged or system-level action (`install -d -m 0755 -o root -g root /usr/`)
[USB-HC15 warn] power-reader/install.sh:23: privileged or system-level action (`install -m 0644 -o root -g root "$source_dir/reade`)

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "jacob.npu",
   4|   "name": "NPU Waveform",
   5|   "version": "1.4.0",
   6|   "author": "Jacob Mink",
   7|   "license": "MIT",
   8|   "description": "Intel NPU waveforms with native performance history and dedicated NPU power.",
   9|   "kinds": [
  10|     "bar-widget"
  11|   ],
  12|   "activation": "on-demand",
  13|   "entryPoints": {
  14|     "barWidget": "BarWidget.qml"
  15|   },
  16|   "barWidget": {
  17|     "displayName": "NPU Waveform",
  18|     "description": "A btop-style waveform sampled from the Intel NPU kernel busy-time counter.",
  19|     "category": "System",
  20|     "aliases": [
  21|       "npu",
  22|       "intel-npu",
  23|       "accelerator"
  24|     ],
  25|     "allowMultiple": false,
  26|    
```

## 3. dell_works_verified:spacexrace/omarchy-screen-mirroring:r01152-0477ffca10 [dell_works_verified, approve]

label: ```{"verdict": "approve", "load": "works", "findings": []}```

provenance: `{"kind": "dell-sweep+checker-agree", "commit": "8f27a9c14e0eb4d78734d6377ff6143280f731b9", "dell_run": "run6", "dell_job": "spacexrace__omarchy-screen-mirroring", "dell_label": "works", "checker_pass": true, "issue_urls": null, "checker_report_regenerated_r3": false, "category_orig": []}`

user (head): ```
## Checker report
[USB-W05 heuristic/medium] Panel.qml: line 122: privileged/system-level action `sudo`. Fix: keep the plugin unprivileged; document manual root steps in the README instead of escalating from the shell
[USB-HC15 warn] Panel.qml:122: privileged or system-level action (`sudo p`)
[USB-HC15 warn] bin/omarchy-screen-mirroring:410: privileged or system-level action (`"pkexec",`)
[USB-HC04 warn] bin/omarchy-screen-mirroring:841: predictable shared path `mkfifo "$` can be pre-created as a symlink/FIFO by another process

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "spacexrace.screen-mirroring",
   4|   "name": "Screen Mirroring",
   5|   "version": "1.0.0",
   6|   "author": "spaceXrace",
   7|   "license": "MIT",
   8|   "description": "Discover compatible receivers and mirror your Linux desktop from the Omarchy bar.",
   9|   "kinds": ["bar-widget"],
  10|   "entryPoints": {
  11|     "barWidget": "BarWidget.qml"
  12|   },
  13|   "barWidget": {
  14|     "displayName": "Screen Mirroring",
  15|     "description": "Discover and mirror to compatible screen receivers.",
  16|     "category": "Network",
  17|     "defaultSection": "right",
  18|     "allowMultiple": false,
  19|     "defaults": {},
  20|     "schema": []
  21|   }
  22| }
  23| 
```

### BarWidget.qml
```
   1| import QtQuick
   2| import Quickshell
   3| import qs.Commons
   4| import qs.Ui
   5| 
   6| BarWidget {
   7|   id: root
   8|   moduleName: "spa
```

## 4. dell_works_verified:jjdizz1l/dizziee.auto-wallpaper:r01919-53ca4b9731 [dell_works_verified, approve]

label: ```{"verdict": "approve", "load": "works", "findings": []}```

provenance: `{"kind": "dell-sweep+checker-agree", "commit": "c5397646b96eaba45710b32e2dd77a9a4720ddc9", "dell_run": "run18", "dell_job": "jjdizz1l__dizziee.auto-wallpaper", "dell_label": "works", "checker_pass": true, "issue_urls": null, "checker_report_regenerated_r3": false, "category_orig": []}`

user (head): ```
## Checker report
(no Checker findings)

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "dizziee.auto-wallpaper",
   4|   "name": "Auto Wallpaper",
   5|   "version": "1.0.0",
   6|   "author": "Dizziee",
   7|   "license": "MIT",
   8|   "description": "Preview the active theme's wallpapers and automatically cycle or shuffle them on a schedule.",
   9|   "kinds": [
  10|     "service",
  11|     "bar-widget"
  12|   ],
  13|   "entryPoints": {
  14|     "service": "Service.qml",
  15|     "barWidget": "BarWidget.qml"
  16|   },
  17|   "barWidget": {
  18|     "displayName": "Auto Wallpaper",
  19|     "description": "Preview and automatically cycle the active theme's wallpapers.",
  20|     "category": "System",
  21|     "allowMultiple": false,
  22|     "defaultSection": "right",
  23|     "defaults": {
  24|       "enabled": true,
  25|       "intervalMinutes": 30,
  26|       "mode": "sequential"
  27|     },
  28|     "schema": [
  29|       {
  30|         "key": "enabled",
  31|         "type": "boolean",
  32|         "label": "Automatic switching",
  33|         "description": "Start cycling wallpapers automatically.",
  34|         "defaultValue": true
  35|       },
  36|       {
  37|         "key": "intervalMinutes",
  38|         "type": "integer",
  39|         "label": "Interval (minutes)",
  40|         "description": "How often the wallpaper changes.",
  41|         "min": 5,
  42|         "max": 1440,
  43|       
```

## 5. version_history:pxllbt/better-recast:5f9a22a6cb:broken [version_history, changes_requested]

label: ```{"verdict": "changes_requested", "load": "broken", "findings": [{"category": "runtime:logic-error", "severity": "blocker", "file": "Config.js", "line": 20, "finding": "The hardcoded default `frameMode: \"cfr\"` forces constant frame rate encoding even when the source content is variable, causing post-save video lag and synchronization issues due to the mismatch between the enforced CFR and the actual VFR input."}]}```

provenance: `{"kind": "version-history-fix", "repo_url": "https://github.com/pxllbt/better-recast", "repo": "pxllbt/better-recast", "commit": "5f9a22a6cbe64591b43086da34fc9df48e8c5933", "parent": "6508df63ae923ac7a86afe6c43cf25faf4146899", "date": "2026-09-20T18:58:24+08:00", "subject": "Fix post-save video lag: race condition, typo, vfr, keyframe interval", "file": "Config.js", "line": 20, "history_bug_kind":`

user (head): ```
## Checker report
[USB-A02] Panel.qml: line 110: `onConfigChanged` is not a signal of `Connections` (handler never fires). Fix: `Connections` signals: none besides <prop>Changed
[USB-W10 warn experimental] BarWidget.qml: reads command output or a file with no size cap
[USB-W07 warn experimental] Service.qml: line 114: a variable is interpolated into a shell/Lua command string (`"bash", "-c", "mkdir -p " +`)
[USB-HC02 warn] scripts/gsr-ipc.py:36: socket recv loop accumulates data with no total-size ceiling
[USB-HC02 warn] scripts/gsr-ipc.py:74: socket recv loop accumulates data with no total-size ceiling

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "pix.recast",
   4|   "name": "Better Recast",
   5|   "version": "1.0.0",
   6|   "author": "pixllbeat",
   7|   "license": "MIT",
   8|   "description": "GPU-accelerated screen recording with automatic hardware detection",
   9|   "kinds": [
  10|     "service",
  11|     "bar-widget"
  12|   ],
  13|   "keepLoaded": true,
  14|   "entryPoints": {
  15|     "service": "Service.qml",
  16|     "barWidget": "BarWidget.qml"
  17|   },
  18|   "barWidget": {
  19|     "displayName": "Better Recast",
  20|     "description": "Record, pause, and manage GPU screen recordings",
  21|     "category": "System",
  22|     "defaultSection": "right",
  23|     "allowMultiple": false
  24|   }
  25| }
```

### BarWidget.qml
```
   1| import QtQuick
   2| import Quickshell
   3| import Quickshell.Io
 
```

## 6. version_history:artur-hash/omarchy-smartac:fb6a9e2b62:broken [version_history, changes_requested]

label: ```{"verdict": "changes_requested", "load": "broken", "findings": [{"category": "runtime:error-handling", "severity": "blocker", "file": "bin/smartac", "line": 172, "finding": "The `api GET /devices` call on silently produces no output when an unknown device ID is provided because the subsequent `jq` filter yields nothing instead of triggering an error, leaving the user without feedback that the requested device does not exist."}]}```

provenance: `{"kind": "version-history-fix", "repo_url": "https://github.com/artur-hash/omarchy-smartac", "repo": "artur-hash/omarchy-smartac", "commit": "fb6a9e2b62ca1657d59bb93327afaf6313f6c235", "parent": "5e633bd993b3aac26d7b6620e405114bb0a17cf1", "date": "2026-08-26T17:36:31-03:00", "subject": "Fix: --capabilities now errors on unknown devices", "file": "bin/smartac", "line": 172, "history_bug_kind": "err`

user (head): ```
## Checker report
(no Checker findings)

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "arturhash.smartac",
   4|   "name": "SmartThings AC",
   5|   "version": "0.1.0",
   6|   "author": "artur-hash",
   7|   "license": "MIT",
   8|   "description": "Turn an air conditioner on and off and set its temperature from the bar, through the SmartThings API.",
   9|   "kinds": ["bar-widget"],
  10|   "entryPoints": {
  11|     "barWidget": "BarWidget.qml"
  12|   },
  13|   "barWidget": {
  14|     "displayName": "SmartThings AC",
  15|     "description": "Air conditioner power and temperature",
  16|     "category": "System",
  17|     "defaultSection": "right",
  18|     "allowMultiple": false
  19|   }
  20| }
  21| 
```

### BarWidget.qml
```
   1| import QtQuick
   2| import qs.Commons
   3| import qs.Ui
   4| 
   5| // Replaced in full by Task 8. Present from the first commit so the repository
   6| // validates at every point in its history, not only at the end.
   7| Item {
   8|   id: root
   9|   required property QtObject bar
  10|   implicitWidth: Style.space(1)
  11|   implicitHeight: Style.space(1)
  12| }
  13| 
```

### LICENSE
```
   1| MIT License
   2| 
   3| Copyright (c) 2026 artur-hash
   4| 
   5| Permission is hereby granted, free of charge, to any person obtaining a copy
   6| of this software and associated documentation files (the "Software"), to deal
   7| in the Software without restriction, including without li
```

## 7. hancore_concrete:wookelvin/omarchy-workspace-swipe:914f36ae2e [hancore_concrete, changes_requested]

label: ```{"verdict": "changes_requested", "load": "unsure", "findings": [{"category": "unbounded-input-resource", "severity": "blocker", "file": "GestureOverlay.qml", "line": 81, "finding": "`GestureOverlay.qml` and `Workspaces.qml` expose predictable Unix-socket listeners to a persistent `SplitParser` without a connection, line, or byte ceiling."}]}```

provenance: `{"kind": "hancore-concrete-verified", "commit": "914f36ae2eb7ae89efe5dd443b43a633669e8426", "source_tree": "hancore_cache_partial_tree", "findings": [{"bug_kind": "unbounded-input-resource", "confidence": "high", "verify": "quoted_code_near_line", "line_derived": false, "kind_relabeled": true, "orig_kind": "process-lifecycle-timeouts", "comment_url": "https://github.com/omacom/omarchy-plugin-marke`

user (head): ```
## Checker report
(no Checker findings)

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "io.github.wookelvin.workspace-swipe",
   4|   "name": "Workspace Swipe",
   5|   "version": "2.0.0",
   6|   "author": "Kelvin Woo",
   7|   "license": "MIT",
   8|   "description": "Compositor-synchronized four-finger workspace sliding with edge resistance, workspace numbers, and a live bar indicator.",
   9|   "kinds": ["service", "bar-widget"],
  10|   "keepLoaded": true,
  11|   "entryPoints": {
  12|     "service": "GestureOverlay.qml",
  13|     "barWidget": "Workspaces.qml"
  14|   },
  15|   "barWidget": {
  16|     "displayName": "Workspace Swipe",
  17|     "description": "Workspace numbers with a finger-tracked active marker",
  18|     "category": "Compositor",
  19|     "allowMultiple": false,
  20|     "defaultSection": "left"
  21|   }
  22| }
  23| 
```

### GestureOverlay.qml
```
   1| import Quickshell
   2| import Quickshell.Io
   3| import Quickshell.Wayland
   4| import QtQuick
   5| import qs.Commons
   6| import qs.Ui
   7| 
   8| Item {
   9|   id: root
  10| 
  11|   property bool gestureActive: false
  12|   property bool gestureEdge: false
  13|   property int gestureBase: 1
  14|   property int gestureTarget: 2
  15|   property real gestureProgress: 0
  16|   property real settleDestination: 0
  17|   property int settleDuration: 180
  18| 
  19|   function consumeLine(rawLine) {
  20|     const fields = String(rawLine 
```

## 8. hancore_concrete:labrat-0/omarchy-omasift:0d77f2236e [hancore_concrete, changes_requested]

label: ```{"verdict": "changes_requested", "load": "unsure", "findings": [{"category": "file-safety-symlink-perms", "severity": "blocker", "file": "Service.qml", "line": 89, "finding": "The shell then reads the cache using an unbounded pathname-based `FileView`."}]}```

provenance: `{"kind": "hancore-concrete-verified", "commit": "0d77f2236e9cf6c0bd4a15ec98aa21d5204258e2", "source_tree": "hancore_cache_partial_tree", "findings": [{"bug_kind": "file-safety-symlink-perms", "confidence": "high", "verify": "quoted_code_near_line", "line_derived": false, "kind_relabeled": false, "orig_kind": "unbounded-input-resource", "comment_url": "https://github.com/omacom/omarchy-plugin-marke`

user (head): ```
## Checker report
[USB-W10 warn experimental] Service.qml: reads command output or a file with no size cap

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "io.github.labrat-0.omasift",
   4|   "name": "OmaSift",
   5|   "version": "1.0.0",
   6|   "author": "mick 'labrat' donahue",
   7|   "license": "MIT",
   8|   "description": "Search the Omarchy plugin marketplace from the shell, with the review status of every listing shown before you install it.",
   9|   "kinds": [
  10|     "service",
  11|     "bar-widget",
  12|     "overlay"
  13|   ],
  14|   "keepLoaded": true,
  15|   "entryPoints": {
  16|     "service": "Service.qml",
  17|     "barWidget": "BarWidget.qml",
  18|     "overlay": "Browser.qml"
  19|   },
  20|   "barWidget": {
  21|     "displayName": "OmaSift",
  22|     "description": "Search the plugin marketplace and see what has actually been reviewed.",
  23|     "category": "System",
  24|     "aliases": [
  25|       "omasift",
  26|       "sift",
  27|       "marketplace",
  28|       "plugins"
  29|     ],
  30|     "allowMultiple": false,
  31|     "defaultSection": "right",
  32|     "defaults": {
  33|       "refreshHours": 24,
  34|       "palette": "lab"
  35|     },
  36|     "schema": [
  37|       {
  38|         "key": "refreshHours",
  39|         "type": "integer",
  40|         "label": "Refresh the catalog every (hours)",
  41|         "min": 1,
  42|         "max": 168,
  43|         "step": 1,
  
```

## 9. dell_broken_verified:lavrinovich86/omarchy-agy-token-usage:r02565-6d5bfe9717 [dell_broken_verified, changes_requested]

label: ```{"verdict": "changes_requested", "load": "broken", "findings": [{"category": "load:invalid-binding", "severity": "blocker", "file": "Panel.qml", "line": 233, "finding": "Cannot assign to non-existent property 'font' on Button. The syntax 'font.family: root.fontFamily' is invalid; use a 'font { family: ... }' block instead."}]}```

provenance: `{"kind": "dell-sweep+checker-agree", "commit": "76d0ce94c3110500ba652eaa219482012eeea9ea", "dell_run": "run20", "dell_job": "lavrinovich86__omarchy-agy-token-usage", "dell_label": "broken", "checker_pass": false, "issue_urls": null, "checker_report_regenerated_r3": false, "category_orig": ["load:property-assignment"]}`

user (head): ```
## Checker report
[USB-W10 warn experimental] BarWidget.qml: reads command output or a file with no size cap

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "agy.token-usage",
   4|   "name": "AGY Token Usage",
   5|   "version": "1.0.0",
   6|   "author": "Antigravity",
   7|   "license": "MIT",
   8|   "description": "Antigravity (AGY) token usage, prompt pace, and session metrics in a native Omarchy bar panel.",
   9|   "kinds": [
  10|     "bar-widget"
  11|   ],
  12|   "activation": "on-demand",
  13|   "entryPoints": {
  14|     "barWidget": "BarWidget.qml"
  15|   },
  16|   "barWidget": {
  17|     "displayName": "AGY Tokens",
  18|     "description": "One bar icon and dropdown panel: today's token consumption, 7-day pace, model split, and recent sessions.",
  19|     "category": "AI",
  20|     "aliases": ["agy", "antigravity", "gemini-tokens"],
  21|     "allowMultiple": false,
  22|     "defaultSection": "right",
  23|     "defaults": {
  24|       "refreshIntervalSec": 60,
  25|       "showLabel": true
  26|     },
  27|     "schema": [
  28|       {
  29|         "key": "refreshIntervalSec",
  30|         "type": "integer",
  31|         "label": "Refresh interval (seconds)",
  32|         "min": 10,
  33|         "max": 3600,
  34|         "step": 10,
  35|         "defaultValue": 60,
  36|         "description": "How often the token statistics update from AGY transcripts"
  37|       },
  38|       {
  39|         "key
```

## 10. dell_broken_verified:flaviomedeiros/rssheadlines:r02376-e66cf0b426 [dell_broken_verified, changes_requested]

label: ```{"verdict": "changes_requested", "load": "broken", "findings": [{"category": "in-use:placeholder-data", "severity": "blocker", "file": "QmlSmokeTest.qml", "line": 70, "finding": "Hardcoded placeholder URL `https://example.com/feed.xml` is used as real data instead of reading from settings."}]}```

provenance: `{"kind": "dell-sweep+checker-agree", "commit": "166bd57bf386fbad59131bd1d715c8489c319851", "dell_run": "run2", "dell_job": "com.flaviomedeiros.rss.headlines", "dell_label": "broken", "checker_pass": false, "issue_urls": null, "checker_report_regenerated_r3": false, "category_orig": ["security:placeholder-credential"]}`

user (head): ```
## Checker report
[USB-H07 heuristic/high] QmlSmokeTest.qml: line 70: placeholder endpoint/credential `https://example.com` used as real data. Fix: read the endpoint/key from settings (declared in manifest defaults) or a real config file; never ship example.com / dummy keys
[USB-W01 warn experimental] notify.sh: runs `flush_pending`, which is not part of a stock Omarchy install and is not listed as a dependency in the README/manifest
[USB-HC04 warn] notify.sh:51: predictable shared path `.tmp.$$` can be pre-created as a symlink/FIFO by another process

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "com.flaviomedeiros.rss.headlines",
   4|   "name": "RSS Headlines",
   5|   "version": "1.0.2",
   6|   "author": "Flavio Medeiros",
   7|   "license": "MIT",
   8|   "description": "RSS headlines in the Menu Bar, powered by Newsboat.",
   9|   "kinds": [
  10|     "bar-widget"
  11|   ],
  12|   "entryPoints": {
  13|     "barWidget": "RSSHeadlines.qml"
  14|   },
  15|   "barWidget": {
  16|     "displayName": "RSS Headlines",
  17|     "description": "Shows the latest RSS articles in a bar panel.",
  18|     "category": "Info",
  19|     "allowMultiple": false,
  20|     "defaultSection": "right",
  21|     "defaults": {
  22|       "maxArticles": 10,
  23|       "maxFeeds": 5,
  24|       "feedUrls": "",
  25|       "refreshIntervalSec": 900
  26|     },
  27|     "schema": [
  28|       {
  29|         "key": "maxArticles",
  30|     
```

## 11. dell_works_verified:farangkao/omarchy-emojis-nerd:r00871-cf79c8295e [dell_works_verified, approve]

label: ```{"verdict": "approve", "load": "works", "findings": []}```

provenance: `{"kind": "dell-sweep+checker-agree", "commit": "bda347615e3b0ee92d02d1ca2fb0d488709afddb", "dell_run": "run2", "dell_job": "farangkao.emojis-nerd", "dell_label": "works", "checker_pass": true, "issue_urls": null, "checker_report_regenerated_r3": false, "category_orig": []}`

user (head): ```
## Checker report
[USB-W03 warn experimental] tools/convert_kaomoji.py: line 21: runs or installs remote code that is not pinned to an immutable ref (`https://raw.githubusercontent.com/w33ble/emoticon-data/maste`)

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "farangkao.emojis-nerd",
   4|   "name": "Emojis & Nerd Fonts",
   5|   "version": "1.2.1",
   6|   "author": "farangkao",
   7|   "license": "MIT",
   8|   "description": "Search, copy, and type emojis, kaomoji, and Nerd Font glyphs — with Recents",
   9|   "kinds": [
  10|     "overlay"
  11|   ],
  12|   "keepLoaded": true,
  13|   "entryPoints": {
  14|     "overlay": "Emojis.qml"
  15|   },
  16|   "omarchy": {
  17|     "clonedFrom": "omarchy.emojis"
  18|   }
  19| }
  20| 
```

### EmojiSearch.js
```
   1| function parseEmojis(raw) {
   2|   try {
   3|     var data = JSON.parse(String(raw || ""))
   4|     return Array.isArray(data) ? data : []
   5|   } catch (e) {
   6|     return []
   7|   }
   8| }
   9| 
  10| function normalizedQuery(query) {
  11|   return String(query || "").trim().toLowerCase()
  12| }
  13| 
  14| function keywordText(item) {
  15|   return String((item && item.k) || "").toLowerCase()
  16| }
  17| 
  18| function filterEmojis(emojis, query, limit) {
  19|   var values = Array.isArray(emojis) ? emojis : []
  20|   var needle = normalizedQuery(query)
  21|   var max = limit === undefined || limit === null ? 1000 : Number(limit)
  22|   if (is
```

## 12. dell_broken_verified:deoxizn/keybind-manager:r02491-ed2f3feadf [dell_broken_verified, changes_requested]

label: ```{"verdict": "changes_requested", "load": "broken", "findings": [{"category": "load:missing-import", "severity": "blocker", "file": "qml/KeybindCatalog.js", "line": 98, "finding": "Uses CommonJS `module.exports` which is not defined in QML's JavaScript environment; causes `ReferenceError: module is not defined` at load time."}]}```

provenance: `{"kind": "dell-sweep+checker-agree", "commit": "443a7e7a937fa5572349722224e5637203e88a92", "dell_run": "run14", "dell_job": "deoxizn__keybind-manager", "dell_label": "broken", "checker_pass": false, "issue_urls": null, "checker_report_regenerated_r3": true, "category_orig": ["load:qml-import-error"]}`

user (head): ```
## Checker report
[USB-W01 warn experimental] scripts/apply.sh: runs `about`, which is not part of a stock Omarchy install and is not listed as a dependency in the README/manifest

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "dev.deoxizn.keybind-manager",
   4|   "name": "Keybind Manager",
   5|   "version": "1.0.0",
   6|   "author": "Deoxizn",
   7|   "license": "MIT",
   8|   "description": "Add, override, and disable Hyprland keybindings from the bar, with a rolling backup and one-click revert.",
   9|   "kinds": ["service", "bar-widget"],
  10|   "keepLoaded": true,
  11|   "entryPoints": {
  12|     "barWidget": "qml/BarWidget.qml",
  13|     "service": "qml/Service.qml"
  14|   },
  15|   "barWidget": {
  16|     "displayName": "Keybind manager",
  17|     "description": "Custom keybindings panel with backup and revert",
  18|     "category": "System",
  19|     "defaultSection": "left",
  20|     "allowMultiple": false
  21|   }
  22| }
  23| 
```

### qml/BarWidget.qml
```
   1| pragma ComponentBehavior: Bound
   2| 
   3| import QtQuick
   4| import Quickshell
   5| import Quickshell.Io
   6| import qs.Commons
   7| import qs.Ui
   8| 
   9| // Bar button for Keybind Manager and host for the keybind panel. Shows a
  10| // keyboard glyph; left click toggles the panel.
  11| //
  12| // Theming: colors and sizes come from the active bar. A Shibumi bar hands us
  13| // its VisualTokens (bar.visualTokens); any other host is
```
