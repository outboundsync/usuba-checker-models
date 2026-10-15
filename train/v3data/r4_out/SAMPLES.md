# Usuba v3-data-r4 — SAMPLES (prompt_v3)

Rows 938 (train 796, val 142). 12 fresh random answers (seed 20261015+404; none appears in the r3 SAMPLES.md); each finding carries the automated check *cited line contains the described construct*. Results: {'pass': 10, 'n/a': 2}.

### `version_history:linuskelsey/arxiv-scanner:5926dea9db:broken` — version-history broken, kind url-scheme-network
- source: version_history; tokens: 11204; files shown: 5; license MIT; https://github.com/linuskelsey/arxiv-scanner @ 5926dea9db
- Checker report shown to the model:
```
[USB-W06 warn experimental] BarWidget.qml: line 254: Text.StyledText renders markup; if its text comes from command output, files, network or other apps it can inject links/images
[USB-W09 warn experimental] bin/poll.py: line 59: plain-http URL `http://arxiv.org` (no TLS)
[USB-W09 warn experimental] bin/check-authors.py: line 41: plain-http URL `http://a9.com` (no TLS)
[USB-W01 warn experimental] install.sh: runs `install_file_safe`, which is not
```
- **[blocker] url-scheme-network** `BarWidget.qml:301`: The code directly passes `modelData.link` to `Qt.openUrlExternally` without validating the URL scheme or domain, allowing attackers to craft malicious links that execute arbitrary commands or launch phishing sites when clicked.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['modelData.link', 'Qt.openUrlExternally'])
```
   297| 
   298|       MouseArea {
   299|         anchors.fill: parent
   300|         cursorShape: Qt.PointingHandCursor
>  301|         onClicked: Qt.openUrlExternally(modelData.link)
   302|       }
   303|     }
   304|   }
   305| 
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "unsure",
 "findings": [
  {
   "category": "url-scheme-network",
   "severity": "blocker",
   "file": "BarWidget.qml",
   "line": 301,
   "finding": "The code directly passes `modelData.link` to `Qt.openUrlExternally` without validating the URL scheme or domain, allowing attackers to craft malicious links that execute arbitrary commands or launch phishing sites when clicked."
  }
 ]
}
```

### `version_history:signal-six/kaomarchy:d8a77d0c66:broken` — version-history broken, kind runtime:undefined-property
- source: version_history; tokens: 11027; files shown: 7; license MIT; https://github.com/signal-six/kaomarchy @ d8a77d0c66
- Checker report shown to the model:
```
[USB-Q01] Kaomoji.qml: line 256: unknown QML type `RowLayout` - not provided by any module this file imports. Fix: add `import QtQuick.Layouts`
[USB-A01] Kaomoji.qml: line 170: `Quickshell.path` is not a member of the Quickshell singleton. Fix: real members include execDetached, env, shellDir, dataDir, stateDir, screens, iconPath, reload
[USB-W10 warn experimental] Kaomoji.qml: reads command output or a file with no size cap
[USB-W03 warn experim
```
- **[blocker] runtime:undefined-property** `Kaomoji.qml:256`: The `RowLayout` type on is used without a corresponding import statement, causing the QML engine to fail at runtime with an undefined component error.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['RowLayout'])
```
   252|         anchors.bottomMargin: card.contentBottomInset
   253|         anchors.leftMargin: card.contentLeftInset
   254|         spacing: root.contentSpacing
   255| 
>  256|         RowLayout {
   257|           width: parent.width
   258|           height: root.headerHeight
   259|           spacing: Style.spacing.md
   260| 
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "runtime:undefined-property",
   "severity": "blocker",
   "file": "Kaomoji.qml",
   "line": 256,
   "finding": "The `RowLayout` type on is used without a corresponding import statement, causing the QML engine to fail at runtime with an undefined component error."
  }
 ]
}
```

### `version_history:hazat/word-fixer-app:4a0acc520e:broken` — version-history broken, kind in-use:invalid-command-arg
- source: version_history; tokens: 11924; files shown: 7; license MIT; https://github.com/hazat/word-fixer-app @ 4a0acc520e
- Checker report shown to the model:
```
[USB-B01] scripts/build-icon.sh: script string runs `qlmanage`, which is not installed on the Dell's Omarchy 4.0.4 (system_bins) and not shipped by the plugin. Fix: use a binary that exists on stock Omarchy (see dell_env/system_bins.txt), ship a script for it, or document `qlmanage` as a dependency in README.md
[USB-B01] scripts/package-app.sh: script string runs `codesign`, which is not installed on the Dell's Omarchy 4.0.4 (system_bins) and not
```
- **[blocker] in-use:invalid-command-arg** `linux/lib/system.mjs:328`: The code passes a Lua expression string to `hyprctl dispatch`, which Hyprland ignores because it expects a direct command rather than an embedded script, causing the window focus operation to fail silently.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['hyprctl dispatch'])
```
   324|   async focusAndVerify(target, { signal } = {}) {
   325|     try {
   326|       await this.command(
   327|         'hyprctl',
>  328|         ['dispatch', `hl.dsp.focus({ window = 'address:${target.address}' })`],
   329|         { signal },
   330|       );
   331|       const deadline = Date.now() + 750;
   332|       while (Date.now() < deadline) {
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
   "file": "linux/lib/system.mjs",
   "line": 328,
   "finding": "The code passes a Lua expression string to `hyprctl dispatch`, which Hyprland ignores because it expects a direct command rather than an embedded script, causing the window focus operation to fail silently."
  }
 ]
}
```

### `version_history:kasemeyer/omalink-bar:77a128d773:broken` — version-history broken, kind shell-lua-injection
- source: version_history; tokens: 10763; files shown: 7; license MIT; https://github.com/kasemeyer/omalink-bar @ 77a128d773
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] shell-lua-injection** `BarWidget.qml:74`: The code passes the unquoted string `"scrcpy"` directly to `root.bar.run`, which executes it via a shell without sanitization. This allows an attacker to inject arbitrary commands if the executed path or arguments ever incorporate untrusted input, leading to remote code execution.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['"scrcpy"', 'root.bar.run'])
```
    70|     { icon: "󰂚", label: "Ring phone",          run: function() { kdec.ring() } },
    71|     { icon: "󰅌", label: "Send clipboard",      run: function() { kdec.sendClipboard(); root.toast() } },
    72|     { icon: "󰈔", label: "Send a file…",        run: function() { root.pickAndShare(); root.close() } },
    73|     { icon: "󰂜", label: "Ping phone",          run: function() { kdec.ping() } },
>   74|     { icon: "󰍹", label: "Mirror screen",       run: function() { root.bar.run("scrcpy"); root.close() } }
    75|   ]
    76| 
    77|   property int cursorIndex: 0
    78|   function moveCursor(dy) {
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
   "file": "BarWidget.qml",
   "line": 74,
   "finding": "The code passes the unquoted string `\"scrcpy\"` directly to `root.bar.run`, which executes it via a shell without sanitization. This allows an attacker to inject arbitrary commands if the executed path or arguments ever incorporate untrusted input, leading to remote code execution."
  }
 ]
}
```

### `version_history:seesharpsi/omarchy-vct-scoreline:97311e2651:broken` — version-history broken, kind in-use:stale-or-wrong-display
- source: version_history; tokens: 10404; files shown: 3; license MIT; https://github.com/seesharpsi/omarchy-vct-scoreline @ 97311e2651
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] in-use:stale-or-wrong-display** `vlr.py:473`: The assignment `warning_text = "Live map details unavailable for " + ", ".join(warnings[:MAX_WARNINGS])` unconditionally constructs a warning message even when the `warnings` list is empty, causing the UI to display a misleading error prefix with no actual errors.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['warning_text = "Live map details unavailable for " + ", ".join(warnings[:MAX_WARNINGS])', 'warnings'])
```
   469|         except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError) as error:
   470|             live.append(match)
   471|             warnings.append(f"{match['id']}: {clean_text(str(error))}")
   472| 
>  473|     warning_text = "Live map details unavailable for " + ", ".join(warnings[:MAX_WARNINGS])
   474|     warning_text = warning_text[:MAX_WARNING_CHARS]
   475|     if len(warnings) > MAX_WARNINGS:
   476|         suffix = f" (+{len(warnings) - MAX_WARNINGS} more)"
   477|         warning_text = warning_text[:MAX_WARNING_CHARS - len(suffix)] + suffix
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
   "file": "vlr.py",
   "line": 473,
   "finding": "The assignment `warning_text = \"Live map details unavailable for \" + \", \".join(warnings[:MAX_WARNINGS])` unconditionally constructs a warning message even when the `warnings` list is empty, causing the UI to display a misleading error prefix with no actual errors."
  }
 ]
}
```

### `version_history:pdfrg/amla:d2f8c278ed:broken` — version-history broken, kind runtime:state-or-race
- source: version_history; tokens: 11796; files shown: 3; license MIT; https://github.com/pdfrg/amla @ d2f8c278ed
- Checker report shown to the model:
```
[USB-J01] Amla.qml: line 401: `pendingM3uText` is never declared (no property, id, var or parameter) - ReferenceError at runtime. Fix: declare `property var pendingM3uText` (and fill it), or use a real API object; never hide missing APIs behind try/catch
[USB-W07 warn experimental] Amla.qml: line 430: a variable is interpolated into a shell/Lua command string (`"sh", "-c", "rm -rf " +`)
[USB-W01 warn experimental] scripts/warm-art-cache.sh: runs 
```
- **[blocker] runtime:state-or-race** `Dispatch.js:25`: The `mustRunningExpr` function relies solely on `[ -S... ]` to detect the running state, which returns true if the socket file persists after a crash. This causes the system to incorrectly report the service as active when the underlying process is actually dead.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['mustRunningExpr', '[ -S... ]'])
```
    21| }
    22| 
    23| // must ctl socket per DOCUMENTATION.md: $XDG_RUNTIME_DIR/must/ctl.sock
    24| function mustRunningExpr() {
>   25|     return "[ -S \"${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/must/ctl.sock\" ]"
    26| }
    27| 
    28| function cliampRunningExpr() {
    29|     return "[ -S \"$HOME/.config/cliamp/cliamp.sock\" ]"
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "runtime:state-or-race",
   "severity": "blocker",
   "file": "Dispatch.js",
   "line": 25,
   "finding": "The `mustRunningExpr` function relies solely on `[ -S... ]` to detect the running state, which returns true if the socket file persists after a crash. This causes the system to incorrectly report the service as active when the underlying process is actually dead."
  }
 ]
}
```

### `version_history:vex-7k9/vex-system-monitor:4422d85610:broken` — version-history broken, kind runtime:logic-error
- source: version_history; tokens: 11654; files shown: 4; license MIT; https://github.com/vex-7k9/vex-system-monitor @ 4422d85610
- Checker report shown to the model:
```
[USB-A04] BarWidget.qml: line 325: `root.toggleMode()` - `BarWidget` has no method `toggleMode`. Fix: real `BarWidget` methods: QObject, _q_createJSWrapper, _q_resourceObjectDeleted, _settingKeys, bar, barSize, broadcast, bumpTemp, cardHovered, childAt
```
- **[blocker] runtime:logic-error** `StatsService.qml:136`: The `echo cpu $u...` command on omits the `=` delimiter between the key and values, causing the parser to drop the entire CPU line because it cannot recognize the malformed output format.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['echo cpu $u...'])
```
   132|   function _snapshotLines() {
   133|     var lines = [
   134|       "LANG=C",
   135|       "{",
>  136|       "  read -r _ u n s i io irq so < /proc/stat; echo cpu $u $n $s $i $io $irq $so",
   137|       "  read -r cur < /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq || cur=NA; echo cur=$cur",
   138|       "  read -r cmax < /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq || cmax=NA; echo cmax=$cmax",
   139|       "  read -r ctemp < " + root.cpuTempPath + " || ctemp=NA; echo ctemp=$ctemp",
   140|       "  echo mem=$(/usr/bin/awk '/^(MemTotal|MemAvailable|SwapTotal|SwapFree):/ {print $1, $2}' /proc/meminfo)",
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "runtime:logic-error",
   "severity": "blocker",
   "file": "StatsService.qml",
   "line": 136,
   "finding": "The `echo cpu $u...` command on omits the `=` delimiter between the key and values, causing the parser to drop the entire CPU line because it cannot recognize the malformed output format."
  }
 ]
}
```

### `jankeesvw-history:omarchy-github-build-monitor:e68bc2e408:broken` — jankeesvw-history broken
- source: jankeesvw-history; tokens: 23716; files shown: 3
- Checker report shown to the model:
```
(no Checker findings)
```
- **[blocker] qml:property-shadowing** `Panel.qml:1412`: The `visible` binding crashes when `flagged` is undefined because accessing `.length` on undefined throws a TypeError.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['visible', 'flagged', '.length'])
```
  1408|                   // is not something the status colour can say.
  1409|                   Item {
  1410|                     id: migrationMark
  1411|                     anchors.verticalCenter: parent.verticalCenter
> 1412|                     visible: row.modelData.flagged !== undefined && row.modelData.flagged.length > 0
  1413|                     width: visible ? migrationGlyph.implicitWidth : 0
  1414|                     height: migrationGlyph.implicitHeight
  1415| 
  1416|                     Text {
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "qml:property-shadowing",
   "severity": "blocker",
   "file": "Panel.qml",
   "line": 1412,
   "finding": "The `visible` binding crashes when `flagged` is undefined because accessing `.length` on undefined throws a TypeError."
  }
 ]
}
```

### `hancore_concrete:alanfrigo/omarchy-openlogi:2cdccc1064` — HANCORE broken
- source: hancore_concrete; tokens: 11114; files shown: 5
- Checker report shown to the model:
```
[USB-B01] scripts/uninstall.sh: script string runs `unit`, which is not installed on the Dell's Omarchy 4.0.4 (system_bins) and not shipped by the plugin. Fix: use a binary that exists on stock Omarchy (see dell_env/system_bins.txt), ship a script for it, or document `unit` as a dependency in README.md
[USB-B01] scripts/build-openlogi.sh: script string runs `cargo`, which is not installed on the Dell's Omarchy 4.0.4 (system_bins) and not shipped 
```
- **[blocker] file-safety-symlink-perms** `scripts/install.sh:27`: `scripts/install.sh` opens `$XDG_STATE_HOME/omarchy-openlogi/.install.lock` with `exec 9>` before checking the destination's ownership or whether it is a symlink.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['$XDG_STATE_HOME/omarchy-openlogi/.install.lock', 'exec 9>'])
```
    23| }
    24| for tool in flock jq omarchy omarchy-shell systemctl sha256sum cut find cmp; do command -v "$tool" >/dev/null || fail "$tool is required"; done
    25| export OMARCHY_SHELL_IPC_TIMEOUT=${OMARCHY_SHELL_IPC_TIMEOUT:-15s}
    26| mkdir -p -- "$state"
>   27| exec 9>"$state/.install.lock"
    28| flock -n 9 || fail 'another OpenLogi installation/removal is running'
    29| [[ ! -e $receipt ]] || fail "installation receipt exists at $receipt; uninstall first (or resolve its reported conflicts)"
    30| for name in openlogi openlogi-agent openlogi-desktop openlogi-overlay; do
    31|     [[ -x $bin/$name && ! -L $bin/$name ]] || fail "missing compatible private binary $bin/$name; run scripts/build-openlogi.sh"
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "unsure",
 "findings": [
  {
   "category": "file-safety-symlink-perms",
   "severity": "blocker",
   "file": "scripts/install.sh",
   "line": 27,
   "finding": "`scripts/install.sh` opens `$XDG_STATE_HOME/omarchy-openlogi/.install.lock` with `exec 9>` before checking the destination's ownership or whether it is a symlink."
  }
 ]
}
```

### `dell_broken_verified:<id-withheld>` — Dell-derived broken
- source: dell_broken_verified; tokens: 21316; files shown: 9
- Checker report shown to the model:
```
[USB-Q01] examples/standalone/shell.qml: line 19: unknown QML type `VpnCore` - not provided by any module this file imports. Fix: VpnCore.qml exists but is not in this file's directory; add `import "../.."`
[USB-W04 warn experimental] scripts/run-example.sh: line 18: unsafe file operation `rm -rf "$workdir"` (world-writable mode, forced symlink, predictable /tmp path, or rm -rf on an unchecked variable)
```
- **[blocker] load:unknown-type** `examples/standalone/shell.qml:19`: Unknown QML type `VpnCore` - the file uses VpnCore but only imports QtQuick and Quickshell. VpnCore.qml exists in the plugin root but is not in this file's directory; add `import "../.."` to resolve it.
  - **automated check 'cited line contains the described construct': PASS** (strict; constructs: ['VpnCore', 'import "../.."'])
```
    15| import QtQuick
    16| import Quickshell
    17| 
    18| ShellRoot {
>   19|   VpnCore {
    20|     id: vpn
    21|     intervalMs: 15000
    22|     // only: "zuhause"                    // default: every VPN-typed profile
    23|     // vpnTypes: ["vpn", "wireguard"]     // add "tun" for raw tunnel profiles
```
- **full answer taught:**
```json
{
 "verdict": "changes_requested",
 "load": "broken",
 "findings": [
  {
   "category": "load:unknown-type",
   "severity": "blocker",
   "file": "examples/standalone/shell.qml",
   "line": 19,
   "finding": "Unknown QML type `VpnCore` - the file uses VpnCore but only imports QtQuick and Quickshell. VpnCore.qml exists in the plugin root but is not in this file's directory; add `import \"../..\"` to resolve it."
  }
 ]
}
```

### `version_history:mshareef-git/omavibes:1bfa453514:fixed` — APPROVE: post-fix version (Checker clean + model check)
- source: version_history; tokens: 12138; files shown: 7; license MIT; https://github.com/mshareef-git/omavibes @ 1bfa453514
- Checker report shown to the model:
```
[USB-W10 warn experimental] OmaVibesState.qml: reads command output or a file with no size cap
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
- source: dell_works_verified; tokens: 14175; files shown: 4
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
