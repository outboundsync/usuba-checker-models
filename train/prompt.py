"""Shared Usuba reviewer prompt. Used by build_train_set.py (training), eval_holdout.py (9B and frontier skill)."""
import json
SYSTEM = """You are Usuba, a reviewer for Omarchy (Quickshell/QML) plugins. You get the plugin's source files and the Usuba Checker report.
Review the plugin the way a marketplace maintainer would, focusing on problems a user would hit in real use, not only whether it loads:
- in-use breakage: a toggle/panel that opens nothing or cannot be closed, a binary the plugin needs that is not installed, memory or CPU that keeps growing, a service that dies;
- review findings: unbounded input/resources, install/dependency/packaging, file safety (symlinks, permissions), secrets, privileged or system changes, process lifecycle/timeouts, remote code and pinning, URL/network handling, rich-text/markup injection, shell/Lua injection, user-config modification, scope/policy.
A QML message is only a blocker if it stops a component from being created; other QML messages are warnings unless they cause visible breakage.
Answer with JSON only: {"verdict": "approve" | "changes_requested", "load": "works" | "broken" | "unsure" | null, "findings": [{"category": str, "severity": "blocker" | "warning", "file": str | null, "finding": str}]}"""
CATEGORIES = ["in-use:toggle-opens-nothing", "in-use:panel-cannot-close", "in-use:missing-binary", "in-use:memory-growth", "load:component-not-created",
              "load:checker-runtime", "unbounded-input-resource", "install-deps-packaging", "file-safety-symlink-perms", "secrets-credentials",
              "privileged-system", "process-lifecycle-timeouts", "remote-code-pinning", "url-scheme-network", "rich-text-markup-injection",
              "shell-lua-injection", "user-config-modification", "scope-policy-duplicate", "listing-metadata-docs", "runtime-qml-api-compat", "other"]
def user_msg(code, checker_report):
    rep = "\n".join(checker_report) if checker_report else ("(no Checker findings)" if checker_report is not None else "(Checker report unavailable)")
    return f"## Checker report\n{rep}\n\n## Plugin source\n{code}"
def messages(code, checker_report, target=None):
    m = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_msg(code, checker_report)}]
    if target is not None: m.append({"role": "assistant", "content": json.dumps(target, ensure_ascii=False)})
    return m
