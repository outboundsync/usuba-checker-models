# Scope-v4 r6 gate report

rows 90 (train 82, val 8); prompt `scope-v4` sha a2317251f69e

## Row types
| type | rows |
|---|---|
| clean | 10 |
| extend | 27 |
| triage | 53 |

tier: verified 45, provisional 45
rows with an EMPTY added_findings list: 63 (70.0%; spec needs >= 50%)

## Rows / findings per added-finding slug (floor 15 across train+val)
| slug | findings | rows | verdict |
|---|---|---|---|
| secrets-credentials | 0 | 0 | OUT_OF_SCOPE (below 15) |
| url-scheme-network | 0 | 0 | OUT_OF_SCOPE (below 15) |
| rich-text-markup-injection | 27 | 27 | kept |
| remote-code-pinning | 0 | 0 | OUT_OF_SCOPE (below 15) |
| scope-policy-duplicate | 0 | 0 | OUT_OF_SCOPE (below 15) |
| listing-metadata-docs | 0 | 0 | OUT_OF_SCOPE (below 15) |
| user-config-modification | 0 | 0 | OUT_OF_SCOPE (below 15) |

added-finding basis (location/attribution): {"reviewer-line/strict": 3, "llm-located/tie-gate-verified": 7, "reviewer-line/tie-quoted-verified": 2, "llm-located/strict": 9, "reviewer-line/tie-gate-verified": 1, "re-anchored/strict": 3, "re-anchored/tie-gate-verified": 1, "re-anchored/tie-quoted-verified": 1}

## Triage items
items 146 over 68 rows: confirm 109, dismiss 37 (25.3%; spec target 25-35%, M3 needs real-confirm to dominate)

| rule | confirm | dismiss |
|---|---|---|
| USB-A01 | 4 | 0 |
| USB-A02 | 9 | 0 |
| USB-A04 | 2 | 0 |
| USB-A08 | 9 | 0 |
| USB-B01 | 1 | 0 |
| USB-F01 | 2 | 0 |
| USB-H07 | 2 | 0 |
| USB-HC01 | 21 | 3 |
| USB-HC02 | 2 | 2 |
| USB-HC04 | 2 | 0 |
| USB-HC15 | 5 | 0 |
| USB-HC16 | 1 | 1 |
| USB-HC19 | 5 | 0 |
| USB-HC20 | 1 | 0 |
| USB-J01 | 7 | 0 |
| USB-L01 | 1 | 0 |
| USB-L02 | 1 | 1 |
| USB-Q01 | 4 | 0 |
| USB-W01 | 3 | 10 |
| USB-W04 | 1 | 3 |
| USB-W05 | 3 | 2 |
| USB-W06 | 1 | 0 |
| USB-W07 | 6 | 3 |
| USB-W08 | 2 | 5 |
| USB-W10 | 14 | 7 |

triage label basis (items): {"two open-weights teachers agree (provisional)": 72, "default-confirm: teachers disagree (provisional)": 11, "reviewer finding with exact location": 24, "verified upstream fix changed this location": 15, "reviewer finding of the same family on this file": 1, "hardware-observed break with the Checker FAIL; the sweep note names this location": 23}

## Approve mix by source
| source | rows | approve | share of rows |
|---|---|---|---|
| hancore_concrete | 48 | 20 | 53.3% |
| dell_broken_verified | 17 | 4 | 18.9% |
| version_history | 12 | 8 | 13.3% |
| hancore_clean_approve | 9 | 9 | 10.0% |
| dell_works_verified | 3 | 3 | 3.3% |
| nudged_approve | 1 | 1 | 1.1% |

approve total 45 (50.0%)
Dell-sweep-pipeline share (dell_* + nudged): 21/90 = 23.3%. Dell-key scores must be reported next to HANCORE-holdout and clean-set scores.

## Exact-quote pass rate (re-checked from the prompt text)
triage quotes in cited file: 146/146 = 100.0%; added quotes in file: 27/27 = 100.0%; within 2 lines of the cited line: 27/27
schema structure errors: 0

## 12 samples (deterministic)

### hancore_concrete:harshith292002/omarchy-system-monitor:55244bf680:provisional  [extend, provisional, hancore_concrete]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-W01",
   "file": "discover-sensors.sh",
   "line": 0,
   "decision": "confirm",
   "reason": "The script uses `shopt`, which may not be available in the default Omarchy environment and isn’t declared as a dependency.",
   "quote": "shopt -s nullglob"
  }
 ],
 "added_findings": [
  {
   "category": "rich-text-markup-injection",
   "severity": "blocker",
   "file": "Panel.qml",
   "line": 183,
   "quote": "\"Load \" + loadText() + (metrics.activeInterface !== \"\" ? \" · \" + metrics.activeInterface : \"\"),",
   "finding": "Untrusted data from metrics.activeInterface is concatenated directly into a rich-text tooltip string without sanitization. This allows an attacker to inject arbitrary HTML or QML markup via the network interface name, potentially executing code or altering the UI layout.",
   "fix": "Replace the concatenation with a call to a sanitization helper: \"Load \" + loadText() + (metrics.activeInterface !== \"\" ? \" · \" + escapeHtml(metrics.activeInterface) : \"\")"
  }
 ],
 "verdict": "changes_requested"
}
```

### hancore_concrete:shawnyeager/briotune:5739950b93  [extend, verified, hancore_concrete]
```json
{
 "scripts_triage": [],
 "added_findings": [
  {
   "category": "rich-text-markup-injection",
   "severity": "blocker",
   "file": "Panel.qml",
   "line": 289,
   "quote": "if (parsed.model) root.modelName = String(parsed.model)",
   "finding": "Untrusted input from a USB device is assigned directly to a property rendered as rich text, allowing an attacker to inject malicious markup or trigger resource loading via crafted model strings.",
   "fix": "Replace the assignment with a sanitized version that strips HTML tags: if (parsed.model) root.modelName = String(parsed.model).replace(/<[^>]*>/g, '')"
  }
 ],
 "verdict": "changes_requested"
}
```

### hancore_concrete:ranjithrajv/omarchy-plugin-ideas:a8cb9fb229:provisional  [extend, provisional, hancore_concrete]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-W10",
   "file": "Panel.qml",
   "line": 0,
   "decision": "confirm",
   "reason": "FileView reads a file without limiting its size, matching the rule about unbounded reads",
   "quote": "FileView {"
  },
  {
   "rule": "USB-W10",
   "file": "Service.qml",
   "line": 0,
   "decision": "confirm",
   "reason": "FileView reads a file without limiting its size, matching the rule about unbounded file reads",
   "quote": "FileView {"
  },
  {
   "rule": "USB-HC01",
   "file": "Panel.qml",
   "line": 85,
   "decision": "confirm",
   "reason": "curl command lacks --max-filesize or -o with size limits, allowing unbounded data download despite time limit.",
   "quote": "\"curl\", \"-fsS\", \"--max-time\", \"10\","
  },
  {
   "rule": "USB-HC01",
   "file": "Service.qml",
   "line": 55,
   "decision": "confirm",
   "reason": "curl lacks --max-filesize or -o with size limits; --max-time only limits duration, allowing unbounded data streaming.",
   "quote": "\"curl\", \"-fsS\", \"--max-time\", \"10\","
  }
 ],
 "added_findings": [
  {
   "category": "rich-text-markup-injection",
   "severity": "blocker",
   "file": "Panel.qml",
   "line": 335,
   "quote": "text: ideaRow.modelData.title",
   "finding": "Untrusted discussion titles from remote sources are assigned directly to a QML Text item with rich-text enabled, allowing attackers to inject malicious markup or execute scripts.",
   "fix": "text: Qt.escape(ideaRow.modelData.title)"
  }
 ],
 "verdict": "changes_requested"
}
```

### hancore_concrete:joejoeflyn/jot:ab308cc9e2:provisional  [extend, provisional, hancore_concrete]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-A02",
   "file": "Noty.qml",
   "line": 701,
   "decision": "confirm",
   "reason": "The rule states onRight is not a valid signal for NotyTab, so the handler will never fire as intended.",
   "quote": "onRight: root.onRight"
  },
  {
   "rule": "USB-A02",
   "file": "Noty.qml",
   "line": 736,
   "decision": "confirm",
   "reason": "The code assigns a handler to 'onRight' on NotyTab, but the rule states this signal does not exist on the component.",
   "quote": "onRight: root.onRight"
  },
  {
   "rule": "USB-A02",
   "file": "Noty.qml",
   "line": 770,
   "decision": "confirm",
   "reason": "Line 770 assigns to `onRight` as a property, but the rule states it is a signal, making this assignment ineffective.",
   "quote": "onRight: root.onRight"
  },
  {
   "rule": "USB-A02",
   "file": "Noty.qml",
   "line": 919,
   "decision": "confirm",
   "reason": "The handler `onRight` is assigned but not listed in the valid signals for `NotyEditor`, so it will never fire.",
   "quote": "onRight: root.onRight"
  },
  {
   "rule": "USB-A02",
   "file": "Noty.qml",
   "line": 1014,
   "decision": "confirm",
   "reason": "The code assigns a handler to `onRight`, but the rule states `NotyMenu` does not have this signal, so the handler will never fire.",
   "quote": "onRight: root.onRight"
  },
  {
   "rule": "USB-J01",
   "file": "NotyEditor.qml",
   "line": 73,
   "decision": "confirm",
   "reason": "The identifier `bodyText` is used but not declared in the provided scope, causing a runtime ReferenceError.",
   "quote": "bodyText.forceActiveFocus()"
  },
  {
   "rule": "USB-W07",
   "file": "Noty.qml",
   "line": 93,
   "decision": "confirm",
   "reason": "Interpolating variables into a shell command string allows command injection if the values contain special characters.",
   "quote": "settingsWriteProc.command = [\"bash\", \"-c\", \"mkdir -p \" + JSON.stringify(dbDir) + \" && cat << 'EOF' > \" + JSON.stringify(settingsPath) + \"\\n\" + JSON.stringify(s, null, 2) + \"\\nEOF\"]"
  },
  {
   "rule": "USB-L01",
   "file": "Noty.qml",
   "line": 29,
   "decision": "confirm",
   "reason": "The root Item at line 29 lacks required open() and close() functions for panel lifecycle management.",
   "quote": "id: root"
  },
  {
   "rule": "USB-L02",
   "file": "BarWidget.qml",
   "line": 17,
   "decision": "confirm",
   "reason": "The plu
```

### hancore_concrete:themediastandard/omarchy-drive-speedtest:0270f41b62:provisional  [extend, provisional, hancore_concrete]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-W10",
   "file": "Panel.qml",
   "line": 0,
   "decision": "confirm",
   "reason": "The Process reads stdout into a StdioCollector without any size limit, potentially unbounded data",
   "quote": "stdout: StdioCollector {"
  }
 ],
 "added_findings": [
  {
   "category": "rich-text-markup-injection",
   "severity": "blocker",
   "file": "Panel.qml",
   "line": 332,
   "quote": "text: modelData.display",
   "finding": "Untrusted device model strings from lsblk are rendered directly as rich text without sanitization. A malicious USB device could embed markup tags in its model name to inject arbitrary formatting, links, or scripts into the interactive panel.",
   "fix": "Change the binding to explicitly treat the content as plain text: text: Qt.escape(modelData.display)"
  }
 ],
 "verdict": "changes_requested"
}
```

### hancore_concrete:vianney-g/omarchy-aelf:8b8d1a3e0a  [extend, verified, hancore_concrete]
```json
{
 "scripts_triage": [],
 "added_findings": [
  {
   "category": "rich-text-markup-injection",
   "severity": "blocker",
   "file": "Model.js",
   "line": 113,
   "quote": "return String(html)",
   "finding": "Arbitrary HTML markup from the API is returned without sanitization, allowing an attacker to inject malicious tags like images that trigger unbounded resource fetching or execution when rendered as rich text.",
   "fix": "return sanitizeHtml(String(html))"
  }
 ],
 "verdict": "changes_requested"
}
```

### version_history:liambateman/omarchy-countdown:e1c2d6d867:broken  [triage, verified, version_history]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-Q01",
   "file": "BarWidget.qml",
   "line": 61,
   "decision": "confirm",
   "reason": "Line 61 uses IpcHandler without importing Quickshell.Io, causing duplicate lifecycle bindings that trigger open and close actions twice.",
   "quote": "IpcHandler {"
  }
 ],
 "added_findings": [],
 "verdict": "changes_requested"
}
```

### hancore_concrete:jexmarc/omarchy-spacexai-usage:50e4030f0c:provisional  [triage, provisional, hancore_concrete]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-HC02",
   "file": "update.py",
   "line": 164,
   "decision": "dismiss",
   "reason": "The code uses urllib.request.urlopen with a timeout, which inherently limits the read size and prevents unbounded blocking.",
   "quote": "body = resp.read()"
  },
  {
   "rule": "USB-HC20",
   "file": "update.py",
   "line": 161,
   "decision": "confirm",
   "reason": "The code calls urllib.request.urlopen at line 163 with a Request object that may contain Authorization headers, allowing credentials to be sent to untrusted redirect targets.",
   "quote": "req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)"
  }
 ],
 "added_findings": [],
 "verdict": "approve"
}
```

### hancore_concrete:18orkidea/omarchy-ai-writer:5b4d88d1c5  [triage, verified, hancore_concrete]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-HC01",
   "file": "bin/ai-writer",
   "line": 223,
   "decision": "confirm",
   "reason": "Line 223 uses curl with --max-time but lacks --max-filesize, allowing unbounded response data.",
   "quote": "response=$(curl -sS --max-time 180 \"$HOST/api/chat\" -d \"$payload\" 2>&1)"
  }
 ],
 "added_findings": [],
 "verdict": "approve"
}
```

### hancore_concrete:jburchel/omarchy-jarvis:884b5c8a76:provisional  [triage, provisional, hancore_concrete]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-W10",
   "file": "BarWidget.qml",
   "line": 0,
   "decision": "dismiss",
   "reason": "FileView is a QML component for reading files, not executing shell commands; the rule targets command output or unsafe file reads, which does not apply here.",
   "quote": "FileView {"
  },
  {
   "rule": "USB-HC19",
   "file": "bin/jarvis",
   "line": 44,
   "decision": "confirm",
   "reason": "Line 44 runs pip install for pip, edge-tts, and piper-tts without --hash or pinned versions.",
   "quote": "\"$JARVIS_VENV/bin/pip\" install -q --upgrade pip edge-tts piper-tts"
  },
  {
   "rule": "USB-HC19",
   "file": "bin/jarvis",
   "line": 107,
   "decision": "confirm",
   "reason": "Line 107 installs openwakeword via pip without the --hash flag to verify package integrity.",
   "quote": "\"$JARVIS_VENV/bin/python\" -c 'import openwakeword' 2>/dev/null || \"$JARVIS_VENV/bin/pip\" install -q openwakeword"
  }
 ],
 "added_findings": [],
 "verdict": "approve"
}
```

### dell_works_verified:28allday/omarchy-hey-cal:r00038-373bc6706c  [clean, verified, dell_works_verified]
```json
{
 "scripts_triage": [],
 "added_findings": [],
 "verdict": "approve"
}
```

### hancore_clean:thenetworkchuck/omarchy-coffee-counter:43b63f40ba  [clean, verified, hancore_clean_approve]
```json
{
 "scripts_triage": [],
 "added_findings": [],
 "verdict": "approve"
}
```
