"""Every relative Markdown link [text](path) in a tracked .md file must point at a file or directory that exists (anchors and URLs are ignored)."""
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')


def _md_files():
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode:
        return []
    return out.stdout.split()


def test_relative_markdown_links_resolve():
    bad = []
    for f in _md_files():
        text = re.sub(r"```.*?```", "", open(os.path.join(ROOT, f), encoding="utf-8", errors="replace").read(), flags=re.S)
        for m in LINK.finditer(text):
            u = m.group(1)
            if re.match(r"^(https?:|mailto:|#)", u):
                continue
            p = u.split("#")[0]
            if not p:
                continue
            t = os.path.join(ROOT, p[1:]) if p.startswith("/") else os.path.normpath(os.path.join(ROOT, os.path.dirname(f), p))
            if not os.path.exists(t):
                bad.append(f"{f}: {u}")
    assert not bad, bad
