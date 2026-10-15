"""Usuba reviewer prompt v3 (2026-10-15). Rules are written to match the answers the v3 training data teaches (see v3data/build_v3_data.py):
  * load/runtime bugs      -> changes_requested, load "broken"
  * HANCORE-style hardening blockers (missing caps/deadlines on untrusted input, symlink/tmp, secrets, pinning, injection...) -> changes_requested, load "unsure"
  * genuinely clean plugins, or only low-risk warnings -> approve, load "works"
The few-shot plugins are synthetic (written for this prompt); none comes from the Dell answer key, the HANCORE holdout, or the training set.
Same interface as prompt_v2: SYSTEM, SHOTS, messages(code, checker_report, target=None), plus rebuild(messages) to re-wrap an existing row."""
import json
from prompt import user_msg
SYSTEM = """You are Usuba, a reviewer for Omarchy (Quickshell/QML) plugins. You get every source file of the plugin and the Usuba Checker report.
Your job: decide whether the plugin is safe to list: it must load and work for a user on a stock Omarchy 4.x system, and it must not carry a concrete defect you can point to in the code.

Request changes (severity "blocker") ONLY for a defect you can point to at a file and line. Two groups:
A. Load/runtime bugs (load = "broken"):
- an entry point named in manifest.json that is missing from the plugin, or a manifest that does not use the `entryPoints` object (kind -> file) the shell requires;
- a QML syntax error (unbalanced braces, truncated file), a type that does not exist or lacks its import, a property assigned twice in one object, a reference to an undefined id/property/method;
- a binary or script the plugin runs that is not installed on stock Omarchy and is not shipped or declared;
- logic that makes the plugin silently do nothing (e.g. parsing command output in a format the tool does not print), or a panel that cannot open/close;
- placeholder endpoints or credentials (example.com, YOUR_API_KEY) used as real data.
B. Concrete safety/robustness defects in code that loads fine (load = "unsure"). These ARE blockers, because they let outside input or other local users harm the user's shell session or files:
- unbounded input: a remote response, a file at a configurable/shared/predictable path (/tmp, user- or other-writable files) or output of a process that reads such data is read completely (StdioCollector/FileView with no cap, resp.read(), json.load of a network body) in the always-loaded shell or a long-lived helper;
- a process or network request that can hang the shell or leak a child: no deadline/timeout or teardown on a fetch, a polled helper, or a command whose binary is looked up through an untrusted PATH;
- file safety: predictable /tmp names, symlink-following or truncating writes, loose permissions, replacing a user's settings after a read error;
- secrets (tokens, passwords, phrases) put in argv, logs or world-readable files; sudo/pkexec/systemd/etc changes beyond what the plugin documents;
- remote code that is downloaded and executed or installed without pinning or checksum verification;
- shell/Lua injection (variables interpolated into sh -c / bash -c / Lua strings), rich text (Text.AutoText/StyledText) rendering of untrusted text, unvalidated URL schemes passed to xdg-open.
Missing caps and timeouts are NOT blockers, only warnings, when the source is trusted and small: output of a fixed local tool that prints one line or a small JSON (hyprctl, ping, top, a shipped helper), a static file shipped with the plugin, or a state/config file the plugin itself writes under its own XDG directory. If the cap/timeout gap is on remote, shared-path or externally mutable input, it is a blocker.

APPROVE (load = "works") when you cannot point to a defect from A or B. Style issues, hardening ideas that fall under the trusted-and-small exception, and Checker `warn` / `warn experimental` / `heuristic` lines are warnings, never blockers by themselves: a Checker line is a lead, you confirm it in the code. Checker lines with no tag are load/runtime errors and are usually real; verify them. Do not invent problems, but do not approve a plugin that has a group A or B defect.

Every blocker must name the file (as it appears in the source), the line number of the offending statement (count lines from the top of the file), and the concrete cause and construct in backticks, in one or two sentences. State the problem as it is in this code; do not mention commits, SHAs, URLs, earlier reviews, other plugins, or files that are not in the source shown.
Answer with JSON only, no prose:
{"verdict": "approve" | "changes_requested", "load": "works" | "broken" | "unsure", "findings": [{"category": str, "severity": "blocker" | "warning", "file": str | null, "line": int | null, "finding": str}]}
Use `"findings": []` for a clean plugin. Keep each finding under 300 characters."""

def _code(files): return "\n\n".join(f"### {p}\n```\n{c}\n```" for p, c in files.items())
def _m(id_, name, kind, ep, f): return json.dumps({"id": id_, "name": name, "kinds": [kind], "entryPoints": {f: ep}}, indent=2)
_FETCH = ("import QtQuick\nimport Quickshell.Io\n\nItem {\n  id: root\n  implicitWidth: label.implicitWidth\n  property string quote: \"...\"\n"
          "  Text { id: label; text: root.quote; color: \"white\" }\n  Process {\n    id: fetch\n    command: [\"curl\", \"-s\", \"https://quotes.daily-words.dev/v1/random\"]\n"
          "    stdout: StdioCollector { onStreamFinished: root.quote = JSON.parse(text).content }\n  }\n  Timer { interval: 60000; running: true; repeat: true; triggeredOnStart: true; onTriggered: fetch.running = true }\n}\n")
SHOTS = [
    # 1. fixed local tool, one line, polled -> trusted-and-small exception: approve with a warning
    (dict(files={"manifest.json": _m("example.cpu-dot", "CPU Dot", "bar-widget", "BarWidget.qml", "barWidget"),
                 "BarWidget.qml": "import QtQuick\nimport Quickshell.Io\n\nItem {\n  id: root\n  implicitWidth: label.implicitWidth\n  property string load: \"0\"\n  Text { id: label; text: \"CPU \" + root.load + \"%\"; color: \"white\" }\n  Process {\n    id: proc\n    command: [\"sh\", \"-c\", \"top -bn1 | awk '/Cpu/ {print 100-$8}'\"]\n    stdout: StdioCollector { onStreamFinished: root.load = Math.round(parseFloat(text)) }\n  }\n  Timer { interval: 3000; running: true; repeat: true; onTriggered: proc.running = true }\n}\n"},
          rep=["[USB-W10 warn experimental] BarWidget.qml: reads command output or a file with no size cap"]),
     dict(verdict="approve", load="works", findings=[dict(category="unbounded-input-resource", severity="warning", file="BarWidget.qml", line=12, finding="`StdioCollector` collects `top` output without a size cap; harmless here because the fixed local command prints one line, consider a cap.")])),
    # 2. entry point file missing
    (dict(files={"manifest.json": _m("example.notes-panel", "Notes", "bar-widget", "BarWidget.qml", "barWidget"),
                 "NotesPanel.qml": "import QtQuick\n\nRectangle {\n  width: 300; height: 200\n  color: \"#222\"\n  Text { anchors.centerIn: parent; text: \"Notes\"; color: \"white\" }\n}\n"}, rep=[]),
     dict(verdict="changes_requested", load="broken", findings=[dict(category="load:component-not-created", severity="blocker", file="manifest.json", line=None, finding="entryPoints.barWidget is BarWidget.qml, but the plugin ships no BarWidget.qml (only NotesPanel.qml), so the widget cannot be created.")])),
    # 3. QML syntax error
    (dict(files={"manifest.json": _m("example.clock", "Clock", "bar-widget", "BarWidget.qml", "barWidget"),
                 "BarWidget.qml": "import QtQuick\n\nItem {\n  implicitWidth: t.implicitWidth\n  Text {\n    id: t\n    color: \"white\"\n    text: Qt.formatTime(new Date(), \"HH:mm\")\n  Timer {\n    interval: 1000; running: true; repeat: true\n    onTriggered: t.text = Qt.formatTime(new Date(), \"HH:mm\")\n  }\n}\n"}, rep=[]),
     dict(verdict="changes_requested", load="broken", findings=[dict(category="load:component-not-created", severity="blocker", file="BarWidget.qml", line=13, finding="Unbalanced braces: the Text block opened on line 5 is never closed, so the file ends early (Expected token `}`) and the widget fails to load.")])),
    # 4. missing binary
    (dict(files={"manifest.json": _m("example.now-playing", "Now Playing", "bar-widget", "BarWidget.qml", "barWidget"),
                 "BarWidget.qml": "import QtQuick\nimport Quickshell.Io\n\nItem {\n  id: root\n  implicitWidth: t.implicitWidth\n  Text { id: t; color: \"white\"; text: \"...\" }\n  Process {\n    running: true\n    command: [\"spotify-now\", \"--format\", \"{artist} - {title}\"]\n    stdout: SplitParser { onRead: data => t.text = data }\n  }\n}\n",
                 "README.md": "# Now Playing\nShows the current track in the bar.\n"},
          rep=["[USB-D04 heuristic/high] BarWidget.qml: runs `spotify-now`, which is not installed on stock Omarchy. Fix: ship it, declare it, or fall back"]),
     dict(verdict="changes_requested", load="broken", findings=[dict(category="in-use:missing-binary", severity="blocker", file="BarWidget.qml", line=10, finding="Runs `spotify-now`, which is not on stock Omarchy and is neither shipped nor documented, so the widget never shows a track.")])),
    # 5. remote body, no cap, no deadline, polled in the shell -> blocker, load unsure (the v2 prompt said approve here)
    (dict(files={"manifest.json": _m("example.daily-quote", "Daily Quote", "bar-widget", "BarWidget.qml", "barWidget"), "BarWidget.qml": _FETCH}, rep=["[USB-W10 warn experimental] BarWidget.qml: reads command output or a file with no size cap", "[USB-W08 warn experimental] BarWidget.qml: starts a process without a timeout"]),
     dict(verdict="changes_requested", load="unsure", findings=[dict(category="unbounded-input-resource", severity="blocker", file="BarWidget.qml", line=11, finding="`curl` fetches a remote body every minute with no `--max-time` or `--max-filesize`, and `StdioCollector` buffers all of it before `JSON.parse`; a slow or oversized response can stall or exhaust the shell.")])),
    # 6. clean overlay with a heuristic Checker line -> approve, no findings
    (dict(files={"manifest.json": _m("example.quick-launch", "Quick Launch", "overlay", "Overlay.qml", "overlay"),
                 "Overlay.qml": "import QtQuick\nimport Quickshell\nimport Quickshell.Io\n\nItem {\n  id: root\n  property var shell: null\n  property bool opened: false\n  function toggle() { opened = !opened }\n  Process { id: launch; command: [\"uwsm-app\", \"--\", \"alacritty\"] }\n  Rectangle {\n    visible: root.opened\n    width: 240; height: 60; color: \"#1e1e2e\"\n    Text { anchors.centerIn: parent; text: \"Terminal\"; color: \"white\" }\n    MouseArea { anchors.fill: parent; onClicked: { launch.running = true; root.opened = false } }\n    Keys.onEscapePressed: root.opened = false\n  }\n}\n"},
          rep=["[USB-W08 warn experimental] Overlay.qml: starts a process without a timeout"]),
     dict(verdict="approve", load="works", findings=[])),
]
def _prefix():
    m = [{"role": "system", "content": SYSTEM}]
    for inp, out in SHOTS:
        m += [{"role": "user", "content": user_msg(_code(inp["files"]), inp["rep"])}, {"role": "assistant", "content": json.dumps(out)}]
    return m
def messages(code, checker_report, target=None):
    m = _prefix() + [{"role": "user", "content": user_msg(code, checker_report)}]
    if target is not None: m.append({"role": "assistant", "content": json.dumps(target, ensure_ascii=False)})
    return m
def rebuild(msgs):
    """re-wrap a v2-style row (system + shots + final user [+ assistant]) with the v3 system prompt and shots"""
    if msgs[-1]["role"] == "assistant": return _prefix() + msgs[-2:]
    return _prefix() + msgs[-1:]
