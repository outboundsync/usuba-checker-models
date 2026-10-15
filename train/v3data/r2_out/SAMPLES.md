# Usuba v3-data-r2 — SAMPLES (prompt_v3)

Rows: 543 (train 523, val 20). 12 fresh random examples (9 HANCORE kinds, 3 Dell-derived) + 3 approve; none appears in the earlier v3 SAMPLES.md / GATE_REPORT.md (seed 20261015+77, not curated). Each blocker/warning carries the automated check *cited line contains the described construct* (a backticked identifier/command from the finding must be ON the cited line, or within the same 2-line statement; blank/comment lines fail). Line numbers are counted from the top of the file as shown in the prompt (the model sees none).
Check results on these 15 samples: {'pass': 12, 'other': 1}. Overall pass rate over ALL rows: see GATE_REPORT.md section 3 (100.0% of checkable findings).

## A. 12 examples

### `hancore_concrete:davedes83/mouse-keybind-plugin:221096118f` — HANCORE kind process-lifecycle-timeouts
- source: hancore_concrete; tokens: 9687; files shown: 5
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] process-lifecycle-timeouts** `mouse_ctl.py:115`: The integer clamp in `mouse_ctl.py` uses `max(max_val, v)` where an upper-bound `min(max_val, v)` is required, forcing values to or above the maximum. - Subprocess calls and captured output need hard timeouts, retained-byte limits, and process-group cleanup.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['max(max_val, v)', 'min(max_val, v)'])
```
   111| 
   112| def validate_int(val, default: int, min_val: int, max_val: int) -> int:
   113|     try:
   114|         v = int(val)
>  115|         return max(min_val, max(max_val, v))
   116|     except (TypeError, ValueError, OverflowError):
   117|         return default
   118| 
   119| def validate_bool(val, default: bool) -> bool:
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
   "file": "mouse_ctl.py",
   "line": 115,
   "finding": "The integer clamp in `mouse_ctl.py` uses `max(max_val, v)` where an upper-bound `min(max_val, v)` is required, forcing values to or above the maximum. - Subprocess calls and captured output need hard timeouts, retained-byte limits, and process-group cleanup."
  }
 ]
}
```

### `hancore_concrete:jburchel/omarchy-jarvis:884b5c8a76` — HANCORE kind remote-code-pinning
- source: hancore_concrete; tokens: 10711; files shown: 7
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

### `hancore_concrete:imargorsi/omarchy-hotspot:c97bb92aa8` — HANCORE kind privileged-system
- source: hancore_concrete; tokens: 9937; files shown: 7
- Checker report shown to the model:
```
[USB-A08 heuristic/medium] Panel.qml: line 75: assigns read-only `bar.centerHoverRevealSuppressed` - plugins get the read-only PluginBarApi facade, so this throws and aborts the rest of the function. Fix: call the setter instead, e.g. `bar.setCenterHoverRevealSuppressed(v)`
[USB-W05 heuristic/medium] Service.qml: line 96: privileged/system-level action `"pkexec",`. Fix: keep the plugin unprivileged; document manual root steps in the README instead of escalating from the shell
[USB-W05 heuristic/
```
- **[blocker] privileged-system** `install.sh:25`: A privilege-boundary race: the script runs `sudo install` with the helper and polkit policy taken directly from the user-writable plugin checkout.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['sudo install'])
```
    21|         echo "Skipping. The hotspot will fail to start without it." >&2
    22|     fi
    23| fi
    24| 
>   25| sudo install -m 755 "$DIR/bin/share-internet" /usr/local/bin/share-internet
    26| sudo install -m 644 "$DIR/io.github.imargorsi.hotspot.policy" \
    27|     /usr/share/polkit-1/actions/io.github.imargorsi.hotspot.policy
    28| 
    29| echo
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
   "file": "install.sh",
   "line": 25,
   "finding": "A privilege-boundary race: the script runs `sudo install` with the helper and polkit policy taken directly from the user-writable plugin checkout."
  }
 ]
}
```

### `hancore_concrete:tngyema/omaclasroom:0a04c604a9` — HANCORE kind secrets-credentials
- source: hancore_concrete; tokens: 8712; files shown: 6
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] secrets-credentials** `README.md:25`: `README.md` instructs users to pass the OAuth client secret on the command line, and `omaclasroom` accepts it as `--client-secret`, exposing the credential in process metadata and shell history. Read it from protected stdin or another non-argv channel.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['omaclasroom', '--client-secret'])
```
    21| 
    22| Then authorize with Google:
    23| 
    24| ```sh
>   25| ~/.config/omarchy/plugins/io.github.omaclasroom/omaclasroom set-token \
    26|   --client-id YOUR_CLIENT_ID \
    27|   --client-secret YOUR_CLIENT_SECRET
    28| ```
    29| 
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
   "file": "README.md",
   "line": 25,
   "finding": "`README.md` instructs users to pass the OAuth client secret on the command line, and `omaclasroom` accepts it as `--client-secret`, exposing the credential in process metadata and shell history. Read it from protected stdin or another non-argv channel."
  }
 ]
}
```

### `hancore_concrete:bit-casper/duck:d8b8bd4ada` — HANCORE kind rich-text-markup-injection
- source: hancore_concrete; tokens: 9598; files shown: 5
- Checker report shown to the model:
```
[USB-B01] uninstall.sh: script string runs `hypr_remove_block`, which is not installed on the Dell's Omarchy 4.0.4 (system_bins) and not shipped by the plugin. Fix: use a binary that exists on stock Omarchy (see dell_env/system_bins.txt), ship a script for it, or document `hypr_remove_block` as a dependency in README.md
[USB-B01] uninstall.sh: script string runs `menu_remove_block`, which is not installed on the Dell's Omarchy 4.0.4 (system_bins) and not shipped by the plugin. Fix: use a binary 
```
- **[blocker] rich-text-markup-injection** `Dock.qml:254`: `Dock.qml` renders `tip.item.name` in a QML `Text` item without `textFormat: Text.PlainText`.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['tip.item.name', 'Text', 'textFormat: Text.PlainText'])
```
   250| 
   251|                     Text {
   252|                         id: tipLabel
   253|                         anchors.centerIn: parent
>  254|                         text: tip.item ? tip.item.name : ""
   255|                         color: Color.tooltip.text
   256|                         font.family: Style.font.family
   257|                         font.pixelSize: Style.font.body
   258|                     }
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
   "file": "Dock.qml",
   "line": 254,
   "finding": "`Dock.qml` renders `tip.item.name` in a QML `Text` item without `textFormat: Text.PlainText`."
  }
 ]
}
```

### `hancore_concrete:alxwolfenstein97/omamenu:538c5066a3` — HANCORE kind user-config-modification
- source: hancore_concrete; tokens: 10454; files shown: 7
- Checker report shown to the model:
```
[USB-F01] Menu.qml: references helper script `/shell/services/hidden-entries.sh`, which the plugin does not ship. Fix: ship `/shell/services/hidden-entries.sh` in the plugin (e.g. bin/hidden-entries.sh) or inline the command
[USB-W07 warn experimental] Menu.qml: line 214: a variable is interpolated into a shell/Lua command string (`"bash", "-c", ": > " +`)
[USB-W01 warn experimental] check.sh: runs `bad`, which is not part of a stock Omarchy install and is not listed as a dependency in the READM
```
- **[blocker] user-config-modification** `install.sh:19`: `install.sh` silently runs `omarchy plugin disable alex.menu` before enabling OmaMenu. `alex.menu` can be a user's separate local plugin, and the README's install path does not disclose disabling it.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['omarchy plugin disable alex.menu', 'alex.menu'])
```
    15| omarchy-shell -q shell rescanPlugins >/dev/null 2>&1 || true
    16| 
    17| if command -v omarchy >/dev/null 2>&1; then
    18|   # Disabling a leftover local clone frees the bar slot / cloneSourceRestores.
>   19|   omarchy plugin disable alex.menu >/dev/null 2>&1 || true
    20|   omarchy plugin enable "$plugin_id" >/dev/null 2>&1 || true
    21| fi
    22| 
    23| omarchy-shell -q shell rescanPlugins >/dev/null 2>&1 || true
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "unsure",
 "findings": [
  {
   "category": "user-config-modification",
   "severity": "blocker",
   "file": "install.sh",
   "line": 19,
   "finding": "`install.sh` silently runs `omarchy plugin disable alex.menu` before enabling OmaMenu. `alex.menu` can be a user's separate local plugin, and the README's install path does not disclose disabling it."
  }
 ]
}
```

### `hancore_concrete:jasonpatel/omarchy-chessdotcom:8aec0f5b1d` — HANCORE kind shell-lua-injection
- source: hancore_concrete; tokens: 8065; files shown: 5
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] shell-lua-injection** `Panel.qml:108`: `Panel.qml` concatenates a supplied URL into a single-quoted shell command passed to `bar.run`. Remote Chess.com fields reach that sink through `modelData.url` and `puzzleData.url`.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['bar.run', 'modelData.url', 'puzzleData.url'])
```
   104|   }
   105| 
   106|   function launchUrl(url) {
   107|     if (!root.bar) return
>  108|     root.bar.run("omarchy-launch-or-focus-webapp Chess '" + url + "'")
   109|     root.close()
   110|   }
   111| 
   112|   function saveUsername(name) {
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
   "file": "Panel.qml",
   "line": 108,
   "finding": "`Panel.qml` concatenates a supplied URL into a single-quoted shell command passed to `bar.run`. Remote Chess.com fields reach that sink through `modelData.url` and `puzzleData.url`."
  }
 ]
}
```

### `hancore_concrete:majkelll/omarchy-remote-servers:2517124396` — HANCORE kind unbounded-input-resource
- source: hancore_concrete; tokens: 9561; files shown: 4
- Checker report shown to the model:
```
[USB-W10 warn experimental] BarWidget.qml: reads command output or a file with no size cap
```
- **[blocker] unbounded-input-resource** `BarWidget.qml:292`: `BarWidget.qml` then buffers the helper's complete combined result in `StdioCollector`; `Model.js` truncates only after that buffering. A hostile or faulty configured server can exhaust memory before the timeout expires.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['StdioCollector'])
```
   288| 
   289|   Process {
   290|     id: statsProc
   291|     property string outText: ""
>  292|     stdout: StdioCollector { waitForEnd: true; onStreamFinished: statsProc.outText = text }
   293|     onExited: function(code) {
   294|       root.applyStats(statsProc.outText, code)
   295|       statsProc.outText = ""
   296|     }
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
   "file": "BarWidget.qml",
   "line": 292,
   "finding": "`BarWidget.qml` then buffers the helper's complete combined result in `StdioCollector`; `Model.js` truncates only after that buffering. A hostile or faulty configured server can exhaust memory before the timeout expires."
  }
 ]
}
```

### `hancore_concrete:vibeschnapps/deck-chameleon:3b1218b634` — HANCORE kind runtime-qml-api-compat
- source: hancore_concrete; tokens: 7067; files shown: 3
- Checker report shown to the model:
```
[USB-W10 warn experimental] BarWidget.qml: reads command output or a file with no size cap
```
- **[blocker] runtime-qml-api-compat** `BarWidget.qml:57`: `BarWidget.qml` drops theme changes while busy after updating `currentTheme`; completion of the older build then applies the newer name. Bind each build/apply to an immutable generation and queue/coalesce the latest event so only the successfully built generation is applied.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['currentTheme'])
```
    53|     if (!theme) return
    54| 
    55|     if (!root.startupChecked) {
    56|       root.startupChecked = true
>   57|       root.currentTheme = theme
    58|       checkCurrentProcess.command = [root.pluginDir + "deck-apply", "--current"]
    59|       checkCurrentProcess.running = true
    60|       return
    61|     }
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
   "file": "BarWidget.qml",
   "line": 57,
   "finding": "`BarWidget.qml` drops theme changes while busy after updating `currentTheme`; completion of the older build then applies the newer name. Bind each build/apply to an immutable generation and queue/coalesce the latest event so only the successfully built generation is applied."
  }
 ]
}
```

### `dell_broken_verified:<id-withheld>` — Dell-derived load bug
- source: dell_broken_verified; tokens: 13552; files shown: 4
- Checker report shown to the model:
```
[USB-F01] Clipboard.qml: references helper script `/shell/plugins/clipboard/capture.sh`, which the plugin does not ship. Fix: ship `/shell/plugins/clipboard/capture.sh` in the plugin (e.g. bin/capture.sh) or inline the command
```
- **[blocker] load:missing-file** `Clipboard.qml:29`: captureScript property references `/shell/plugins/clipboard/capture.sh` which the plugin does not ship; currentProc, textWatchProc, and imageWatchProc all depend on this script to capture clipboard content.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: [])
```
    25|   property bool clearConfirmOpen: false
    26|   property var history: []
    27| 
    28|   property string historyPath: Quickshell.env("HOME") + "/.local/state/omarchy/clipboard-history.json"
>   29|   property string captureScript: root.omarchyPath + "/shell/plugins/clipboard/capture.sh"
    30|   // Shares the [menu] surface tokens — themes that style the menu also
    31|   // style the clipboard. Selected-row colors composed in the
    32|   // singleton so consumers drop them straight into Rectangle bindings.
    33|   property color background: Color.menu.background
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "load:missing-file",
   "severity": "blocker",
   "file": "Clipboard.qml",
   "line": 29,
   "finding": "captureScript property references `/shell/plugins/clipboard/capture.sh` which the plugin does not ship; currentProc, textWatchProc, and imageWatchProc all depend on this script to capture clipboard content."
  }
 ]
}
```

### `dell_inuse_missing_binary:<id-withheld>` — Dell-derived in-use bug
- source: dell_inuse_missing_binary; tokens: 21288; files shown: 14
- Checker report shown to the model:
```
[USB-A08 heuristic/medium] Panel.qml: line 60: assigns read-only `bar.centerHoverRevealSuppressed` - plugins get the read-only PluginBarApi facade, so this throws and aborts the rest of the function. Fix: call the setter instead, e.g. `bar.setCenterHoverRevealSuppressed(v)`
[USB-W05 heuristic/medium] install.sh: line 24: privileged/system-level action `sudo`. Fix: keep the plugin unprivileged; document manual root steps in the README instead of escalating from the shell
[USB-W05 heuristic/medium
```
- **[blocker] in-use:missing-binary** `Panel.qml:75`: Runs `magic-mouse-config` which is not on stock Omarchy PATH and not declared/shipped as an accessible binary; the bin/ file exists but won't be found without running install.sh.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['magic-mouse-config'])
```
    71|   }
    72| 
    73|   Process {
    74|     id: readProc
>   75|     command: ["magic-mouse-config", "get"]
    76|     stdout: StdioCollector {
    77|       onStreamFinished: {
    78|         try { root.cfg = JSON.parse(text) } catch (e) { console.warn("magic-mouse: bad config json", e) }
    79|       }
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
   "line": 75,
   "finding": "Runs `magic-mouse-config` which is not on stock Omarchy PATH and not declared/shipped as an accessible binary; the bin/ file exists but won't be found without running install.sh."
  }
 ]
}
```

### `dell_broken_verified:<id-withheld>` — Dell-derived other bug
- source: dell_broken_verified; tokens: 18352; files shown: 8
- Checker report shown to the model:
```
[USB-H07 heuristic/high] BarWidget.qml: line 11: placeholder endpoint/credential `https://proxmox.example.com` used as real data. Fix: read the endpoint/key from settings (declared in manifest defaults) or a real config file; never ship example.com / dummy keys
[USB-W08 warn experimental] bin/pve-status.sh: line 23: network call without a timeout (`curl`)
[USB-W08 warn experimental] bin/pve-action.sh: line 29: network call without a timeout (`curl`)
[USB-W01 warn experimental] bin/pve-console.sh
```
- **[blocker] config:placeholder-in-defaults** `BarWidget.qml:11`: Placeholder endpoint `https://proxmox.example.com:8006` is used as a real default value. The widget will attempt to connect to this non-existent host if the user doesn't configure their own endpoint, causing poller failures.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['https://proxmox.example.com:8006'])
```
     7|   id: root
     8|   moduleName: "io.github.boyoyooo.proxmarchy"
     9| 
    10|   // --- settings, read from this widget's shell.json entry -------------------
>   11|   readonly property string endpoint:        setting("endpoint", "https://proxmox.example.com:8006")
    12|   readonly property string credentialsFile: setting("credentialsFile", "")
    13|   readonly property string actionCredentialsFile: setting("actionCredentialsFile", "")
    14|   readonly property string caBundle:        setting("caBundle", "")
    15|   readonly property int    interval:        setting("interval", 15)
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "config:placeholder-in-defaults",
   "severity": "blocker",
   "file": "BarWidget.qml",
   "line": 11,
   "finding": "Placeholder endpoint `https://proxmox.example.com:8006` is used as a real default value. The widget will attempt to connect to this non-existent host if the user doesn't configure their own endpoint, causing poller failures."
  }
 ]
}
```


## B. 3 approve examples

### `dell_works_verified:<id-withheld>` — APPROVE with a warning (trusted-and-small exception)
- source: dell_works_verified; tokens: 17587; files shown: 4
- Checker report shown to the model:
```
[USB-W10 warn experimental] BarWidget.qml: reads command output or a file with no size cap
```
- **[warning] unbounded-input-resource** `BarWidget.qml:None`: Process stdout collectors read without explicit size caps; for typical JSON/status output this is acceptable.
  - **automated check 'cited line contains the described construct': N/A (no line cited)** (n/a; constructs: [])
```
(no line)
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
   "line": null,
   "finding": "Process stdout collectors read without explicit size caps; for typical JSON/status output this is acceptable."
  }
 ]
}
```

### `dell_works_verified:<id-withheld>` — APPROVE clean
- source: dell_works_verified; tokens: 12638; files shown: 5
- Checker report shown to the model:
```
[USB-W10 warn experimental] BarWidget.qml: reads command output or a file with no size cap
[USB-W10 warn experimental] Panel.qml: reads command output or a file with no size cap
[USB-W01 warn experimental] shield-backend.sh: runs `ensure_private_directory`, which is not part of a stock Omarchy install and is not listed as a dependency in the README/manifest
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

### `fix_upstream:0x1ocean/omarchy-server-mode:r02907-5990f5e127` — APPROVE after upstream fix / nudged
- source: fix_upstream; tokens: 18703; files shown: 11
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


## C. Reviewer notes

Read of the 15 fresh samples against the code shown (not curated; mechanical check passes 14/14 where a line is cited, the 15th, an approve warning, cites no line):
- **Anchoring is now mostly the exact statement**: `Dock.qml:254` is the `text: tip.item.name` binding, `Panel.qml:108` is the `bar.run("...'" + url + "'")` concatenation, `install.sh:19` is the `omarchy plugin disable` line, `bin/jarvis:44` is the unpinned `pip install`. Two samples are weaker: `omaclasroom` cites `README.md:25`, the first line of a two-line shell command whose `--client-secret` flag sits on the next line (accepted as a 2-line statement); `mouse_ctl.py:115` is correct for the clamp bug but see the next point.
- **Kind noise remains**: `davedes83/mouse-keybind-plugin` is filed `process-lifecycle-timeouts` while its cited line is an unrelated `max(max_val, v)` clamp bug (the prose bundles two findings with a '- ' bullet); `deck-chameleon` (`runtime-qml-api-compat`) is really a build-queue race. The vote picks one primary kind per finding; bundled findings keep a noisy label.
- **Prose is cleaner than v3** (file:line spans and review framing stripped, mid-word cuts removed) but some findings still read as continuations ('A privilege-boundary race: ...'), and a few keep a second sentence about a different construct.
- **Dell-derived samples**: `load:missing-file`, `config:placeholder-in-defaults` and `in-use:missing-binary` (`magic-mouse-config`, Dell run recorded it as a missing binary) are consistent with the code. Placeholder-URL rows (`config:*`) are a judgement call: the URL is example data a user is meant to overwrite.
- **Approve examples**: the warning sample (`docwatz/omarchyss`) has `line: null`, so it teaches a warning with no cited line; only 1 approve row left with a cited-line warning, which the open-model re-check flags as not exact.
