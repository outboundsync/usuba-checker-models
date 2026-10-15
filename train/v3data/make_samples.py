#!/usr/bin/env python3
"""SAMPLES.md for the v3 data: 12 full examples across kinds + 3 approve examples + prompt v2->v3 diff. usage: make_samples.py [DIR]"""
import gzip, json, random, re, difflib, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import prompt_v2 as A, prompt_v3 as B
D = sys.argv[1] if len(sys.argv) > 1 else "/workspace/usuba-runs/v3-data"
rows = [json.loads(l) for f in ('train', 'val') for l in gzip.open(f'{D}/{f}.jsonl.gz', 'rt')]
rnd = random.Random(15)
def files(r):
    u = r['messages'][-2]['content']
    return {m.group(1): m.group(2) for m in re.finditer(r"^### (.+?)\n```\n(.*?)\n```$", u, re.S | re.M)}
def ans(r): return json.loads(r['messages'][-1]['content'])
def plugin(r): return r['id'].split(':', 1)[1].rsplit(':', 1)[0] if r['source'] != 'hancore_concrete' else r['id'].split(':')[1]
def snippet(r, f, ctx=5):
    fs = files(r); fn = f['file']; t = fs.get(fn) or next((c for p, c in fs.items() if p.endswith('/' + fn)), None)
    if t is None or not f.get('line'): return '(no line cited)'
    L = t.split('\n'); a = max(0, f['line'] - 1 - ctx); b = min(len(L), f['line'] + ctx)
    return '\n'.join(f"{'>' if i + 1 == f['line'] else ' '}{i + 1:5d}| {L[i][:160]}" for i in range(a, b))
def render(r, why):
    a = ans(r); u = r['messages'][-2]['content']; rep = u.split('## Plugin source')[0].replace('## Checker report\n', '').strip()
    o = [f"### `{r['id']}` — {why}", f"- plugin: `{plugin(r)}`; source: {r['source']}; tokens: {r['tokens']}", f"- Checker report shown to the model:\n```\n{rep[:700]}\n```"]
    for f in a['findings']:
        o.append(f"- cited `{f['file']}:{f['line']}` ({f['category']}, {f['severity']}); code near the line ('>' = cited line):\n```\n{snippet(r, f)}\n```")
    if not a['findings']: o.append("- no findings, so no cited line; files in prompt: " + ", ".join(files(r))[:300])
    o.append("- **full answer taught:**\n```json\n" + json.dumps(a, indent=1, ensure_ascii=False) + "\n```\n")
    return "\n".join(o)
used = set(); ex = []; app = []
def pick(pred, why, out):
    c = [r for r in rows if pred(r) and r['id'] not in used and r['tokens'] < 20000 and r['split'] == 'train']
    r = rnd.choice(c); used.add(r['id']); out.append(render(r, why))
kinds = ["unbounded-input-resource", "process-lifecycle-timeouts", "file-safety-symlink-perms", "secrets-credentials", "privileged-system", "remote-code-pinning", "rich-text-markup-injection", "shell-lua-injection", "url-scheme-network", "install-deps-packaging"]
for k in kinds: pick(lambda r, k=k: r['source'] == 'hancore_concrete' and any(f['category'] == k for f in ans(r)['findings']), "HANCORE kind " + k, ex)
pick(lambda r: r['source'] == 'dell_broken_verified' and ans(r)['findings'][0]['category'].startswith('load:'), "Dell-derived load bug", ex)
pick(lambda r: r['source'] == 'dell_broken_verified' and ans(r)['findings'][0]['category'].startswith('in-use:'), "Dell-derived in-use bug", ex)
pick(lambda r: r['source'] == 'dell_works_verified' and ans(r)['findings'] and ans(r)['findings'][0]['category'] == 'unbounded-input-resource', "APPROVE with an unbounded-input warning (trusted-and-small exception)", app)
pick(lambda r: r['source'] == 'dell_works_verified' and not ans(r)['findings'], "APPROVE clean, no findings", app)
pick(lambda r: r['source'] == 'fix_upstream', "APPROVE after upstream fix (clean)", app)
diff = '\n'.join(difflib.unified_diff(A.SYSTEM.split('\n'), B.SYSTEM.split('\n'), 'prompt_v2.SYSTEM', 'prompt_v3.SYSTEM', lineterm='', n=0))
NOTES = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples_notes.md")).read() if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples_notes.md")) else ""
md = ["# Usuba v3 data — SAMPLES (prompt_v3)", "", f"Rows: {len(rows)}. Every row = prompt_v3 system + 6 synthetic shots + the plugin. Code excerpts come from the exact prompt text of each row (line numbers counted from the top of the file as shown; the model sees no line numbers). Samples are random (seed 15) from train, not hand-picked, so they show the real quality.", "", "## A. 12 examples across kinds", ""] + ex + ["", "## B. 3 approve examples", ""] + app
md += ["", "## C. Reviewer notes on these samples", "", NOTES, "", "## D. Prompt v2 -> v3 diff summary", "",
"**System prompt**",
"- v2: 'Request changes ONLY for a real load/runtime bug'; missing size caps, missing timeouts, hardening ideas = warnings, never blockers; 'Most plugins work'.",
"- v3: two blocker groups. A = load/runtime bugs (load=broken), incl. placeholder endpoints/credentials. B = concrete safety/robustness defects in code that loads (load=unsure): unbounded input on remote/shared-path/mutable sources, no deadline/teardown, file safety, secrets in argv, sudo beyond docs, unpinned remote code, shell/Lua injection, rich-text of untrusted text, URL schemes. Missing caps/timeouts stay warnings ONLY for trusted-and-small sources (fixed local tool, one line/small JSON, shipped static file, plugin's own XDG state/config).",
"- v3 asks for the offending line (counted from the top), the construct in backticks, 1-2 sentences, no URLs/earlier reviews/commits; says unmarked Checker lines are usually real errors and tagged lines are leads to confirm; 'do not approve a plugin with a group A or B defect'.",
"- JSON schema line unchanged (verdict/load/findings with category, severity, file, line, finding).", "",
"**Few-shot shots (synthetic)**: v2 had 5 (approve+uncapped warning, missing entry point, syntax error, missing binary, clean overlay). v3 has 6: shot 1 keeps approve-with-warning, now because the fixed local `top` prints one line; NEW shot 5 = remote `curl` body with no `--max-time`/cap buffered by `StdioCollector` -> changes_requested, load unsure, blocker with line (Checker lines are only `warn experimental`: the blocker comes from the code); the clean overlay stays last.", "",
"**Raw unified diff of SYSTEM**", "```diff", diff, "```"]
open(f"{D}/SAMPLES.md", "w").write("\n".join(md)); print(len(ex), len(app))
