"""scrub() copied from hancore/build_reviewer.py (that module runs its build on import)."""
import re, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "functest"))
from usuba import hancore_rules as HR
SEC = [re.compile(p) for p, _ in HR.SECRET_PATS[:7]] + [re.compile(r"(?i)((?:api[_-]?key|secret|token|password|passwd)\w*\s*[:=]\s*[\"'`])([A-Za-z0-9_\-+/=.]{16,})([\"'`])")]
def scrub(s, handles=()):
    for i, r in enumerate(SEC):
        s = r.sub((lambda m: m.group(1) + "<REDACTED>" + m.group(3)) if i == len(SEC) - 1 else "<REDACTED_SECRET>", s)
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+\b", lambda m: m.group(0) if m.group(0).endswith(("noreply.github.com",)) and False else "<email>", s)
    s = re.sub(r"/home/[\w.-]+", "/home/user", s)
    s = re.sub(r"(?<![\w/])@([A-Za-z0-9-]{2,39})\b(?![./])", lambda m: m.group(0) if m.group(1) in ("param", "returns", "media", "import", "keyframes") else "@user", s)
    return s
