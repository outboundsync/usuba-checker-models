"""Automatic sanity checks for harvested answers (beyond the functest grader)."""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runs/clean")); sys.path.insert(0, os.path.join(ROOT, "validator")); sys.path.insert(0, os.path.join(ROOT, "functest/dell_env"))
from loopdet import loopy
from build_parse import parse
from binaries import SYSTEM_BINS, OMARCHY_BINS
SH_WORDS = set("if then else elif fi for while until do done case esac in function return local export set unset shift exit break continue read eval exec source . : [[ ]] { } ! cd pwd trap wait declare typeset let printf echo test true false type hash alias getopts ulimit umask builtin time".split())
STR = r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\''
def _cmd_words(script, shipped, funcs):
    bad = set()
    for seg in re.split(r"\|\||&&|[|;\n`]|\$\(", script):
        w = seg.strip().split()
        while w and re.match(r"^\w+=", w[0]): w = w[1:]
        if not w: continue
        if re.match(r"^[^\s()]+\)", seg.strip()): continue  # case pattern
        c = w[0].strip("()'\"")
        if not c or c.startswith(("$", "#", "-", ">", "<", "&")) or c in SH_WORDS or c in funcs or not re.match(r"^[\w./+\[-]+$", c): continue
        if re.match(r"^\d", c): continue
        b = os.path.basename(c)
        if "/" in c:
            if c.lstrip("./") in shipped or os.path.basename(c) in {os.path.basename(s) for s in shipped} or c.startswith(("/usr/bin/", "/bin/")) and b in SYSTEM_BINS: continue
            if c.startswith(("/dev", "/tmp", "/proc", "/sys")): continue
            bad.add(c); continue
        if c not in SYSTEM_BINS and c not in OMARCHY_BINS: bad.add(c)   # functest system_bins + Omarchy's own omarchy-* bins
    return bad
def check(output, finish):
    """returns list of failure reasons (empty = sane)"""
    why = []
    if finish != "stop": why.append(f"truncated/finish={finish}")
    if output.count("```") % 2: why.append("unbalanced-fence(truncation)")
    if loopy(output): why.append("loop")
    files = parse(output)
    if not files: return why + ["no-files"]
    shipped = set(files)
    m = files.get("manifest.json")
    if m:
        try:
            mid = str(json.loads(m).get("id", ""))
            if mid == "omarchy" or mid.startswith("omarchy.") or mid.startswith("omarchy-"): why.append(f"reserved-id:{mid}")
        except Exception: why.append("manifest-unparseable")
    # helper scripts / assets referenced but not shipped
    allt = "\n".join(files.values())
    for ref in set(re.findall(r"[\"'/]((?:[\w.-]+/)*[\w.-]+\.(?:sh|py|js|mjs|qml|bash|json|svg|png))[\"']", allt)):
        r = ref.lstrip("./")
        if r in shipped or any(s.endswith("/" + r) or r.endswith("/" + s) or os.path.basename(s) == os.path.basename(r) for s in shipped): continue
        if r[0].isupper() and r.endswith(".qml"): continue          # likely qs.Ui / Commons component
        if r in ("manifest.json", "settings.json", "config.json", "state.json", "cache.json") or "/" not in r and r.endswith(".json"): continue  # runtime data files
        if r.endswith((".svg", ".png", ".json")): continue          # icons/data may be theme/user files
        why.append(f"unshipped-helper:{r}")
    # binaries: argv[0] of command arrays, sh -c scripts, shipped shell scripts
    funcs = set(re.findall(r"^\s*(?:function\s+)?([\w-]+)\s*\(\)\s*\{", allt, re.M)) | set(re.findall(r"^\s*function\s+([\w-]+)", allt, re.M))
    bad = set()
    for arr in re.findall(r"\[\s*((?:\"[^\"\n]*\"|'[^'\n]*')\s*(?:,\s*(?:[^\]\n]*?))?)\]", allt):
        toks = [a or b for a, b in re.findall(STR, arr)]
        if not toks: continue
        c0 = toks[0]
        if c0 in ("sh", "bash", "dash") and len(toks) >= 3 and toks[1] in ("-c", "-lc"): bad |= _cmd_words(toks[2], shipped, funcs); continue
        if c0 in ("sh", "bash", "dash", "python3", "python", "node") and len(toks) >= 2: continue
        if not re.match(r"^[\w./+-]+$", c0) or " " in c0: continue
        # only treat as command if array is used as a command (heuristic: within 'command' / 'exec' context)
        ctx = allt[max(0, allt.find(arr) - 40):allt.find(arr)]
        if re.search(r"(command|exec|execDetached|startDetached|run|argv|cmd)\w*\s*[:=(]\s*\[?\s*$", ctx): bad |= _cmd_words(c0, shipped, funcs)
    for b in sorted(bad)[:6]: why.append(f"binary-not-on-system:{b}")
    pre = output.split("### ", 1)[0]
    if len(pre) > 400 or re.search(r"(?m)^(Wait|Actually|Let's|I will|I'll)\b", pre): why.append("leaked-reasoning-prose")
    # --- stricter filters (parent steering 06:42): grader gaps the fixer loop games ---
    code = {p: c for p, c in files.items() if p != "manifest.json"}
    if not any(p.endswith(".qml") for p in code): why.append("manifest-only/no-qml")
    ct = "\n".join(code.values())
    for pidn in re.findall(r"Process\s*\{\s*id\s*:\s*(\w+)", ct):
        if re.search(r"\b" + pidn + r"\.start\s*\(", ct): why.append("invented-api:Process.start"); break
    if re.search(r"\bProcess\.start\b", ct): why.append("invented-api:Process.start")
    for name, rx in INVENTED:
        if re.search(rx, ct): why.append("invented-api:" + name)
    for name, rx in FAKE:
        if re.search(rx, ct, re.I): why.append("fake-data:" + name)
    if re.search(r"\bon[A-Z]\w*\s*:\s*(\{\s*)?console\.(log|warn|info)\([^()]*(\([^()]*\)[^()]*)*\)\s*;?\s*\}?\s*$", ct, re.M): why.append("console-log-only-handler")
    m = re.search(r"\b(xinput|setxkbmap|onboard|xdotool|xrandr|xclip|xsel|xprop|xset|xmodmap|xwininfo)\b(?=[\"' ])", ct)
    if m: why.append("x11-tool:" + m.group(1))
    return why
INVENTED = [("Quickshell.exec(", r"Quickshell\.exec\s*\("), ("Service.call", r"\bService\.call\b"), 
            ("Process.onFinished", r"Process\s*\{[^{}]*\bonFinished\s*:"), ("Qt.clipboard", r"\bQt\.clipboard\b"),
            ("new SequentialAnimation", r"new\s+(Sequential|Parallel|Number|Property)Animation"), ("hyprctl background", r"hyprctl[\"', ]+\s*background"),
            ("hyprsunset enable/disable", r"hyprsunset[\"', ]+\s*(enable|disable)\b"),
            ("Quickshell.Window", r"\bQuickshell\.Window\b"), ("FileView.open/readAll/write/close/mkdir", r"\.(readAll|mkdir)\s*\(|FileView\.(ReadOnly|WriteOnly|Truncate)"),
            ("resolvedUrl-in-command(file:// argv)", r"command\s*:\s*\[[^\]]*Qt\.resolvedUrl\([^)]*\)\s*(\.toString\(\))?\s*[,\]]"),
            ("File{} type", r"(?m)^\s*File\s*\{"), ("execDetached-callback/return", r"execDetached\(\s*\[[^\]]*\]\s*,\s*function|=\s*Quickshell\.execDetached"),
            ("Hyprland.windows/onClientAdded", r"\bHyprland\.windows\b|onClient(Added|Removed)"), ("readAllStandardOutput", r"readAllStandardOutput"),
            ("XMLHttpRequest-file", r"XMLHttpRequest[\s\S]{0,300}file://")]
FAKE = [("simulated", r"\bsimulat(e|ed|ion|ing)\b"), ("placeholder", r"\bplaceholder\s+(data|value|logic|implementation)|//\s*placeholder"),
        ("mock/dummy/fake", r"\b(mock|dummy|fake)\s*(data|values?|items?|results?|response)\b"), ("hardcoded", r"\bhard-?coded\b"),
        ("stub-setter-echo", r"(?m)^\s*set-[\w-]+\)\s*echo\b"),
        ("fake-sunset/example.com/api_key", r"today sunset|\w+\.example\.com|api_key=MTA|isn't a standard binary|as a proxy for"),
        ("TODO", r"\bTODO\b|in a real (plugin|implementation|app)"), ("random-data", r"Math\.random\(\)\s*\*\s*\d{2,}")]
