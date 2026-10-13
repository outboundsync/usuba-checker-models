"""Print the logic-bearing lines (functions, data properties, commands, handlers) of an answer dir."""
import sys, os, re
for d in sys.argv[1:]:
    print("#####", d)
    for root, _, fs in os.walk(d):
        for f in sorted(fs):
            if f == "manifest.json" or f.endswith((".md", ".svg", ".png")): continue
            p = os.path.join(root, f); src = open(p, errors="replace").read()
            keep = [l.rstrip() for l in src.splitlines() if l.strip() and not re.match(r"\s*(anchors|font|color|Layout|width|height|radius|spacing|implicit|border|margins|horizontalAlignment|verticalAlignment|elide|opacity|visible|z:|x:|y:|//|import|}\s*$|\{\s*$)", l)]
            print(f"== {os.path.relpath(p, d)} ({len(src)} chars)"); print("\n".join(k[:150] for k in keep[:60]))
