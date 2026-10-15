"""Synthetic rows for v3-fixes (clearly marked synthetic; every file here is written for this repo, no HANCORE text, no plugin names, no issue links).
SPECS: list of dict(id, expect, files, verdict, load, findings, note). `expect` = the set of Checker rule ids that must fire on the tree
(lifecycle_rules USB-N/L/W* with all rules on, hancore_rules_v2 USB-HC* all rules on); empty set = must be clean. build_v3_fixes_rows.py refuses a spec whose expectation fails."""
import json
def man(i, kinds, eps, extra=None):
    d = {"schemaVersion": 1, "id": i, "name": i.split(".")[-1].replace("-", " ").title(), "version": "1.0.0", "kinds": kinds, "entryPoints": eps}
    d.update(extra or {}); return json.dumps(d, indent=2)
HDR = "import QtQuick\nimport Quickshell\nimport Quickshell.Io\n\n"
def surface_ok(kind_word):
    return (HDR + "Item {\n  id: root\n  property var shell: null\n  property bool opened: false\n  function open(payloadJson) {\n    var p = {}\n    try { p = JSON.parse(String(payloadJson || \"{}\").slice(0, 16384)) } catch (e) {}\n    opened = true; win.visible = true\n  }\n  function close() { opened = false; win.visible = false }\n  PanelWindow {\n    id: win\n    visible: false\n    implicitWidth: 320; implicitHeight: 180\n    Text { anchors.centerIn: parent; text: \"" + kind_word + "\"; color: \"white\"; textFormat: Text.PlainText }\n    Item { anchors.fill: parent; focus: root.opened; Keys.onEscapePressed: root.close() }\n  }\n}\n")
def surface(kind_word, fns):
    return (HDR + "Item {\n  id: root\n  property var shell: null\n  property bool opened: false\n" + fns + "  PanelWindow {\n    visible: root.opened\n    implicitWidth: 320; implicitHeight: 180\n    Text { anchors.centerIn: parent; text: \"" + kind_word + "\"; color: \"white\"; textFormat: Text.PlainText }\n  }\n}\n")
BW = HDR + "Item {\n  id: root\n  implicitWidth: t.implicitWidth\n  Text { id: t; color: \"white\"; text: \"ok\"; textFormat: Text.PlainText }\n}\n"
def broken(i, line_word, f, ln, cat, text, load="broken"):
    return dict(verdict="changes_requested", load=load, findings=[dict(category=cat, severity="blocker", file=f, line=ln, finding=text)])
OK = dict(verdict="approve", load="works", findings=[])
SPECS = [
 dict(id="syn.lifecycle.overlay-toggle-only", expect={"USB-L01"}, note="overlay entry with toggle() only",
      files={"manifest.json": man("sample.dim-screen", ["overlay"], {"overlay": "Overlay.qml"}), "Overlay.qml": surface("Dim", "  function toggle() { opened = !opened }\n")},
      **broken("", "", "Overlay.qml", 4, "load:panel-lifecycle", "The `overlay` root `Item` defines `toggle()` but neither `open(payloadJson)` nor `close()`; the shell calls those to show and hide the overlay and skips them when absent, so it never appears.")),
 dict(id="syn.lifecycle.panel-open-no-close", expect={"USB-L01"}, note="panel with open() but no close()",
      files={"manifest.json": man("sample.stat-board", ["panel"], {"panel": "Panel.qml"}), "Panel.qml": surface("Stats", "  function open(payloadJson) { opened = true }\n")},
      **broken("", "", "Panel.qml", 4, "load:panel-lifecycle", "The `panel` root `Item` defines `open()` but no `close()`; the shell hides the panel by calling `close()`, which is skipped when absent, so `opened` stays true and the panel cannot be dismissed.")),
 dict(id="syn.lifecycle.menu-close-only", expect={"USB-L01"}, note="menu with close() but no open()",
      files={"manifest.json": man("sample.quick-actions", ["menu"], {"menu": "Menu.qml"}), "Menu.qml": surface("Actions", "  function close() { opened = false }\n")},
      **broken("", "", "Menu.qml", 4, "load:panel-lifecycle", "The `menu` root `Item` defines `close()` but no `open(payloadJson)`; the shell summons the menu through `open()`, so it never appears.")),
 dict(id="syn.manifest.kind-without-key", expect={"USB-N01"}, note="bar-widget declared, entryPoints names panel",
      files={"manifest.json": man("sample.mini-clock", ["bar-widget"], {"panel": "BarWidget.qml"}), "BarWidget.qml": BW},
      **broken("", "", "manifest.json", 8, "load:component-not-created", "Kind `bar-widget` is declared but `entryPoints` has no `barWidget` key (only `panel`), so the shell finds no bar-widget entry point and the widget is never created.")),
 dict(id="syn.manifest.kind-used-as-key", expect={"USB-N01"}, note="entryPoints keyed by kind name instead of entry-point key",
      files={"manifest.json": man("sample.load-dots", ["bar-widget"], {"bar-widget": "BarWidget.qml"}), "BarWidget.qml": BW},
      **broken("", "", "manifest.json", 8, "load:component-not-created", "`entryPoints` uses the key `bar-widget`; the shell reads `entryPoints.barWidget`, so this widget has no entry point and is never created.")),
 dict(id="syn.manifest.no-schema-version", expect={"USB-N02"}, note="manifest rejected by the registry",
      files={"manifest.json": json.dumps({"id": "sample.tiny-note", "name": "Tiny Note", "version": "1.0.0", "kinds": ["bar-widget"], "entryPoints": {"barWidget": "BarWidget.qml"}}, indent=2), "BarWidget.qml": BW},
      **broken("", "", "manifest.json", 1, "load:component-not-created", "The manifest has no `schemaVersion` (the shell registry requires the number 1) and is rejected, so the plugin is never registered.")),
 dict(id="syn.qml.required-injected-property", expect={"USB-L03"}, note="required property on a host-injected name",
      files={"manifest.json": man("sample.net-badge", ["bar-widget"], {"barWidget": "BarWidget.qml"}), "BarWidget.qml": HDR + "Item {\n  id: root\n  required property var shell\n  implicitWidth: t.implicitWidth\n  Text { id: t; color: \"white\"; text: \"net\"; textFormat: Text.PlainText }\n}\n"},
      **broken("", "", "BarWidget.qml", 6, "load:component-not-created", "`required property var shell` on the entry root: the host assigns `shell` only after the component is created, so creation fails with 'Required property shell was not initialized'.")),
 dict(id="syn.supply.cargo-git-unpinned", expect={"USB-HC17", "USB-W11"}, note="unpinned git build in an installer",
      files={"manifest.json": man("sample.beat-meter", ["bar-widget"], {"barWidget": "BarWidget.qml"}), "BarWidget.qml": BW, "README.md": "# Beat Meter\nRun `./install.sh` once; remove with `rm ~/.local/bin/beatd`.\n",
             "install.sh": "#!/bin/bash\nset -euo pipefail\ncargo install --git https://example.invalid/beatd/beatd.git --root \"$HOME/.local\"\n"},
      **broken("", "", "install.sh", 3, "remote-code-pinning", "`cargo install --git` builds whatever the default branch holds today and installs it, with no `--rev` commit pin or checksum.", load="unsure")),
 dict(id="syn.supply.sudoers-nopasswd-all", expect={"USB-HC15", "USB-W13"}, note="broad sudoers written by setup script",
      files={"manifest.json": man("sample.fan-curve", ["bar-widget"], {"barWidget": "BarWidget.qml"}), "BarWidget.qml": BW, "README.md": "# Fan Curve\nRun `./setup.sh` to allow fan control; remove /etc/sudoers.d/fan-curve to undo.\n",
             "setup.sh": "#!/bin/bash\nset -euo pipefail\necho \"$USER ALL=(ALL) NOPASSWD: ALL\" | sudo tee /etc/sudoers.d/fan-curve >/dev/null\n"},
      **broken("", "", "setup.sh", 3, "privileged-system", "The setup script writes `NOPASSWD: ALL` for the user into `/etc/sudoers.d`, so any process of the user gets passwordless root.", load="unsure")),
 # ---- approve side
 dict(id="syn.ok.overlay-open-close", expect=set(), note="clean overlay with open/close/opened, payload cap, Escape",
      files={"manifest.json": man("sample.screen-ruler", ["overlay"], {"overlay": "Overlay.qml"}), "Overlay.qml": surface_ok("Ruler")}, **OK),
 dict(id="syn.ok.panel-open-close", expect=set(), note="clean panel with open/close/opened",
      files={"manifest.json": man("sample.todo-pad", ["panel"], {"panel": "Panel.qml"}), "Panel.qml": surface_ok("Todo")}, **OK),
 dict(id="syn.ok.menu-open-close", expect=set(), note="clean menu with open/close/opened",
      files={"manifest.json": man("sample.power-menu", ["menu"], {"menu": "Menu.qml"}), "Menu.qml": surface_ok("Power")}, **OK),
 dict(id="syn.ok.service-driven-hud", expect=set(), note="persistent HUD overlay driven by its service: no summon, so no open/close needed",
      files={"manifest.json": man("sample.key-hud", ["service", "overlay"], {"service": "Service.qml", "overlay": "Overlay.qml"}),
             "Service.qml": "import QtQuick\n\nItem {\n  id: root\n  property bool enabled: true\n  property string last: \"\"\n}\n",
             "Overlay.qml": HDR + "Item {\n  id: root\n  property var service: null\n  PanelWindow {\n    visible: !!(root.service && root.service.enabled)\n    implicitWidth: 200; implicitHeight: 40\n    Text { anchors.centerIn: parent; text: root.service ? root.service.last : \"\"; color: \"white\"; textFormat: Text.PlainText }\n  }\n}\n"}, **OK),
 dict(id="syn.ok.bash-c-shellquote", expect=set(), note="bash -c with literal script, every external value goes through Util.shellQuote",
      files={"manifest.json": man("sample.note-copy", ["bar-widget"], {"barWidget": "BarWidget.qml"}),
             "BarWidget.qml": "import QtQuick\nimport Quickshell.Io\nimport qs.Commons\n\nItem {\n  id: root\n  implicitWidth: t.implicitWidth\n  property string title: \"note\"\n  Text { id: t; color: \"white\"; text: root.title; textFormat: Text.PlainText }\n  Process { id: cp; command: [\"bash\", \"-c\", \"printf %s \" + Util.shellQuote(root.title) + \" | wl-copy\"] }\n  MouseArea { anchors.fill: parent; onClicked: cp.running = true }\n}\n"}, **OK),
 dict(id="syn.ok.readme-mentions-sudo", expect=set(), note="README says no sudo is needed; no privileged code",
      files={"manifest.json": man("sample.uptime-chip", ["bar-widget"], {"barWidget": "BarWidget.qml"}), "BarWidget.qml": BW,
             "README.md": "# Uptime Chip\nRuns with your normal user permissions. No sudo or pkexec is required.\n\n## Remove\n`omarchy plugin remove sample.uptime-chip`\n"}, **OK),
 dict(id="syn.ok.mktemp-guarded-cleanup", expect=set(), note="rm -rf on a mktemp -d variable with a trap; curl output to /dev/null with timeouts",
      files={"manifest.json": man("sample.sync-ping", ["bar-widget"], {"barWidget": "BarWidget.qml"}), "BarWidget.qml": BW,
             "README.md": "# Sync Ping\nHelper `bin/ping.sh` pings a fixed health URL once.\n",
             "bin/ping.sh": "#!/usr/bin/env bash\nset -euo pipefail\nwork=$(mktemp -d)\ntrap 'rm -rf \"$work\"' EXIT\ncurl --fail --silent --max-time 4 --proto '=https' https://status.example.invalid/ping >/dev/null 2>&1 || true\nprintf ok > \"$work/state\"\nrm -rf \"$work\"\n"}, **OK),
]
