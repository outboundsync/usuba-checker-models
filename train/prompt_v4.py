"""Usuba reviewer prompt v4 (r5 data). Derived from prompt_v3 with the audit fixes:
  * A1/E  the code is rendered by code_blob.py (label-independent order/caps, truncation markers, every line prefixed with its number); shots use the same renderer
  * A3    the allowed category slugs are listed in the system prompt (the scored label space, SLUGS below)
  * E     few-shot plugins changed so their themes (now-playing/spotify, quote fetcher) no longer match sealed-holdout plugins, and shot 7's finding is no longer a
          near-copy of a synthetic training target
Same interface as prompt_v3: SYSTEM, SHOTS, messages(code, checker_report, target=None). `code` is the string from code_blob.code_blob(files).
PROMPT_SHA256 identifies the exact system prompt + shots (recorded in every row's meta and every result file)."""
import json, hashlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prompt_v3 as V3
from prompt import user_msg
from code_blob import code_blob

# The label space. Scored HANCORE-style slugs + the load/runtime families the Dell-sourced rows use. norm_cat() in the eval maps free text onto these.
SCORED_SLUGS = ["unbounded-input-resource", "install-deps-packaging", "file-safety-symlink-perms", "secrets-credentials", "privileged-system",
                "rich-text-markup-injection", "shell-lua-injection", "process-lifecycle-timeouts", "remote-code-pinning", "url-scheme-network",
                "scope-policy-duplicate", "user-config-modification", "listing-metadata-docs"]
LOAD_SLUGS = ["load:component-not-created", "load:panel-lifecycle", "in-use:missing-binary", "runtime-qml-api-compat", "runtime:logic-error"]
SLUGS = SCORED_SLUGS + LOAD_SLUGS
# Fine-grained families of the training rows are folded into the label space with this table (builders use it; an unmapped slug is dropped and counted).
SLUG_MAP = {"packaging:missing-file": "install-deps-packaging", "security:placeholder-credential": "secrets-credentials"}

_ADD = ("\n\nEvery shown line starts with its line number (`  12| code`); cite that number as `line`. A file marked `(truncated: ...)` or `(omitted: ...)` is not fully shown: do not report defects in the part you cannot see.\n"
        "Allowed `category` values (use exactly one of these slugs): " + ", ".join(SLUGS) + ".")
_s = V3.SYSTEM.replace("(count lines from the top of the file)", "(the number printed at the start of the line)")
SYSTEM = _s.replace("\nAnswer with JSON only, no prose:", _ADD + "\nAnswer with JSON only, no prose:", 1)
assert SYSTEM != V3.SYSTEM and _ADD in SYSTEM

_SWAP = [("example.now-playing", "example.disk-health"), ("Now Playing", "Disk Health"), ("spotify-now", "smartstat"), ("--format", "--brief"), ("{artist} - {title}", "{dev}"),
         ("Shows the current track in the bar.", "Shows drive health in the bar."), ("never shows a track", "never shows drive health"),
         ("example.daily-quote", "example.build-status"), ("Daily Quote", "Build Status"), ("quotes.daily-words.dev", "ci.example-builds.dev"), ("v1/random", "v1/status"),
         ("root.quote", "root.status"), ("property string quote", "property string status"), (".content", ".state")]
def _swap(o):
    if isinstance(o, str):
        for a, b in _SWAP: o = o.replace(a, b)
        return o
    if isinstance(o, dict): return {_swap(k): _swap(v) for k, v in o.items()}
    if isinstance(o, list): return [_swap(x) for x in o]
    return o
_SHOT7 = "`Panel.qml` declares `toggle()` as its only entry function; with no `open(payloadJson)` or `close()` the shell has nothing to call, so the panel never appears."
SHOTS = []
for k, (inp, out) in enumerate(V3.SHOTS):
    inp, out = _swap(inp), _swap(out)
    if k == 6: out["findings"][0]["finding"] = _SHOT7
    SHOTS.append((inp, out))
def _code(files): return code_blob(files)
def _prefix():
    m = [{"role": "system", "content": SYSTEM}]
    for inp, out in SHOTS:
        m += [{"role": "user", "content": user_msg(_code(inp["files"]), inp["rep"])}, {"role": "assistant", "content": json.dumps(out)}]
    return m
PROMPT_SHA256 = hashlib.sha256(json.dumps(_prefix(), sort_keys=True).encode()).hexdigest()
def messages(code, checker_report, target=None):
    m = _prefix() + [{"role": "user", "content": user_msg(code, checker_report)}]
    if target is not None: m.append({"role": "assistant", "content": json.dumps(target, ensure_ascii=False)})
    return m
