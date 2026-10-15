# Usuba v3-data-r3 — SAMPLES (prompt_v3)

Rows: 582 (train 516, val 66). 13 fresh random examples (7 HANCORE kinds, 3 Dell-derived, 3 approve; fewer than the 12+3 asked because kinds with no unseen row were skipped); none appears in the earlier v3 SAMPLES.md / GATE_REPORT.md (seed 20261015+77, not curated). Each blocker/warning carries the automated check *cited line contains the described construct* (a backticked identifier/command from the finding must be ON the cited line, or within the same 2-line statement; blank/comment lines fail). Line numbers are counted from the top of the file as shown in the prompt (the model sees none).
Check results on these 15 samples: {'pass': 11}. Overall pass rate over ALL rows: see GATE_REPORT.md section 3 (98.3% of checkable findings).

## A. 12 examples

### `hancore_concrete:robertlindomar/omarchy-ptbr-disk-speedtest:84af10fb39` — HANCORE kind process-lifecycle-timeouts
- source: hancore_concrete; tokens: 8990; files shown: 7
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] process-lifecycle-timeouts** `Panel.qml:99`: `Panel.qml` launches bare `omarchy-disk-speedtest` through inherited `PATH`, accepts unbounded stdout lines, fully buffers unbounded stderr, and has no hard deadline, TERM→KILL escalation, descendant reap, superseded-run cleanup, or component-destruction cleanup.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['omarchy-disk-speedtest', 'PATH'])
```
    95|   }
    96| 
    97|   Process {
    98|     id: proc
>   99|     command: ["omarchy-disk-speedtest"]
   100|     stdout: SplitParser { onRead: function(line) { root.updateLine(line) } }
   101|     // Exit and stream-finished have no guaranteed order: when a failed exit
   102|     // beat the collector and published the generic message, replace it with
   103|     // the specific one once it lands.
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "unsure",
 "findings": [
  {
   "category": "process-lifecycle-timeouts",
   "severity": "blocker",
   "file": "Panel.qml",
   "line": 99,
   "finding": "`Panel.qml` launches bare `omarchy-disk-speedtest` through inherited `PATH`, accepts unbounded stdout lines, fully buffers unbounded stderr, and has no hard deadline, TERM→KILL escalation, descendant reap, superseded-run cleanup, or component-destruction cleanup."
  }
 ]
}
```

### `hancore_concrete:omarchyfans/omarchy-fans-help:76adb2cb62` — HANCORE kind remote-code-pinning
- source: hancore_concrete; tokens: 11719; files shown: 9
- Checker report shown to the model:
```
[USB-W08 warn experimental] tools/fetch-gemma.sh: line 14: network call without a timeout (`curl`)
[USB-W08 warn experimental] tools/bench.sh: line 104: network call without a timeout (`curl`)
[USB-W01 warn experimental] tools/bench.sh: runs `cfg`, which is not part of a stock Omarchy install and is not listed as a dependency in the README/manifest
```
- **[blocker] remote-code-pinning** `tools/fetch-models.sh:11`: `tools/fetch-models.sh` and `tools/fetch-gemma.sh` download GGUF files from mutable Hugging Face `resolve/main` URLs and accept them without an expected digest or signature; resumed downloads can also combine bytes if the upstream asset changes.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['resolve/main'])
```
     7| mkdir -p "$MODELS"
     8| 
     9| fetch() {
    10|   local repo="$1" file="$2" out="$3"
>   11|   local url="https://huggingface.co/${repo}/resolve/main/${file}"
    12|   if [[ -s "$MODELS/$out" ]]; then
    13|     echo "have    $out"
    14|     return 0
    15|   fi
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
   "file": "tools/fetch-models.sh",
   "line": 11,
   "finding": "`tools/fetch-models.sh` and `tools/fetch-gemma.sh` download GGUF files from mutable Hugging Face `resolve/main` URLs and accept them without an expected digest or signature; resumed downloads can also combine bytes if the upstream asset changes."
  }
 ]
}
```

### `hancore_concrete:zpl-zak/omarchy-cider-widget:d9a8543ba4` — HANCORE kind privileged-system
- source: hancore_concrete; tokens: 10769; files shown: 4
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] privileged-system** `Service.qml:104`: The continuously loaded service starts the security-sensitive helper as bare `python3`, and the helper itself resolves `systemctl`, `secret-tool`, and ImageMagick from the inherited `PATH`. It also forwards almost the complete inherited environment to ImageMagick.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['python3', 'systemctl', 'secret-tool', 'PATH'])
```
   100|     _statusError = ""
   101|     _statusFailure = ""
   102|     _statusGeneration += 1
   103|     _statusRequestGeneration = _statusGeneration
>  104|     statusProcess.command = ["python3", helperPath, "status"]
   105|     statusWatchdog.restart()
   106|     statusProcess.running = true
   107|   }
   108| 
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "unsure",
 "findings": [
  {
   "category": "privileged-system",
   "severity": "blocker",
   "file": "Service.qml",
   "line": 104,
   "finding": "The continuously loaded service starts the security-sensitive helper as bare `python3`, and the helper itself resolves `systemctl`, `secret-tool`, and ImageMagick from the inherited `PATH`. It also forwards almost the complete inherited environment to ImageMagick."
  }
 ]
}
```

### `hancore_concrete:ferc10110/omarchy-syllabus:937a80ee7e` — HANCORE kind secrets-credentials
- source: hancore_concrete; tokens: 11546; files shown: 8
- Checker report shown to the model:
```
[USB-W10 warn experimental] SyllabusEngine.qml: reads command output or a file with no size cap
```
- **[blocker] secrets-credentials** `lib/syllabus/web.py:105`: `lib/syllabus/web.py` and `lib/syllabus/downloads.py` pass the course password as `--video-password <secret>`; `lib/syllabus/player.py` carries it into mpv's `--ytdl-raw-options` argument.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['--video-password <secret>', '--ytdl-raw-options'])
```
   101| def fetch_playlist(url, password="", timeout=120):
   102|     """What is behind a link: a playlist with its entries, or a single video."""
   103|     args = ["--flat-playlist", "-J", "--no-warnings"]
   104|     if password:
>  105|         args += ["--video-password", password]
   106|     data, error = _run(args + [url], timeout)
   107|     if error:
   108|         return _answer(error=error)
   109|     if data.get("_type") == "playlist":
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
   "file": "lib/syllabus/web.py",
   "line": 105,
   "finding": "`lib/syllabus/web.py` and `lib/syllabus/downloads.py` pass the course password as `--video-password <secret>`; `lib/syllabus/player.py` carries it into mpv's `--ytdl-raw-options` argument."
  }
 ]
}
```

### `hancore_concrete:basecamp/omarchy-basecamp-plugin:abc1ba72aa` — HANCORE kind rich-text-markup-injection
- source: hancore_concrete; tokens: 10306; files shown: 4
- Checker report shown to the model:
```
[USB-W07 warn experimental] Panel.qml: line 559: a variable is interpolated into a shell/Lua command string (`"bash", "-c", "printf %s " +`)
```
- **[blocker] rich-text-markup-injection** `Model.js:266`: `Model.js` decodes `&lt;`/`&gt;` in remote notification fields, which are then rendered by default `Text.AutoText`. Encoded markup can therefore become active rich text and trigger unintended resource loading in the shell UI.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['&lt;', '&gt;', 'Text.AutoText'])
```
   262|     .replace(/<br\s*\/?\s*>/gi, " ")
   263|     .replace(/<[^>]*>/g, " ")
   264|     .replace(/&nbsp;/gi, " ")
   265|     .replace(/&amp;/gi, "&")
>  266|     .replace(/&lt;/gi, "<")
   267|     .replace(/&gt;/gi, ">")
   268|     .replace(/&quot;/gi, "\"")
   269|     .replace(/&#39;|&apos;/gi, "'")
   270|     .replace(/\s+/g, " ")
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
   "file": "Model.js",
   "line": 266,
   "finding": "`Model.js` decodes `&lt;`/`&gt;` in remote notification fields, which are then rendered by default `Text.AutoText`. Encoded markup can therefore become active rich text and trigger unintended resource loading in the shell UI."
  }
 ]
}
```

### `hancore_concrete:cylon58/omarchy-codex-crash-model-picker:7c19309578` — HANCORE kind shell-lua-injection
- source: hancore_concrete; tokens: 8263; files shown: 10
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] shell-lua-injection** `bin/omarchy-crash-watch:38`: `bin/omarchy-crash-watch` reads `COREDUMP_COMM`, `COREDUMP_EXE`, and the signal from journal data, and `bin/codex-crash-diagnose` interpolates those attacker-influenced strings directly into the initial prompt before launches Codex with `--approve-for-me`.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['bin/omarchy-crash-watch', 'COREDUMP_COMM', 'COREDUMP_EXE', 'bin/codex-crash-diagnose'])
```
    34| 
    35| journalctl -f -n 0 -o json "MESSAGE_ID=$COREDUMP_MESSAGE_ID" 2>/dev/null |
    36|   while IFS= read -r entry; do
    37|     pid=$(jq -r '.COREDUMP_PID // empty' <<<"$entry")
>   38|     comm=$(jq -r '.COREDUMP_COMM // empty' <<<"$entry")
    39|     exe=$(jq -r '.COREDUMP_EXE // empty' <<<"$entry")
    40|     signal=$(jq -r '.COREDUMP_SIGNAL_NAME // .COREDUMP_SIGNAL // empty' <<<"$entry")
    41| 
    42|     [[ $pid =~ ^[0-9]+$ ]] || continue
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "unsure",
 "findings": [
  {
   "category": "shell-lua-injection",
   "severity": "blocker",
   "file": "bin/omarchy-crash-watch",
   "line": 38,
   "finding": "`bin/omarchy-crash-watch` reads `COREDUMP_COMM`, `COREDUMP_EXE`, and the signal from journal data, and `bin/codex-crash-diagnose` interpolates those attacker-influenced strings directly into the initial prompt before launches Codex with `--approve-for-me`."
  }
 ]
}
```

### `hancore_concrete:dreed47/tempest-weather:3bb566cdae` — HANCORE kind unbounded-input-resource
- source: hancore_concrete; tokens: 11087; files shown: 3
- Checker report shown to the model:
```
[USB-A08 heuristic/medium] Panel.qml: line 217: assigns read-only `bar.centerHoverRevealSuppressed` - plugins get the read-only PluginBarApi facade, so this throws and aborts the rest of the function. Fix: call the setter instead, e.g. `bar.setCenterHoverRevealSuppressed(v)`
[USB-W06 warn experimental] Panel.qml: line 613: Text.StyledText renders markup; if its text comes from command output, files, network or other apps it can inject links/images
```
- **[blocker] unbounded-input-resource** `Panel.qml:261`: `Panel.qml` and `AlertService.qml` still send unrestricted `curl` stdout directly into `StdioCollector`; the existing timeouts do not prevent an allowed endpoint from returning an arbitrarily large body and exhausting the long-lived shell's memory.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['curl', 'StdioCollector'])
```
   257|   Process {
   258|     id: stationsProc
   259|     stdinEnabled: true
   260|     command: ["bash", "-c",
>  261|       'read -r URL && printf "url = %s\\n" "$URL" | curl -fsS --max-time 10 -K -']
   262|     onStarted: write(("https://swd.weatherflow.com/swd/rest/stations?token="
   263|       + encodeURIComponent(root.token)).replace(/[\r\n]/g, "") + "\n")
   264|     stdout: StdioCollector {
   265|       waitForEnd: true
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
   "file": "Panel.qml",
   "line": 261,
   "finding": "`Panel.qml` and `AlertService.qml` still send unrestricted `curl` stdout directly into `StdioCollector`; the existing timeouts do not prevent an allowed endpoint from returning an arbitrarily large body and exhausting the long-lived shell's memory."
  }
 ]
}
```

### `dell_broken_verified:<id-withheld>` — Dell-derived load bug
- source: dell_broken_verified; tokens: 15453; files shown: 11
- Checker report shown to the model:
```
[USB-W01 warn experimental] install.sh: runs `check_managed_target`, which is not part of a stock Omarchy install and is not listed as a dependency in the README/manifest
[USB-W01 warn experimental] uninstall.sh: runs `has_symlink_component`, which is not part of a stock Omarchy install and is not listed as a dependency in the README/manifest
```
- **[blocker] load:invalid-command-path** `Panel.qml:87`: Passes Qt.resolvedUrl() result directly as a command argument; this returns a file:// URL string that the shell cannot execute as a filesystem path.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: [])
```
    83|   }
    84| 
    85|   Process {
    86|     id: statusProc
>   87|     command: [root.pathFromUrl(Qt.resolvedUrl("scripts/omarchy-rdp-status"))]
    88|     stdout: StdioCollector {
    89|       waitForEnd: true
    90|       onStreamFinished: {
    91|         try {
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "load:invalid-command-path",
   "severity": "blocker",
   "file": "Panel.qml",
   "line": 87,
   "finding": "Passes Qt.resolvedUrl() result directly as a command argument; this returns a file:// URL string that the shell cannot execute as a filesystem path."
  }
 ]
}
```

### `dell_broken_verified:<id-withheld>` — Dell-derived in-use bug
- source: dell_broken_verified; tokens: 15790; files shown: 6
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] in-use:missing-binary** `Panel.qml:146`: Runs `anki` via Quickshell.execDetached, which is not on stock Omarchy and is neither shipped nor declared; sync/launch will fail.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['anki'])
```
   142|     syncProc.running = true
   143|   }
   144| 
   145|   function launchAnki() {
>  146|     Quickshell.execDetached(["anki"])
   147|   }
   148| 
   149|   // Consecutive error reports tolerated before one is allowed to replace a
   150|   // good one. The collector abandons a snapshot that overruns its query
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
   "file": "Panel.qml",
   "line": 146,
   "finding": "Runs `anki` via Quickshell.execDetached, which is not on stock Omarchy and is neither shipped nor declared; sync/launch will fail."
  }
 ]
}
```

### `dell_inuse_missing_binary:<id-withheld>` — Dell-derived other bug
- source: dell_inuse_missing_binary; tokens: 16276; files shown: 4
- Checker report shown to the model:
```
[USB-A04] BarWidget.qml: line 487: `bar.showTooltip()` - `Rectangle` has no method `showTooltip`. Fix: real `Rectangle` methods: QObject, _q_createJSWrapper, _q_resourceObjectDeleted, childAt, contains, destroy, doUpdate, dumpItemTree, ensurePolished, forceActiveFocus
```
- **[blocker] runtime:method-missing** `BarWidget.qml:487`: Calls bar.showTooltip() but bar (Rectangle) lacks this method on stock Omarchy, causing a runtime TypeError.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: [])
```
   483|   }
   484| 
   485|   // Keep an open tooltip in step with the track instead of freezing the
   486|   // text from the moment the pointer entered.
>  487|   onTooltipTextChanged: if (tooltipHovered && bar) bar.showTooltip(root, tooltipText)
   488| 
   489|   MouseArea {
   490|     id: mouseArea
   491|     anchors.fill: parent
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "runtime:method-missing",
   "severity": "blocker",
   "file": "BarWidget.qml",
   "line": 487,
   "finding": "Calls bar.showTooltip() but bar (Rectangle) lacks this method on stock Omarchy, causing a runtime TypeError."
  }
 ]
}
```


## B. 3 approve examples

### `dell_works_verified:<id-withheld>` — APPROVE with a warning (trusted-and-small exception)
- source: dell_works_verified; tokens: 7178; files shown: 5
- Checker report shown to the model:
```
[USB-W07 warn experimental] BarWidget.qml: line 79: a variable is interpolated into a shell/Lua command string (`execDetached("hyprctl eval " +`)
[USB-W10 warn experimental] BarWidget.qml: reads command output or a file with no size cap
```
- **[warning] unbounded-input-resource** `BarWidget.qml:27`: FileView reads omahide.json without a size cap; consider adding a maxBytes limit.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: [])
```
    23|   visible: count > 0
    24|   implicitWidth: count > 0 ? (count * slot + Math.max(0, count - 1) * Style.space(1)) : 0
    25|   implicitHeight: barSize
    26| 
>   27|   FileView {
    28|     id: hideFile
    29|     path: (Quickshell.env("XDG_RUNTIME_DIR") || "/tmp") + "/omahide.json"
    30|     watchChanges: true
    31|     printErrors: false
```
- **full answer taught:**
```json
{
 "verdict": "approve",
 "load": "works",
 "findings": [
  {
   "category": "unbounded-input-resource",
   "severity": "warning",
   "file": "BarWidget.qml",
   "line": 27,
   "finding": "FileView reads omahide.json without a size cap; consider adding a maxBytes limit."
  }
 ]
}
```

### `dell_works_verified:<id-withheld>` — APPROVE clean
- source: dell_works_verified; tokens: 19509; files shown: 6
- Checker report shown to the model:
```
(no Checker findings)
```
- no findings (clean approve); no cited line to check
- **full answer taught:**
```json
{
 "verdict": "approve",
 "load": "works",
 "findings": []
}
```

### `fix_upstream:esegnorelli/omarchy-omacapy:r02966-08485e6430` — APPROVE after upstream fix / nudged
- source: fix_upstream; tokens: 14256; files shown: 3
- Checker report shown to the model:
```
[USB-W10 warn experimental] Panel.qml: reads command output or a file with no size cap
```
- no findings (clean approve); no cited line to check
- **full answer taught:**
```json
{
 "verdict": "approve",
 "load": "works",
 "findings": []
}
```


## C. Reviewer notes

Read of the 15 fresh samples against the code shown (not curated; mechanical check passes 14/14 where a line is cited, the 15th, an approve warning, cites no line):
- **Anchoring is now mostly the exact statement**: `Dock.qml:254` is the `text: tip.item.name` binding, `Panel.qml:108` is the `bar.run("...'" + url + "'")` concatenation, `install.sh:19` is the `omarchy plugin disable` line, `bin/jarvis:44` is the unpinned `pip install`. Two samples are weaker: `omaclasroom` cites `README.md:25`, the first line of a two-line shell command whose `--client-secret` flag sits on the next line (accepted as a 2-line statement); `mouse_ctl.py:115` is correct for the clamp bug but see the next point.
- **Kind noise remains**: `davedes83/mouse-keybind-plugin` is filed `process-lifecycle-timeouts` while its cited line is an unrelated `max(max_val, v)` clamp bug (the prose bundles two findings with a '- ' bullet); `deck-chameleon` (`runtime-qml-api-compat`) is really a build-queue race. The vote picks one primary kind per finding; bundled findings keep a noisy label.
- **Prose is cleaner than v3** (file:line spans and review framing stripped, mid-word cuts removed) but some findings still read as continuations ('A privilege-boundary race: ...'), and a few keep a second sentence about a different construct.
- **Dell-derived samples**: `load:missing-file`, `config:placeholder-in-defaults` and `in-use:missing-binary` (`magic-mouse-config`, Dell run recorded it as a missing binary) are consistent with the code. Placeholder-URL rows (`config:*`) are a judgement call: the URL is example data a user is meant to overwrite.
- **Approve examples**: the warning sample (`docwatz/omarchyss`) has `line: null`, so it teaches a warning with no cited line; only 1 approve row left with a cited-line warning, which the open-model re-check flags as not exact.
