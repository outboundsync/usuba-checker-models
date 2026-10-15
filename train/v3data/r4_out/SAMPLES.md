# Usuba v3-data-r4 — SAMPLES (prompt_v3)

Rows 1034 (train 896, val 138). 12 fresh random answers (seed 20261015+404; none appears in the r3 SAMPLES.md); each finding carries the automated check *cited line contains the described construct*. Results: {'pass': 10, 'n/a': 2}.

### `version_history:devasstated/omarchy-workspace-stash:e1342b2146:broken` — version-history broken, kind unbounded-input-resource
- source: version_history; tokens: 12459; files shown: 1; license MIT; https://github.com/devasstated/omarchy-workspace-stash @ e1342b2146
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] unbounded-input-resource** `Service.qml:572`: The `waitForEnd: true` setting on `StdioCollector` forces the process to buffer all stdout in memory before delivery, which causes memory exhaustion or application hangs when `hyprctl` outputs large amounts of data.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['waitForEnd: true', 'StdioCollector', 'hyprctl'])
```
   568|     id: moveCaptureProcess
   569|     command: ["hyprctl", "-j", "clients"]
   570|     stdout: StdioCollector {
   571|       id: moveCaptureOutput
>  572|       waitForEnd: true
   573|     }
   574|     onExited: function(exitCode) {
   575|       var clients = []
   576|       if (exitCode === 0) {
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "unsure",
 "findings": [
  {
   "category": "unbounded-input-resource",
   "severity": "blocker",
   "file": "Service.qml",
   "line": 572,
   "finding": "The `waitForEnd: true` setting on `StdioCollector` forces the process to buffer all stdout in memory before delivery, which causes memory exhaustion or application hangs when `hyprctl` outputs large amounts of data."
  }
 ]
}
```

### `version_history:datbuiquoc035/omasky:7309bac60b:broken` — version-history broken, kind rich-text-markup-injection
- source: version_history; tokens: 16433; files shown: 1; license MIT; https://github.com/datbuiquoc035/omasky @ 7309bac60b
- Checker report shown to the model:
```
[USB-A08 heuristic/medium] Panel.qml: line 130: assigns read-only `bar.centerHoverRevealSuppressed` - plugins get the read-only PluginBarApi facade, so this throws and aborts the rest of the function. Fix: call the setter instead, e.g. `bar.setCenterHoverRevealSuppressed(v)`
```
- **[blocker] rich-text-markup-injection** `BarWidget.qml:1224`: The code concatenates `ev.name` and `occ.start_local_label` directly into tooltip text without sanitization, allowing untrusted event data to inject arbitrary content or break the UI layout.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['ev.name', 'occ.start_local_label'])
```
  1220|         var ev = capped[i]
  1221|         var occ = EventsModel.nextOccurrence(ev)
  1222|         if (!occ) continue
  1223|         lines.push(
> 1224|           ev.name + " · " + occ.start_local_label
  1225|           + (ev.is_active ? " · ACTIVE" : "")
  1226|         )
  1227|       }
  1228|       if (root.dailyReset && root.setting("showDailyReset", true) !== false) {
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "unsure",
 "findings": [
  {
   "category": "rich-text-markup-injection",
   "severity": "blocker",
   "file": "BarWidget.qml",
   "line": 1224,
   "finding": "The code concatenates `ev.name` and `occ.start_local_label` directly into tooltip text without sanitization, allowing untrusted event data to inject arbitrary content or break the UI layout."
  }
 ]
}
```

### `version_history:linuxgameruk/omafinsight:1784e2c1c4:broken` — version-history broken, kind runtime-qml-api-compat
- source: version_history; tokens: 12822; files shown: 4; license MIT; https://github.com/linuxgameruk/omafinsight @ 1784e2c1c4
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] runtime-qml-api-compat** `AppWindow.qml:102`: The `icon` property on is invalid for `AppWindow` in Qt6, causing the application to fail at launch because this property was removed from the API.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['icon', 'AppWindow'])
```
    98|   readonly property color green: "#a6da95"
    99|   readonly property color inputBg: "#11131c"
   100| 
   101|   title: "OmaFinSight"
>  102|   icon: Qt.resolvedUrl("assets/logo.png")
   103|   color: cBg
   104|   width: 1160
   105|   height: 760
   106|   visible: true
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "unsure",
 "findings": [
  {
   "category": "runtime-qml-api-compat",
   "severity": "blocker",
   "file": "AppWindow.qml",
   "line": 102,
   "finding": "The `icon` property on is invalid for `AppWindow` in Qt6, causing the application to fail at launch because this property was removed from the API."
  }
 ]
}
```

### `version_history:ef-code/omarchy-mcp-manager:6288cd80ac:broken` — version-history broken, kind in-use:stale-or-wrong-display
- source: version_history; tokens: 11623; files shown: 1; license MIT; https://github.com/ef-code/omarchy-mcp-manager @ 6288cd80ac
- Checker report shown to the model:
```
[USB-W10 warn experimental] Controller.qml: reads command output or a file with no size cap
```
- **[blocker] in-use:stale-or-wrong-display** `Panel.qml:573`: The `ImportSheet` component is declared as a sibling within the main scrollable column, causing it to be clipped or hidden behind other content when `root.importOpen` becomes true. This layout placement prevents users from seeing or interacting with the import dialog because it does not overlay the interface as a proper sheet.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['ImportSheet', 'root.importOpen'])
```
   569|           ServerDetails { visible: !!root.selectedServer && !root.editorOpen && !root.importOpen; server: root.selectedServer; foreground: root.foreground }
   570| 
   571|           ServerEditor { visible: root.editorOpen; server: root.editingServer; sourceId: root.selectedSource ? String(root.selectedSource.sourceId) : ""; foreground: root
   572| 
>  573|           ImportSheet { visible: root.importOpen; foreground: root.foreground; onRegisterRequested: function(path, adapter, mode) { root.importOpen = false; backend.regis
   574| 
   575|         }
   576|       }
   577|     }
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "in-use:stale-or-wrong-display",
   "severity": "blocker",
   "file": "Panel.qml",
   "line": 573,
   "finding": "The `ImportSheet` component is declared as a sibling within the main scrollable column, causing it to be clipped or hidden behind other content when `root.importOpen` becomes true. This layout placement prevents users from seeing or interacting with the import dialog because it does not overlay the interface as a proper sheet."
  }
 ]
}
```

### `version_history:deadjoe/omarchy-mbpfan:948941ce8a:broken` — version-history broken, kind in-use:invalid-command-arg
- source: version_history; tokens: 10670; files shown: 6; license MIT; https://github.com/deadjoe/omarchy-mbpfan @ 948941ce8a
- Checker report shown to the model:
```
[USB-W05 heuristic/medium] Panel.qml: line 276: privileged/system-level action `"pkexec",`. Fix: keep the plugin unprivileged; document manual root steps in the README instead of escalating from the shell
```
- **[blocker] in-use:invalid-command-arg** `Panel.qml:243`: The `command` array uses the incorrect hardcoded namespace `joe.mbpfan` in the plugin path, causing the shell to fail locating the `mbpfan-status` executable and preventing the panel from displaying temperature or fan data.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['command', 'joe.mbpfan', 'mbpfan-status'])
```
   239|     onTriggered: root.refreshStatus()
   240|   }
   241|   Process {
   242|     id: statusProc
>  243|     command: [Quickshell.env("HOME") + "/.config/omarchy/plugins/joe.mbpfan/bin/mbpfan-status"]
   244|     stdout: StdioCollector {
   245|       waitForEnd: true
   246|       onStreamFinished: {
   247|         var parts = String(text).trim().split(/\s+/)
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "in-use:invalid-command-arg",
   "severity": "blocker",
   "file": "Panel.qml",
   "line": 243,
   "finding": "The `command` array uses the incorrect hardcoded namespace `joe.mbpfan` in the plugin path, causing the shell to fail locating the `mbpfan-status` executable and preventing the panel from displaying temperature or fan data."
  }
 ]
}
```

### `version_history:gustavohariel/omarchy-hubstaff:7fb70b7fa9:broken` — version-history broken, kind in-use:missing-binary
- source: version_history; tokens: 10487; files shown: 2; license MIT; https://github.com/gustavohariel/omarchy-hubstaff @ 7fb70b7fa9
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] in-use:missing-binary** `Service.qml:567`: The expression `out.indexOf("cli") >= 0` incorrectly validates installation by searching for a generic substring instead of verifying the specific client GUI binary path, causing false positives when unrelated text appears in the output.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['out.indexOf("cli") >= 0'])
```
   563|     command: []
   564|     stdout: StdioCollector { id: envStdout; waitForEnd: true }
   565|     onExited: {
   566|       var out = String(envStdout.text || "")
>  567|       root.cliInstalled = out.indexOf("cli") >= 0
   568|       root.hyprctlAvailable = out.indexOf("hypr") >= 0
   569|       root.envChecked = true
   570|       if (root.cliInstalled) {
   571|         root.guardWindow()
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "in-use:missing-binary",
   "severity": "blocker",
   "file": "Service.qml",
   "line": 567,
   "finding": "The expression `out.indexOf(\"cli\") >= 0` incorrectly validates installation by searching for a generic substring instead of verifying the specific client GUI binary path, causing false positives when unrelated text appears in the output."
  }
 ]
}
```

### `version_history:tobiasz-p/next-event:6a768aa6cf:broken` — version-history broken, kind secrets-credentials
- source: version_history; tokens: 11010; files shown: 5; license MIT; https://github.com/tobiasz-p/next-event @ 6a768aa6cf
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] secrets-credentials** `BarWidget.qml:82`: Assigning `root.icsUrl` directly to `fetchProc.command` exposes the URL in the system process table, allowing other users to view sensitive calendar endpoints via process inspection tools.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['root.icsUrl', 'fetchProc.command'])
```
    78|   }
    79| 
    80|   function fetchCalendar() {
    81|     if (!root.configured || fetchProc.running) return
>   82|     fetchProc.command = ["curl", "-fsSL", "--max-time", "15", root.icsUrl]
    83|     fetchProc.running = true
    84|   }
    85| 
    86|   function refresh() {
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "unsure",
 "findings": [
  {
   "category": "secrets-credentials",
   "severity": "blocker",
   "file": "BarWidget.qml",
   "line": 82,
   "finding": "Assigning `root.icsUrl` directly to `fetchProc.command` exposes the URL in the system process table, allowing other users to view sensitive calendar endpoints via process inspection tools."
  }
 ]
}
```

### `jankeesvw-history:omarchy-notification-center:0c4e475190:broken` — jankeesvw-history broken
- source: jankeesvw-history; tokens: 23984; files shown: 6
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] in-use:stale-or-wrong-display** `bin/notification-center:143`: The `have_key` check causes `ingest_file` to return silently on multi-screen setups, preventing the second screen's panel from receiving the notification entry.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['have_key', 'ingest_file'])
```
   139| ingest_file() {
   140|   local file=$1 key entry app_icon image_src exec_src icon_copy image_copy preview_src preview_copy
   141|   key=$(basename -- "$file"); key=${key%.json}
   142|   [[ -n $key ]] || return 0
>  143|   have_key "$key" && return 0
   144|   [[ -s $file ]] || return 0
   145| 
   146|   # A file caught mid-write parses as nothing; it will be caught again on the
   147|   # move into history, or by the next sync.
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "in-use:stale-or-wrong-display",
   "severity": "blocker",
   "file": "bin/notification-center",
   "line": 143,
   "finding": "The `have_key` check causes `ingest_file` to return silently on multi-screen setups, preventing the second screen's panel from receiving the notification entry."
  }
 ]
}
```

### `hancore_concrete:jburchel/omarchy-jarvis:884b5c8a76` — HANCORE broken
- source: hancore_concrete; tokens: 11611; files shown: 7
- Checker report shown to the model:
```
[USB-W10 warn experimental] BarWidget.qml: reads command output or a file with no size cap
```
- **[blocker] remote-code-pinning** `bin/jarvis:44`: `bin/jarvis` installs `pip`, `edge-tts`, and `piper-tts` without pinned versions or hashes; `bin/jarvis` does the same for `openwakeword`.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['bin/jarvis', 'pip', 'edge-tts', 'piper-tts'])
```
    40| case "${1:-status}" in
    41| setup)
    42|   mkdir -p "$JARVIS_HOME" "$JARVIS_VOICES" "$JARVIS_CONFIG_DIR"
    43|   [ -x "$JARVIS_VENV/bin/python" ] || python3 -m venv "$JARVIS_VENV"
>   44|   "$JARVIS_VENV/bin/pip" install -q --upgrade pip edge-tts piper-tts
    45|   if [ ! -f "$JARVIS_VOICES/$JARVIS_PIPER_VOICE.onnx" ]; then
    46|     (cd "$JARVIS_VOICES" && "$JARVIS_VENV/bin/python" -m piper.download_voices "$JARVIS_PIPER_VOICE")
    47|   fi
    48|   if [ ! -f "$JARVIS_CONFIG_DIR/config.sh" ]; then
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "unsure",
 "findings": [
  {
   "category": "remote-code-pinning",
   "severity": "blocker",
   "file": "bin/jarvis",
   "line": 44,
   "finding": "`bin/jarvis` installs `pip`, `edge-tts`, and `piper-tts` without pinned versions or hashes; `bin/jarvis` does the same for `openwakeword`."
  }
 ]
}
```

### `dell_broken_verified:<id-withheld>` — Dell-derived broken
- source: dell_broken_verified; tokens: 22129; files shown: 7
- Checker report shown to the model:
```
[USB-W01 warn experimental] install.sh: runs `confirm`, which is not part of a stock Omarchy install and is not listed as a dependency in the README/manifest
[USB-W01 warn experimental] uninstall.sh: runs `info`, which is not part of a stock Omarchy install and is not listed as a dependency in the README/manifest
```
- **[blocker] load:missing-import** `AppPicker.qml:7`: Imports `qs.services`, which is not a valid Omarchy module (only `qs.Commons` and `qs.Ui` exist on stock Omarchy), so the QML file fails to load.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['qs.services', 'qs.Commons', 'qs.Ui'])
```
     3| import Quickshell.Wayland
     4| import QtQuick
     5| import qs.Commons
     6| import qs.Ui
>    7| import qs.services
     8| 
     9| // App Picker: a full-screen (or centered, windowed) grid of every app the
    10| // Omarchy Apps menu shows. Apps can be sorted A-Z / Z-A, filtered by typing,
    11| // and ranked as favorites by dragging them into the Favorites box.
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "load:missing-import",
   "severity": "blocker",
   "file": "AppPicker.qml",
   "line": 7,
   "finding": "Imports `qs.services`, which is not a valid Omarchy module (only `qs.Commons` and `qs.Ui` exist on stock Omarchy), so the QML file fails to load."
  }
 ]
}
```

### `version_history:duketopceo/omarchy-fan:c730a3d505:fixed` — APPROVE: post-fix version (Checker clean + model check)
- source: version_history; tokens: 9240; files shown: 4; license MIT; https://github.com/duketopceo/omarchy-fan @ c730a3d505
- Checker report shown to the model:
```
(no Checker findings)
```
- no findings (clean approve)
- **full answer taught:**
```json
{
 "verdict": "approve",
 "load": "works",
 "findings": []
}
```

### `dell_works_verified:<id-withheld>` — APPROVE: Dell-verified working plugin
- source: dell_works_verified; tokens: 16450; files shown: 9
- Checker report shown to the model:
```
(no Checker findings)
```
- no findings (clean approve)
- **full answer taught:**
```json
{
 "verdict": "approve",
 "load": "works",
 "findings": []
}
```
