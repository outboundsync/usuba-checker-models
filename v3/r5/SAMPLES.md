# r5 samples (12)

## 1. hancore_clean:filipechagas/omarchy-pinboard:a876061a58 [hancore_clean_approve, approve]

label: ```{"verdict": "approve", "load": "works", "findings": []}```

provenance: `{"kind": "hancore-reviewed-clean", "repo": "filipechagas/omarchy-pinboard", "commit": "a876061a58c7bf7f05dcb83526de80751b66c4f2", "approved": false, "listed": true, "weak_outcomes": ["closed_no_fix"], "license": "see repo (public plugin)", "category_orig": []}`

user (head): ```
## Checker report
(no Checker findings)

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "io.github.filipechagas.omapin",
   4|   "name": "Omapin",
   5|   "version": "0.1.1",
   6|   "author": "Filipe Chagas",
   7|   "description": "Keyboard-first Pinboard capture for Omarchy",
   8|   "license": "MIT",
   9|   "homepage": "https://github.com/filipechagas/omarchy-pinboard",
  10|   "repository": "https://github.com/filipechagas/omarchy-pinboard",
  11|   "keywords": [
  12|     "pinboard",
  13|     "bookmarks",
  14|     "productivity"
  15|   ],
  16|   "kinds": [
  17|     "service",
  18|     "bar-widget"
  19|   ],
  20|   "keepLoaded": true,
  21|   "entryPoints": {
  22|     "service": "Service.qml",
  23|     "barWidget": "BarWidget.qml"
  24|   },
  25|   "barWidget": {
  26|     "displayName": "Omapin",
  27|     "description": "Add and update Pinboard bookmarks",
  28|     "category": "Productivity",
  29|     "allowMultiple": false,
  30|     "defaultSection": "right"
  31|   }
  32| }
  33| 
```

### BarWidget.qml
```
   1| import QtQuick
   2| import qs.Commons as C
   3| import qs.Ui as Ui
   4| 
   5| Ui.BarWidget {
   6|   id: root
   7|   moduleName: "io.github.filipechagas.omapin"
   8| 
   9|   readonly property bool showIcon: setting("showIcon", true) !== false
  10|   readonly property var pinboardService: bar && bar.shell
  11|     ? bar.shell.serviceFor("io.github.filipechagas.omapin")
  12|     : null
  13|  
```

## 2. hancore_clean:ziouf/omarchy-adaptive-brightness:2dd87df4cf [hancore_clean_approve, approve]

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

## 3. dell_works_verified:nejcc/omarchy-safe-update:r00243-7900d748fd [dell_works_verified, approve]

label: ```{"verdict": "approve", "load": "works", "findings": []}```

provenance: `{"kind": "dell-sweep+checker-agree", "commit": "a7750dc17cbc98008f41f21429fc65a485151d16", "dell_run": "run22", "dell_job": "nejcc__omarchy-safe-update", "dell_label": "works", "checker_pass": true, "issue_urls": null, "checker_report_regenerated_r3": false, "category_orig": []}`

user (head): ```
## Checker report
[USB-W05 heuristic/medium] Panel.qml: line 141: privileged/system-level action `sudo`. Fix: keep the plugin unprivileged; document manual root steps in the README instead of escalating from the shell
[USB-W10 warn experimental] BarWidget.qml: reads command output or a file with no size cap
[USB-HC15 warn] Panel.qml:141: privileged or system-level action (`sudo s`)
[USB-HC15 warn] Panel.qml:142: privileged or system-level action (`sudo s`)

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "nejcc.safe-update",
   4|   "name": "Safe Update",
   5|   "version": "0.1.0",
   6|   "author": "Nejcc",
   7|   "license": "MIT",
   8|   "description": "Checks the shell and every plugin after an Omarchy update and shows the snapshot to roll back to",
   9|   "kinds": ["bar-widget"],
  10|   "entryPoints": { "barWidget": "BarWidget.qml" },
  11|   "barWidget": {
  12|     "displayName": "Safe Update",
  13|     "description": "Post-update plugin check and rollback snapshot",
  14|     "category": "System",
  15|     "allowMultiple": false,
  16|     "defaultSection": "right"
  17|   }
  18| }
  19| 
```

### BarWidget.qml
```
   1| import QtQuick
   2| import Quickshell
   3| import Quickshell.Io
   4| import qs.Commons
   5| import qs.Ui
   6| 
   7| // Bar icon for Safe Update. Reads the last post-update check from
   8| // $XDG_STATE_HOME/omarchy-safe-update/last.json (written by bin/safe-update)
   9| // through a file watcher,
```

## 4. dell_works_verified:grupertal/omarchy-nanit:r01600-5a5f286509 [dell_works_verified, approve]

label: ```{"verdict": "approve", "load": "works", "findings": []}```

provenance: `{"kind": "dell-sweep+checker-agree", "commit": "add8665407c6b31bfae9e4de70da28f8a9ba3c96", "dell_run": "run16", "dell_job": "grupertal__omarchy-nanit", "dell_label": "works", "checker_pass": true, "issue_urls": null, "checker_report_regenerated_r3": false, "category_orig": []}`

user (head): ```
## Checker report
[USB-HC19 warn] bin/nanit:12: pip/pipx install without --hash (model-proposed rule)

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "gruper.nanit",
   4|   "name": "Nanit",
   5|   "version": "1.0.1",
   6|   "author": "Tal Gruper",
   7|   "license": "MIT",
   8|   "description": "Nanit baby monitor in the bar: live camera video in the popup, always-on audio while you work, night light and white noise controls.",
   9|   "kinds": [
  10|     "service",
  11|     "bar-widget"
  12|   ],
  13|   "entryPoints": {
  14|     "service": "Service.qml",
  15|     "barWidget": "Panel.qml"
  16|   },
  17|   "barWidget": {
  18|     "displayName": "Nanit",
  19|     "description": "Live Nanit camera in the popup, always-on audio, night light and white noise.",
  20|     "category": "Home",
  21|     "aliases": [
  22|       "nanit",
  23|       "baby",
  24|       "monitor"
  25|     ],
  26|     "allowMultiple": false,
  27|     "defaultSection": "right",
  28|     "defaults": {},
  29|     "schema": []
  30|   }
  31| }
  32| 
```

### NanitIcon.qml
```
   1| import QtQuick
   2| 
   3| // The Nanit mark drawn natively: a filled rounded square with a ring cut out
   4| // of its middle, so it takes the bar's theme color like every other icon.
   5| Item {
   6|   id: root
   7|   property real iconSize: 14
   8|   property color color: "white"
   9|   property color background: "black"
  10| 
  11|   width: iconSize
  12|  
```

## 5. version_history:charlieras262/omarchy-omablur:ffa789aafa:broken [version_history, changes_requested]

label: ```{"verdict": "changes_requested", "load": "unsure", "findings": [{"category": "runtime-qml-api-compat", "severity": "blocker", "file": "Panel.qml", "line": 142, "finding": "The assignment `config.bar.transparent = want` writes a boolean value to the shell configuration, which forces the bar into full invisibility instead of enabling the intended partial opacity with blur effect."}]}```

provenance: `{"kind": "version-history-fix", "repo_url": "https://github.com/charlieras262/omarchy-omablur", "repo": "charlieras262/omarchy-omablur", "commit": "ffa789aafa0290360ba546f30a3fff7f6935ed7a", "parent": "555a6c908dbe17777c833749aa56b5295ba3ee84", "date": "2026-08-27T10:33:23-06:00", "subject": "fix: use partial background opacity instead of full transparency", "file": "Panel.qml", "line": 142, "hist`

user (head): ```
## Checker report
(no Checker findings)

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "charlieras262.omablur",
   4|   "name": "Omablur",
   5|   "version": "1.3.0",
   6|   "author": "Charlieras262",
   7|   "description": "Bar panel to tune window corner rounding and blur intensity live, no config file editing required",
   8|   "kinds": [
   9|     "bar-widget"
  10|   ],
  11|   "entryPoints": {
  12|     "barWidget": "Panel.qml"
  13|   },
  14|   "barWidget": {
  15|     "displayName": "Omablur",
  16|     "description": "Tune window corner rounding and blur intensity",
  17|     "category": "Compositor",
  18|     "defaultSection": "right",
  19|     "allowMultiple": false
  20|   }
  21| }
  22| 
```

### Panel.qml
```
   1| import QtQuick
   2| import Quickshell
   3| import Quickshell.Io
   4| import qs.Ui
   5| import qs.Commons
   6| 
   7| // Bar chip + popup panel to tune window corner rounding and blur intensity
   8| // live. Dragging a slider applies the change to the running Hyprland
   9| // session immediately via `hyprctl eval` (Omarchy's Lua config parser
  10| // doesn't support the older `hyprctl keyword`, so this is required, not
  11| // just faster); no config write, no reload happens for the live preview.
  12| // releasing it persists the setting as a marked block in the user's own
  13| // ~/.config/hypr/looknfeel.lua so it survives restarts, using the same
  14| // atomic, symlink-safe writer other Oma
```

## 6. version_history:deunnis/comapilot:d4e4d76f10:broken [version_history, changes_requested]

label: ```{"verdict": "changes_requested", "load": "unsure", "findings": [{"category": "runtime-qml-api-compat", "severity": "blocker", "file": "Copilot.qml", "line": 185, "finding": "The code uses `hl.config({layerrule=...})` which is an incorrect Lua API shape for Hyprland's `eval` command, causing the blur rule to silently fail and leaving the overlay background unblurred."}]}```

provenance: `{"kind": "version-history-fix", "repo_url": "https://github.com/deunnis/comapilot", "repo": "deunnis/comapilot", "commit": "d4e4d76f1028037e11b4b5b9d570bb5f42321497", "parent": "ce530772c4abc2cf02d37a6f5f7eb86bb742ba04", "date": "2026-08-24T14:39:19+02:00", "subject": "Fix: previous blur fix was a no-op - wrong Lua config API shape", "file": "Copilot.qml", "line": 185, "history_bug_kind": "api-com`

user (head): ```
## Checker report
[USB-H07 heuristic/high] ActionAllowlist.js: line 58: placeholder endpoint/credential `https://example.com` used as real data. Fix: read the endpoint/key from settings (declared in manifest defaults) or a real config file; never ship example.com / dummy keys
[USB-HC01 warn] Copilot.qml:742: curl/wget response is not size-limited (--max-time is a time limit, not a byte cap); a hostile or compromised endpoint can stream unbounded data into memory/disk
[USB-HC01 warn] OllamaProbe.js:10: curl/wget response is not size-limited (--max-time is a time limit, not a byte cap); a hostile or compromised endpoint can stream unbounded data into memory/disk
[USB-HC25 warn] AnthropicBackend.js:14: HTTP request with Authorization/API-key header and default redirects (model-proposed rule)
[USB-HC25 warn] OpenAiCompatBackend.js:8: HTTP request with Authorization/API-key header and default redirects (model-proposed rule)

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "io.github.omacopilot",
   4|   "name": "cOMApilot",
   5|   "version": "0.1.0",
   6|   "author": "Deunnis",
   7|   "license": "MIT",
   8|   "description": "An AI assistant that streams answers and, with your explicit confirmation, can act: open files, run a small set of safe named actions, or drive other Omarchy plugins.",
   9|   "kinds": ["overlay", "bar-widget"],
  10|   "keepLoaded": true,
  11|   "entryPoints": {
  12|     "overlay": "Copilot.qml",
  13|     "barW
```

## 7. hancore_concrete:neilofneils404/acid-alerts:9ada5f89dc [hancore_concrete, changes_requested]

label: ```{"verdict": "changes_requested", "load": "unsure", "findings": [{"category": "unbounded-input-resource", "severity": "blocker", "file": "Model.js", "line": 209, "finding": "`Panel.qml` fetch NWS alert/zone responses into `StdioCollector` with a timeout but no response-size limit, and `Model.js` then materializes the full body with `JSON.parse`."}]}```

provenance: `{"kind": "hancore-concrete-verified", "commit": "9ada5f89dc0d438d5f2a1a84e585b4760cbfd21e", "source_tree": "hancore_cache_partial_tree", "findings": [{"bug_kind": "unbounded-input-resource", "confidence": "high", "verify": "quoted_code_near_line", "line_derived": false, "kind_relabeled": true, "orig_kind": "unbounded-input-resource", "comment_url": "https://github.com/omacom/omarchy-plugin-marketp`

user (head): ```
## Checker report
[USB-A08 heuristic/medium] Panel.qml: line 106: assigns read-only `bar.centerHoverRevealSuppressed` - plugins get the read-only PluginBarApi facade, so this throws and aborts the rest of the function. Fix: call the setter instead, e.g. `bar.setCenterHoverRevealSuppressed(v)`
[USB-HC01 warn] Panel.qml:126: curl/wget response is not size-limited (--max-time is a time limit, not a byte cap); a hostile or compromised endpoint can stream unbounded data into memory/disk
[USB-HC01 warn] Panel.qml:235: curl/wget response is not size-limited (--max-time is a time limit, not a byte cap); a hostile or compromised endpoint can stream unbounded data into memory/disk

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "neil.acid-alerts",
   4|   "name": "Acid Alerts",
   5|   "version": "1.0.0",
   6|   "author": "Neil",
   7|   "license": "MIT",
   8|   "description": "National Weather Service alerts for your Omarchy weather location. Warnings on by default; watches and advisories are opt-in.",
   9|   "kinds": ["bar-widget"],
  10|   "entryPoints": {
  11|     "barWidget": "BarWidget.qml"
  12|   },
  13|   "barWidget": {
  14|     "displayName": "Acid Alerts",
  15|     "description": "Warnings for your weather location, with an idle brand mark when the area is clear.",
  16|     "category": "Info",
  17|     "allowMultiple": false,
  18|     "defaultSection": "center"
  19|   }
  20| }
  21| 
```

### AlertMap.qml
```
   1| import
```

## 8. hancore_concrete:lekonidus/omarchy-currency:1fbe9b6137 [hancore_concrete, changes_requested]

label: ```{"verdict": "changes_requested", "load": "unsure", "findings": [{"category": "unbounded-input-resource", "severity": "blocker", "file": "Panel.qml", "line": 120, "finding": "`Panel.qml` fetches a remote API response with only a time limit, and `Panel.qml` buffers the complete stdout in `StdioCollector` before parsing it."}]}```

provenance: `{"kind": "hancore-concrete-verified", "commit": "1fbe9b6137cb1412fabd8547de00cb2c2fe830c1", "source_tree": "src_full", "findings": [{"bug_kind": "unbounded-input-resource", "confidence": "high", "verify": "quoted_code_near_line", "line_derived": false, "kind_relabeled": true, "orig_kind": "process-lifecycle-timeouts", "comment_url": "https://github.com/omacom/omarchy-plugin-marketplace/issues/7865`

user (head): ```
## Checker report
[USB-W10 warn experimental] Panel.qml: reads command output or a file with no size cap
[USB-HC01 warn] Panel.qml:93: curl/wget response is not size-limited (--max-time is a time limit, not a byte cap); a hostile or compromised endpoint can stream unbounded data into memory/disk

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "io.github.lekonidus.currency",
   4|   "name": "Currency",
   5|   "version": "1.0.0",
   6|   "author": "Lekonidus",
   7|   "license": "MIT",
   8|   "description": "Convert currencies from the bar using ECB rates.",
   9|   "kinds": ["bar-widget"],
  10|   "entryPoints": {
  11|     "barWidget": "Entry.qml"
  12|   },
  13|   "barWidget": {
  14|     "displayName": "Currency",
  15|     "description": "Live FX rate with a conversion panel",
  16|     "category": "Info",
  17|     "allowMultiple": false,
  18|     "defaultSection": "center",
  19|     "defaults": {
  20|       "from": "USD",
  21|       "to": "ILS"
  22|     },
  23|     "schema": [
  24|       { "key": "from", "type": "string", "label": "From currency" },
  25|       { "key": "to", "type": "string", "label": "To currency" }
  26|     ]
  27|   }
  28| }
  29| 
```

### Entry.qml
```
   1| import QtQuick
   2| import Quickshell
   3| import Quickshell.Io
   4| import qs.Commons
   5| import qs.Ui
   6| import "Model.js" as Model
   7| 
   8| // Icon-sized bar slot (same as weather / hass). Rate lives in the tooltip
   9| // an
```

## 9. dell_broken_verified:koenhendriks/omarchy-menu-calculator-plugin:r02382-7dc6d8e42c [dell_broken_verified, changes_requested]

label: ```{"verdict": "changes_requested", "load": "broken", "findings": [{"category": "in-use:missing-file", "severity": "blocker", "file": "AppLibraryShim.qml", "line": 166, "finding": "Line 166 constructs a path to `/shell/services/hidden-entries.sh` which is not shipped by the plugin; the script must be included in the plugin package or the logic inlined."}, {"category": "load:unknown-type", "severity": "blocker", "file": "BarWidget.qml", "line": 6, "finding": "Import `file:///usr/share/omarchy/shell/plugins/menu` as Upstream does not provide `Upstream.BarWidget` type; the type is unknown and the widget cannot be created."}]}```

provenance: `{"kind": "dell-sweep+checker-agree", "commit": "2ffacdd5ab20d5af67e570a80387986a9e1d6585", "dell_run": "run6", "dell_job": "koenhendriks__omarchy-menu-calculator-plugin", "dell_label": "broken", "checker_pass": false, "issue_urls": null, "checker_report_regenerated_r3": true, "category_orig": [null, null]}`

user (head): ```
## Checker report
[USB-Q01] BarWidget.qml: line 6: unknown QML type `Upstream.BarWidget` - not provided by any module this file imports. Fix: add `import qs.Ui`
[USB-Q01] Menu.qml: line 15: unknown QML type `Upstream.Menu` - not provided by any module this file imports. Fix: add `import Qt.labs.platform`

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "io.github.koenhendriks.menu-calculator",
   4|   "name": "Omarchy Menu Calculator Plugin",
   5|   "version": "1.1.0",
   6|   "author": "Koen Hendriks",
   7|   "description": "Answers arithmetic typed into the Omarchy menu search field and copies the result on Enter",
   8|   "kinds": [
   9|     "menu",
  10|     "bar-widget"
  11|   ],
  12|   "keepLoaded": true,
  13|   "entryPoints": {
  14|     "menu": "Menu.qml",
  15|     "barWidget": "BarWidget.qml"
  16|   },
  17|   "barWidget": {
  18|     "displayName": "Omarchy Menu Calculator Plugin",
  19|     "description": "Launches the Omarchy menu",
  20|     "category": "Compositor",
  21|     "allowMultiple": false
  22|   },
  23|   "omarchy": {
  24|     "clonedFrom": "omarchy.menu"
  25|   }
  26| }
  27| 
```

### AppLibraryShim.qml
```
   1| import QtQuick
   2| import Quickshell
   3| import Quickshell.Io
   4| import qs.Commons
   5| import "file:///usr/share/omarchy/shell/services/AppSearch.js" as AppSearch
   6| 
   7| // Stand-in for the shell's own AppLibrary, for when the host does not hand one
   8| // over. Omarchy 4
```

## 10. dell_broken_verified:jcarcinogen/omarchy-rice-bar:r02417-cb6cdf060a [dell_broken_verified, changes_requested]

label: ```{"verdict": "changes_requested", "load": "broken", "findings": [{"category": "load:undefined-reference", "severity": "blocker", "file": "Service.qml", "line": 79, "finding": "Assigns to bar.foregroundAnimationEnabled which does not exist on stock Omarchy 4.x bar, causing runtime error."}, {"category": "load:undefined-reference", "severity": "blocker", "file": "Service.qml", "line": 82, "finding": "Assigns to bar.transparent which does not exist on stock Omarchy 4.x bar, causing runtime error."}]}```

provenance: `{"kind": "dell-sweep+checker-agree", "commit": "266b7dd133e3a86c04da5548d0844ed017d5d8de", "dell_run": "run8", "dell_job": "jcarcinogen__omarchy-rice-bar", "dell_label": "broken", "checker_pass": false, "issue_urls": null, "checker_report_regenerated_r3": false, "category_orig": ["load:property-not-found", "load:property-not-found"]}`

user (head): ```
## Checker report
(no Checker findings)

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "io.github.jcarcinogen.rice-bar",
   4|   "name": "Rice Bar",
   5|   "version": "0.4.2",
   6|   "author": "Scott Angel",
   7|   "license": "MIT",
   8|   "description": "Theme-aware visual presets for the stock Omarchy bar. Rice Bar keeps omarchy.bar, its official logo, widgets, panels, gestures, layout, and behavior intact while drawing passive chrome behind it.",
   9|   "kinds": [
  10|     "service",
  11|     "bar-widget"
  12|   ],
  13|   "entryPoints": {
  14|     "service": "Service.qml",
  15|     "barWidget": "BarWidget.qml"
  16|   },
  17|   "barWidget": {
  18|     "displayName": "Rice Bar",
  19|     "description": "Choose stock-preserving visual treatments for the Omarchy bar",
  20|     "category": "Appearance",
  21|     "allowMultiple": false,
  22|     "defaultSection": "right",
  23|     "defaults": {
  24|       "preset": "islands",
  25|       "opacity": 92,
  26|       "radius": 12,
  27|       "gap": 4,
  28|       "border": true
  29|     },
  30|     "schema": [
  31|       {
  32|         "key": "preset",
  33|         "type": "enum",
  34|         "label": "Style",
  35|         "options": [
  36|           "Omarchy",
  37|           "Islands",
  38|           "Pills",
  39|           "Material",
  40|           "Outline",
  41|           "Rail",
  42|           "Bracket",
  43|           "Glow",
  44|           "Pow
```

## 11. hancore_clean:mahdihedhli/omarchy-usage-grok-bar:0b3eb00a59 [hancore_clean_approve, approve]

label: ```{"verdict": "approve", "load": "works", "findings": []}```

provenance: `{"kind": "hancore-reviewed-clean", "repo": "mahdihedhli/omarchy-usage-grok-bar", "commit": "0b3eb00a59ac3d33ab03a627a9d7f171f3d68bf0", "approved": true, "listed": false, "weak_outcomes": ["stale"], "license": "see repo (public plugin)", "category_orig": []}`

user (head): ```
## Checker report
[USB-W07 warn experimental] Panel.qml: line 70: a variable is interpolated into a shell/Lua command string (`"bash", "-c", "printf %s " +`)
[USB-W04 warn experimental] install.sh: line 21: unsafe file operation `rm -rf "$PLUGIN_DIR"` (world-writable mode, forced symlink, predictable /tmp path, or rm -rf on an unchecked variable)

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "usage.grok",
   4|   "name": "Grok + Cursor Usage Widget",
   5|   "version": "1.2.0",
   6|   "author": "Mahdi Hedhli",
   7|   "license": "MIT",
   8|   "description": "One bar chip for all of it: SuperGrok Build, Chat, Imagine, and Voice, Cursor Pro monthly pools, and ngrok tunnels. Complements stock omarchy.agents instead of replacing it.",
   9|   "kinds": ["bar-widget"],
  10|   "activation": "on-demand",
  11|   "entryPoints": {
  12|     "barWidget": "BarWidget.qml"
  13|   },
  14|   "barWidget": {
  15|     "displayName": "Grok + Cursor Usage Widget",
  16|     "description": "One chip for SuperGrok channels, Cursor Pro, and ngrok tunnels. Left-click expands the popup; middle-click opens omarchy.agents; right-click launches the default agent.",
  17|     "category": "AI",
  18|     "aliases": ["grok-usage", "grok-limits", "ngrok"],
  19|     "allowMultiple": false,
  20|     "defaultSection": "right",
  21|     "defaults": {
  22|       "showCursorUsage": true,
  23|       "showNgrok": true
  24|     },
  25|     "schema": [
  26|    
```

## 12. version_history:dimdoremy/omaflameshot:061240d43b:broken [version_history, changes_requested]

label: ```{"verdict": "changes_requested", "load": "broken", "findings": [{"category": "runtime:logic-error", "severity": "blocker", "file": "Service.qml", "line": 74, "finding": "The `requestDeadlineAt` property uses a 32-bit `int` to store epoch milliseconds, which overflows in 2031 and causes active capture requests to appear instantly expired, breaking screenshot functionality."}]}```

provenance: `{"kind": "version-history-fix", "repo_url": "https://github.com/dimdoremy/omaflameshot", "repo": "dimdoremy/omaflameshot", "commit": "061240d43b9aef2f155d0879683527d244ec2053", "parent": "a694cc4ed26f280105023b2bd6f4376c7054d9ff", "date": "2026-09-02T20:46:25+08:00", "subject": "Fix instant request expiry: epoch-millis deadline overflows QML int, use real", "file": "Service.qml", "line": 74, "hist`

user (head): ```
## Checker report
[USB-W10 warn experimental] Service.qml: reads command output or a file with no size cap

## Plugin source
### manifest.json
```
   1| {
   2|   "schemaVersion": 1,
   3|   "id": "dimdoremy.omaflameshot",
   4|   "name": "omaflameshot",
   5|   "version": "1.3.0",
   6|   "author": "DimDoremy",
   7|   "license": "MIT",
   8|   "description": "Flameshot as the capture / annotate / pin tool: keeps every Flameshot window floating and pinned so screenshots pin on top of all workspaces like Snipaste, with omarchy-shell IPC actions ready for the menu or your own keybindings.",
   9|   "kinds": [
  10|     "service"
  11|   ],
  12|   "entryPoints": {
  13|     "service": "Service.qml"
  14|   }
  15| }
  16| 
```

### FlameshotModel.js
```
   1| // Pure helpers for the omaflameshot service.
   2| 
   3| // argv builders. Every helper runs as a direct argv array with an absolute
   4| // executable path — nothing is resolved through PATH and no shell is ever
   5| // spawned. Detachment is done by the caller via `setsid --fork`, so the
   6| // interactive Flameshot session is reparented and never tracked by us.
   7| 
   8| function readinessArgs(busctlBin) {
   9|   return [String(busctlBin), "--user", "--no-pager", "list"]
  10| }
  11| 
  12| function captureArgs(flameshotBin, args) {
  13|   var flags = Array.isArray(args) ? args : [String(args || "gui")]
  14|   return [String(flameshotBin)].concat(flags)
  15| }
  16| 
  17| function daemonArgs(flameshotBin
```
