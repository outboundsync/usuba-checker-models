# Scope-v4 r6 gate report

rows 110 (train 98, val 12); prompt `scope-v4` sha a2317251f69e

## Row types
| type | rows |
|---|---|
| clean | 11 |
| extend | 44 |
| triage | 55 |

tier: verified 48, provisional 62
rows with an EMPTY added_findings list: 66 (60.0%; spec needs >= 50%)

## Rows / findings per added-finding slug (floor 15 across train+val)
| slug | findings | rows | verdict |
|---|---|---|---|
| secrets-credentials | 16 | 16 | kept |
| url-scheme-network | 0 | 0 | OUT_OF_SCOPE (below 15) |
| rich-text-markup-injection | 28 | 28 | kept |
| remote-code-pinning | 0 | 0 | OUT_OF_SCOPE (below 15) |
| scope-policy-duplicate | 0 | 0 | OUT_OF_SCOPE (below 15) |
| listing-metadata-docs | 0 | 0 | OUT_OF_SCOPE (below 15) |
| user-config-modification | 0 | 0 | OUT_OF_SCOPE (below 15) |

added-finding basis (location/attribution): {"reviewer-line/strict": 8, "llm-located/tie-gate-verified": 10, "reviewer-line/tie-quoted-verified": 5, "llm-located/strict": 9, "re-anchored/strict": 3, "re-anchored/tie-gate-verified": 2, "re-anchored/tie-quoted-verified": 4, "reviewer-line/tie-gate-verified": 3}

## Triage items
items 199 over 80 rows: confirm 117, dismiss 82 (41.2%; spec target 25-35%, M3 needs real-confirm to dominate)

| rule | confirm | dismiss |
|---|---|---|
| USB-A01 | 5 | 0 |
| USB-A02 | 10 | 0 |
| USB-A04 | 2 | 0 |
| USB-A08 | 6 | 1 |
| USB-B01 | 1 | 0 |
| USB-F01 | 2 | 0 |
| USB-H07 | 2 | 0 |
| USB-HC01 | 20 | 4 |
| USB-HC02 | 1 | 6 |
| USB-HC04 | 6 | 0 |
| USB-HC10 | 1 | 1 |
| USB-HC15 | 3 | 18 |
| USB-HC16 | 1 | 1 |
| USB-HC17 | 3 | 0 |
| USB-HC19 | 1 | 2 |
| USB-J01 | 7 | 0 |
| USB-L01 | 1 | 0 |
| USB-L02 | 1 | 1 |
| USB-L03 | 3 | 0 |
| USB-Q01 | 4 | 0 |
| USB-W01 | 7 | 12 |
| USB-W03 | 1 | 0 |
| USB-W04 | 1 | 4 |
| USB-W05 | 2 | 7 |
| USB-W06 | 1 | 3 |
| USB-W07 | 7 | 6 |
| USB-W08 | 4 | 6 |
| USB-W09 | 1 | 1 |
| USB-W10 | 13 | 9 |

triage label basis (items): {"default-confirm: teachers disagree (provisional)": 17, "two open-weights teachers agree (provisional)": 82, "reviewer finding with exact location": 6, "verified upstream fix changed this location": 17, "reviewer finding of the same family on this file": 2, "provisional: line unchanged in >= 3 later versions, warn-level": 38, "verified: fix commit removed or changed the cited line": 18, "hardware-observed break with the Checker FAIL; the sweep note names this location": 19}

## Approve mix by source
| source | rows | approve | share of rows |
|---|---|---|---|
| hancore_concrete | 44 | 6 | 40.0% |
| version_history | 44 | 35 | 40.0% |
| dell_broken_verified | 13 | 0 | 11.8% |
| hancore_clean_approve | 9 | 9 | 8.2% |

approve total 50 (45.5%)
Dell-sweep-pipeline share (dell_* + nudged): 13/110 = 11.8%. Dell-key scores must be reported next to HANCORE-holdout and clean-set scores.

## Exact-quote pass rate (re-checked from the prompt text)
triage quotes in cited file: 199/199 = 100.0%; added quotes in file: 44/44 = 100.0%; within 2 lines of the cited line: 44/44
schema structure errors: 0

## 12 samples (deterministic)

### hancore_concrete:ekkostech/omarchy-cockpit:7cfc775375:provisional  [extend, provisional, hancore_concrete]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-W01",
   "file": "Cockpit.qml",
   "line": 0,
   "decision": "confirm",
   "reason": "Code executes 'ekkos-personal' directly without checking existence first, unlike the guarded check on line 142.",
   "quote": "command: [\"ekkos-personal\", \"work\", \"status\"]"
  }
 ],
 "added_findings": [
  {
   "category": "secrets-credentials",
   "severity": "warning",
   "file": "bin/cockpit-scan",
   "line": 15,
   "quote": "terminals=$(jq -c -n --argjson c \"$clients\" --arg ps \"$ps_out\" '",
   "finding": "Passing window titles containing private browser or document names via --argjson exposes sensitive user activity in process arguments visible to other users on the system.",
   "fix": "Replace --argjson with --arg and pass a sanitized, pre-filtered JSON string that excludes title fields before invoking jq."
  }
 ],
 "verdict": "approve"
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

### hancore_concrete:ozdadirri/omarchy-sydney-train-planer:dd9dfaff01:provisional  [extend, provisional, hancore_concrete]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-A08",
   "file": "Panel.qml",
   "line": 87,
   "decision": "confirm",
   "reason": "Assigns to read-only facade property which throws; must use setter method instead.",
   "quote": "root.bar.centerHoverRevealSuppressed = value"
  },
  {
   "rule": "USB-W10",
   "file": "BarWidget.qml",
   "line": 0,
   "decision": "confirm",
   "reason": "FileView reads a file without imposing a size limit, which may cause unbounded memory usage",
   "quote": "FileView {"
  },
  {
   "rule": "USB-W08",
   "file": "Model.js",
   "line": 54,
   "decision": "confirm",
   "reason": "The code sets a timeout using '--max-time' on line 55, so the curl call is not missing a timeout.",
   "quote": "\"curl\", \"-fsS\","
  },
  {
   "rule": "USB-HC01",
   "file": "Model.js",
   "line": 54,
   "decision": "confirm",
   "reason": "The curlArgs function uses --max-time but omits --max-filesize, allowing a hostile endpoint to stream unbounded data into memory.",
   "quote": "\"curl\", \"-fsS\","
  },
  {
   "rule": "USB-HC01",
   "file": "Panel.qml",
   "line": 272,
   "decision": "confirm",
   "reason": "curl lacks --max-filesize or pipe to head, allowing unbounded data download despite --max-time.",
   "quote": "command: [\"curl\", \"-fsS\", \"--max-time\", \"6\", \"https://ipapi.co/json/\"]"
  }
 ],
 "added_findings": [
  {
   "category": "secrets-credentials",
   "severity": "blocker",
   "file": "Model.js",
   "line": 56,
   "quote": "\"-H\", \"Authorization: apikey \" + String(apiKey || \"\"),",
   "finding": "The API key is concatenated directly into the curl command arguments, exposing the secret in the process list visible to other users on the system via tools like ps or /proc.",
   "fix": "Replace string concatenation with an environment variable injection: pass the key via { env: { AUTH_KEY: apiKey } } to the spawn call and use '-H', 'Authorization: apikey $AUTH_KEY' with shell expansion enabled."
  }
 ],
 "verdict": "changes_requested"
}
```

### hancore_concrete:hackxit/omarchy-chromecast:5e6832e63d:provisional  [extend, provisional, hancore_concrete]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-W01",
   "file": "install.sh",
   "line": 0,
   "decision": "dismiss",
   "reason": "The variable 'dst' is a local Python variable assigned from an environment variable, not an external command execution.",
   "quote": "dst = os.environ['DST_FONT']"
  }
 ],
 "added_findings": [
  {
   "category": "rich-text-markup-injection",
   "severity": "blocker",
   "file": "Chromecast.qml",
   "line": 97,
   "quote": "statusText = String(data.text || \"\")",
   "finding": "Untrusted text from network sources is assigned directly to a rich-text label without sanitization. This allows an attacker on the local network to inject arbitrary HTML or QML markup into the UI, potentially executing scripts or defacing the interface.",
   "fix": "Replace direct assignment with a sanitized plain-text extraction: statusText = stripRichText(String(data.text || \"\"))"
  }
 ],
 "verdict": "changes_requested"
}
```

### hancore_concrete:devinblack001/omarchy-transfer-manager:6897b8704a:provisional  [extend, provisional, hancore_concrete]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-W10",
   "file": "Service.qml",
   "line": 0,
   "decision": "confirm",
   "reason": "Collecting unbounded command output into memory without size limit may cause resource exhaustion",
   "quote": "stdout: StdioCollector { id: listStdout; waitForEnd: true }"
  },
  {
   "rule": "USB-W04",
   "file": "install.sh",
   "line": 56,
   "decision": "dismiss",
   "reason": "Variable is validated via readlink comparison and user confirmation before removal; not an unchecked or predictable path.",
   "quote": "rm -rf \"$PLUGIN_LINK\""
  },
  {
   "rule": "USB-W01",
   "file": "install.sh",
   "line": 0,
   "decision": "confirm",
   "reason": "The script calls ok_to_write which is not a standard command and lacks declared dependencies.",
   "quote": "if ok_to_write \"$FTCTL_BIN\"; then"
  }
 ],
 "added_findings": [
  {
   "category": "rich-text-markup-injection",
   "severity": "blocker",
   "file": "Panel.qml",
   "line": 139,
   "quote": "text: transfer.lastError || \"Could not reach the transfer daemon.\"",
   "finding": "The code renders untrusted error strings directly into a QML Text element without enforcing plain text mode, allowing an attacker to inject malicious markup or scripts via crafted filenames or error messages.",
   "fix": "Change the Text element to explicitly set textFormat: Text.PlainText to prevent markup injection when displaying transfer.lastError."
  }
 ],
 "verdict": "changes_requested"
}
```

### hancore_concrete:cad0p/omarchy-threads:81485ac71a  [extend, verified, hancore_concrete]
```json
{
 "scripts_triage": [],
 "added_findings": [
  {
   "category": "secrets-credentials",
   "severity": "blocker",
   "file": "bin/thread-store",
   "line": 109,
   "quote": "jq -c --argjson e \"$json\" --argjson now \"$(now_ms)\" \\",
   "finding": "Passing sensitive notification JSON as a command-line argument exposes private data in /proc, allowing other local users to read secrets from the process list.",
   "fix": "Replace the --argjson e \"$json\" pattern by piping the JSON via stdin or using a temporary file with restricted permissions instead of exposing it in argv."
  }
 ],
 "verdict": "changes_requested"
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

### r7:birajdotdev__omacore:a5122c0a07:fix:provisional  [triage, provisional, version_history]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-W05",
   "file": "Panel.qml",
   "line": 227,
   "decision": "confirm",
   "reason": "Line 227 explicitly claims 'no sudo needed' while the rule detected a privileged sudo call in the associated installation logic.",
   "quote": "+ \"Install it now — no sudo needed, it goes into ~/.local.\""
  },
  {
   "rule": "USB-W10",
   "file": "Service.qml",
   "line": 0,
   "decision": "dismiss",
   "reason": "The cited line calls a function with a static string, not reading command output or a file.",
   "quote": "_noteDisconnected(\"Could not read the earbuds' status.\")"
  },
  {
   "rule": "USB-HC15",
   "file": "Panel.qml",
   "line": 227,
   "decision": "confirm",
   "reason": "Line 227 explicitly claims 'no sudo needed' for the install action, contradicting the rule's detection of a privileged operation.",
   "quote": "+ \"Install it now — no sudo needed, it goes into ~/.local.\""
  }
 ],
 "added_findings": [],
 "verdict": "approve"
}
```

### r7:tuxclaw__familiar:60c1cdf564:fix:provisional  [triage, provisional, version_history]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-W10",
   "file": "Service.qml",
   "line": 0,
   "decision": "dismiss",
   "reason": "mktemp creates a file with a random name, not unbounded output from a command.",
   "quote": "+ \"tmp=$(mktemp \\\"$config_dir/.shell.json.XXXXXX\\\"); \""
  },
  {
   "rule": "USB-L03",
   "file": "Bar.qml",
   "line": 11,
   "decision": "confirm",
   "reason": "The code declares omarchyPath as a required property on line 11, but the host assigns it only after load, causing the Loader to fail.",
   "quote": "required property string omarchyPath"
  },
  {
   "rule": "USB-L03",
   "file": "Bar.qml",
   "line": 12,
   "decision": "confirm",
   "reason": "Line 12 declares barWidgetRegistry as required, but the host assigns it only after load, causing the Loader to fail with an uninitialized property error.",
   "quote": "required property var barWidgetRegistry"
  },
  {
   "rule": "USB-L03",
   "file": "Bar.qml",
   "line": 13,
   "decision": "confirm",
   "reason": "Line 13 declares barConfig as a required property, but the host assigns it only after load, causing the Loader to fail with an uninitialized property error.",
   "quote": "required property var barConfig"
  }
 ],
 "added_findings": [],
 "verdict": "approve"
}
```

### vh_security:cossssmin/omarchy-xkcd:ce5ef201ba  [triage, verified, version_history]
```json
{
 "scripts_triage": [
  {
   "rule": "USB-W08",
   "file": "Xkcd.qml",
   "line": 157,
   "decision": "confirm",
   "reason": "Line 157 executes curl with -L to follow redirects on an unvalidated comic.img URL, enabling SSRF attacks.",
   "quote": "\"curl -fsSL \\\"$1\\\" | wl-copy --type \\\"$2\\\"\", \"sh\", url, type]"
  },
  {
   "rule": "USB-HC01",
   "file": "Xkcd.qml",
   "line": 157,
   "decision": "confirm",
   "reason": "The curl command on line 157 lacks a byte-size limit like --max-filesize, allowing unbounded data streaming.",
   "quote": "\"curl -fsSL \\\"$1\\\" | wl-copy --type \\\"$2\\\"\", \"sh\", url, type]"
  }
 ],
 "added_findings": [],
 "verdict": "approve"
}
```

### r7:anishfn__omarchy-widgets:21307d7201:clean  [clean, verified, version_history]
```json
{
 "scripts_triage": [],
 "added_findings": [],
 "verdict": "approve"
}
```

### r7:anderskeis__keisvibe:f6db38d7a5:clean  [clean, verified, version_history]
```json
{
 "scripts_triage": [],
 "added_findings": [],
 "verdict": "approve"
}
```
