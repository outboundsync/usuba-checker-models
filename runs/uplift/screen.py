"""Red-flag screen for hand-check: per Checker pass, list Checker warnings and code smells. Prints one block per pass."""
import json, sys, os, re
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, os.path.join(ROOT, "functest")); import rescore
from usuba import checks
m = sys.argv[1]
for l in open(os.path.join(H, m, "rows.jsonl")):
    r = json.loads(l); fp = r["first_pass_round"]
    if fp is None: continue
    x = r["rounds"][fp]; fs = rescore.parse(x["output"]); task = r["task"]
    code = "\n".join(c for p, c in fs.items() if p.endswith((".qml", ".js", ".sh", ".py")) or "/" in p and "." not in os.path.basename(p))
    flags = [f"{f['rule']}:{f['reason'][:80]}" for f in checks.check(fs) if not checks.blocking(f)]
    io = bool(re.search(r"\bProcess\b|FileView|XMLHttpRequest|execDetached|NotificationServer|Hyprland\.|Pipewire|UPower|SystemTray|Mpris|Socket|IpcHandler|Quickshell\.Services", code))
    smell = [s for s, pat in [("random", r"Math\.random"), ("demo", r"(?i)\bdemo\b|sample data|mock|simulat|fake"), ("TODO", r"TODO|FIXME"),
                               ("hardcoded-%", r"text:\s*\"\d+\s*(%|°|GB|MB)"), ("swallow", r"catch\s*\([^)]*\)\s*\{\s*\}")] if re.search(pat, code)]
    tgt = re.search(r"Implement `([^`]+)`", rescore.hold[r["i"]]["messages"][1]["content"])
    print(f"{m} i={r['i']:2} {task:32} @{fp} io={'Y' if io else 'N'} files={len(fs)} {('target=' + tgt.group(1)) if tgt else ''} smell={smell} warn={flags[:3]}")
