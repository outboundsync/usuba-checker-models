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

# The label space (audit A3). SCORED_SLUGS are the HANCORE-style categories the eval scores; LOAD_SLUGS fold the ~80 load/runtime/in-use variants of the r4 rows into a few families.
# OUT_OF_SCOPE = scored slugs the dataset cannot supply (fewer than MIN_PER_SLUG rows): they are NOT listed in the prompt and the build asserts nobody labels them;
# the eval score for them must be reported as n/a (documented in the r5 GATE_REPORT), not as recall 0.
MIN_PER_SLUG = 15   # findings across train+val
SCORED_SLUGS = ["unbounded-input-resource", "install-deps-packaging", "file-safety-symlink-perms", "secrets-credentials", "privileged-system",
                "rich-text-markup-injection", "shell-lua-injection", "process-lifecycle-timeouts", "remote-code-pinning", "url-scheme-network",
                "scope-policy-duplicate", "user-config-modification", "listing-metadata-docs"]
OUT_OF_SCOPE = ["scope-policy-duplicate", "install-deps-packaging", "url-scheme-network", "listing-metadata-docs", "user-config-modification", "process-lifecycle-timeouts", "rich-text-markup-injection"]   # r5 counts: see GATE_REPORT section 7
LOAD_SLUGS = ["load:component-not-created", "load:panel-lifecycle", "load:undefined-reference", "load:unknown-type", "load:missing-import", "load:invalid-binding",
              "in-use:missing-binary", "in-use:missing-file", "in-use:invalid-command-arg", "in-use:stale-or-wrong-display", "in-use:placeholder-data",
              "runtime-qml-api-compat", "runtime:logic-error", "runtime:error-handling", "runtime:state-or-race"]
SLUGS = [x for x in SCORED_SLUGS if x not in OUT_OF_SCOPE] + LOAD_SLUGS
_EXPLICIT = {"packaging:missing-file": "in-use:missing-file",            # NOT install-deps-packaging: a file the plugin forgot to ship is not a dependency-install problem
             "security:placeholder-credential": "in-use:placeholder-data",  # NOT secrets-credentials: a placeholder key is dummy data, not a leaked secret
             "missing-file": "in-use:missing-file", "in-use:missing-asset": "in-use:missing-file", "in-use:missing-qml-module": "load:missing-import", "in-use:missing-module": "load:missing-import",
             "in-use:missing-script": "in-use:missing-binary", "load:invalid-command-path": "in-use:missing-binary", "load:missing-file": "in-use:missing-file",
             "in-use:data-loss": "runtime:logic-error", "runtime:missing-implementation": "runtime:logic-error", "load:runtime-error": "runtime:logic-error",
             "runtime:invalid-api": "runtime-qml-api-compat", "runtime:invalid-command-arg": "in-use:invalid-command-arg",
             "runtime:readonly-property-assignment": "load:invalid-binding", "qml:property-shadowing": "load:invalid-binding",
             "runtime:undefined-property": "load:undefined-reference", "runtime:undefined-method": "load:undefined-reference", "runtime:method-missing": "load:undefined-reference",
             "runtime:method-not-found": "load:undefined-reference", "qml:undefined-method": "load:undefined-reference", "qml:undefined-property": "load:undefined-reference",
             "syntax:type-not-found": "load:unknown-type", "logic:placeholder-data": "in-use:placeholder-data", "load:placeholder-data": "in-use:placeholder-data"}
_PREFIX = [("load:undefined", "load:undefined-reference"), ("load:reference-error", "load:undefined-reference"), ("load:method-not-found", "load:undefined-reference"),
           ("load:property-not-found", "load:undefined-reference"), ("load:missing-property", "load:undefined-reference"), ("load:signal-not-found", "load:undefined-reference"),
           ("load:unknown-property", "load:undefined-reference"), ("load:unknown-type", "load:unknown-type"), ("load:unknown-qml-type", "load:unknown-type"),
           ("load:type-", "load:unknown-type"), ("load:qml-type-error", "load:unknown-type"), ("load:missing-module", "load:missing-import"), ("load:missing-import", "load:missing-import"),
           ("load:missing-native-module", "load:missing-import"), ("load:module-not-installed", "load:missing-import"), ("load:import-not-found", "load:missing-import"),
           ("load:qml-import-error", "load:missing-import"), ("load:invalid-", "load:invalid-binding"), ("load:signal-handler", "load:invalid-binding"),
           ("load:property-assignment", "load:invalid-binding"), ("load:qml-property-error", "load:invalid-binding"), ("config:", "in-use:placeholder-data")]
def to_slug(cat):
    """map a training-row category onto the r5 label space; None = unmappable (the finding is dropped and counted)"""
    if cat in SLUGS: return cat
    if cat in _EXPLICIT: return _EXPLICIT[cat]
    for p, s in _PREFIX:
        if cat.startswith(p): return s
    return None
SLUG_MAP = _EXPLICIT

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
