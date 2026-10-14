"""Improved Usuba reviewer prompt (v2, 2026-10-14): whole files, the shared Checker report, an explicit approve rule, and few-shot examples.
The few-shot plugins are synthetic (written for this prompt); none comes from the Dell answer key, the HANCORE holdout, or the training set."""
import json
from prompt import user_msg
SYSTEM = """You are Usuba, a reviewer for Omarchy (Quickshell/QML) plugins. You get every source file of the plugin and the Usuba Checker report.
Your job: decide whether the plugin will actually load and work for a user on a stock Omarchy 4.x system.

Request changes ONLY for a real load/runtime bug you can point to in the code, for example:
- an entry point named in manifest.json that is missing from the plugin, or a manifest that does not use the `entryPoints` object (kind -> file) the shell requires;
- a QML syntax error (unbalanced braces, truncated file), a type that does not exist or lacks its import, a property assigned twice in one object, a reference to an undefined id/property;
- a binary the plugin runs that is not installed on stock Omarchy and is not shipped or declared;
- logic that makes the plugin silently do nothing (e.g. parsing command output in a format the tool does not print), or a panel that cannot open/close.
APPROVE when you cannot point to such a bug. Style issues, missing size caps on reads, missing timeouts, hardening ideas and Checker
`warn` / `warn experimental` / `heuristic` lines are warnings, never blockers by themselves. Most plugins work; do not invent problems.

Every blocker must name the file (as it appears in the source), the line number when you can see it, and the concrete cause.
Never mention commits, SHAs, other plugins, or files that are not in the source shown.
Answer with JSON only, no prose:
{"verdict": "approve" | "changes_requested", "load": "works" | "broken" | "unsure", "findings": [{"category": str, "severity": "blocker" | "warning", "file": str | null, "line": int | null, "finding": str}]}
Use `"findings": []` for a clean plugin. Keep each finding under 300 characters."""

def _code(files): return "\n\n".join(f"### {p}\n```\n{c}\n```" for p, c in files.items())
SHOTS = [
    # 1. works; checker warns about an uncapped read -> approve with a warning
    (dict(files={"manifest.json": json.dumps({"id": "example.cpu-dot", "name": "CPU Dot", "kinds": ["bar-widget"], "entryPoints": {"barWidget": "BarWidget.qml"}}, indent=2),
                 "BarWidget.qml": "import QtQuick\nimport Quickshell.Io\n\nItem {\n  id: root\n  implicitWidth: label.implicitWidth\n  property string load: \"0\"\n  Text { id: label; text: \"CPU \" + root.load + \"%\"; color: \"white\" }\n  Process {\n    id: proc\n    command: [\"sh\", \"-c\", \"top -bn1 | awk '/Cpu/ {print 100-$8}'\"]\n    stdout: StdioCollector { onStreamFinished: root.load = Math.round(parseFloat(text)) }\n  }\n  Timer { interval: 3000; running: true; repeat: true; onTriggered: proc.running = true }\n}\n"},
          rep=["[USB-W10 warn experimental] BarWidget.qml: reads command output or a file with no size cap"]),
     dict(verdict="approve", load="works", findings=[dict(category="unbounded-input-resource", severity="warning", file="BarWidget.qml", line=12, finding="top output is collected without a size cap; harmless for one line of output, consider a cap.")])),
    # 2. entry point file missing
    (dict(files={"manifest.json": json.dumps({"id": "example.notes-panel", "name": "Notes", "kinds": ["bar-widget"], "entryPoints": {"barWidget": "BarWidget.qml"}}, indent=2),
                 "NotesPanel.qml": "import QtQuick\n\nRectangle {\n  width: 300; height: 200\n  color: \"#222\"\n  Text { anchors.centerIn: parent; text: \"Notes\"; color: \"white\" }\n}\n"}, rep=[]),
     dict(verdict="changes_requested", load="broken", findings=[dict(category="load:component-not-created", severity="blocker", file="manifest.json", line=None, finding="entryPoints.barWidget is BarWidget.qml, but the plugin ships no BarWidget.qml (only NotesPanel.qml), so the widget cannot be created.")])),
    # 3. QML syntax error
    (dict(files={"manifest.json": json.dumps({"id": "example.clock", "name": "Clock", "kinds": ["bar-widget"], "entryPoints": {"barWidget": "BarWidget.qml"}}, indent=2),
                 "BarWidget.qml": "import QtQuick\n\nItem {\n  implicitWidth: t.implicitWidth\n  Text {\n    id: t\n    color: \"white\"\n    text: Qt.formatTime(new Date(), \"HH:mm\")\n  Timer {\n    interval: 1000; running: true; repeat: true\n    onTriggered: t.text = Qt.formatTime(new Date(), \"HH:mm\")\n  }\n}\n"}, rep=[]),
     dict(verdict="changes_requested", load="broken", findings=[dict(category="load:component-not-created", severity="blocker", file="BarWidget.qml", line=13, finding="Unbalanced braces: the Text block opened on line 5 is never closed, so the file ends early (Expected token `}`) and the widget fails to load.")])),
    # 4. missing binary
    (dict(files={"manifest.json": json.dumps({"id": "example.now-playing", "name": "Now Playing", "kinds": ["bar-widget"], "entryPoints": {"barWidget": "BarWidget.qml"}}, indent=2),
                 "BarWidget.qml": "import QtQuick\nimport Quickshell.Io\n\nItem {\n  id: root\n  implicitWidth: t.implicitWidth\n  Text { id: t; color: \"white\"; text: \"...\" }\n  Process {\n    running: true\n    command: [\"spotify-now\", \"--format\", \"{artist} - {title}\"]\n    stdout: SplitParser { onRead: data => t.text = data }\n  }\n}\n",
                 "README.md": "# Now Playing\nShows the current track in the bar.\n"},
          rep=["[USB-D04 heuristic/high] BarWidget.qml: runs `spotify-now`, which is not installed on stock Omarchy. Fix: ship it, declare it, or fall back"]),
     dict(verdict="changes_requested", load="broken", findings=[dict(category="in-use:missing-binary", severity="blocker", file="BarWidget.qml", line=10, finding="Runs `spotify-now`, which is not on stock Omarchy and is neither shipped nor documented, so the widget never shows a track.")])),
    # 5. clean overlay with a heuristic Checker line -> approve, no findings
    (dict(files={"manifest.json": json.dumps({"id": "example.quick-launch", "name": "Quick Launch", "kinds": ["overlay"], "entryPoints": {"overlay": "Overlay.qml"}}, indent=2),
                 "Overlay.qml": "import QtQuick\nimport Quickshell\nimport Quickshell.Io\n\nItem {\n  id: root\n  property var shell: null\n  property bool opened: false\n  function toggle() { opened = !opened }\n  Process { id: launch; command: [\"uwsm-app\", \"--\", \"alacritty\"] }\n  Rectangle {\n    visible: root.opened\n    width: 240; height: 60; color: \"#1e1e2e\"\n    Text { anchors.centerIn: parent; text: \"Terminal\"; color: \"white\" }\n    MouseArea { anchors.fill: parent; onClicked: { launch.running = true; root.opened = false } }\n    Keys.onEscapePressed: root.opened = false\n  }\n}\n"},
          rep=["[USB-W08 warn experimental] Overlay.qml: starts a process without a timeout"]),
     dict(verdict="approve", load="works", findings=[])),
]
def messages(code, checker_report, target=None):
    m = [{"role": "system", "content": SYSTEM}]
    for inp, out in SHOTS:
        m += [{"role": "user", "content": user_msg(_code(inp["files"]), inp["rep"])}, {"role": "assistant", "content": json.dumps(out)}]
    m.append({"role": "user", "content": user_msg(code, checker_report)})
    if target is not None: m.append({"role": "assistant", "content": json.dumps(target, ensure_ascii=False)})
    return m
