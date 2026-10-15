# Opus audit closure (Janus, 2026-10-15)

Each item of `usuba-runs/opus-audit/VERDICTS.md` was checked against repo HEAD by grep/test, not by trusting commit messages. Status: CLOSED, PARTIAL or OPEN. "Evidence" is what to re-check.

| Item | Status | Evidence / remainder |
|---|---|---|
| A1 shared code_blob | CLOSED | canonical in `usuba_checker`; parity test |
| A2/A3 r5 gate | CLOSED (supply limits stay) | gate report: approves 100% real-clean, 0 twins |
| A4 weighted_micro_loss | CLOSED | CPU tests |
| A5 llm_client fail-closed | CLOSED | error budget; failures not cached |
| A6 gz loader, r5 bundled | CLOSED | |
| A7 `--prompt` required, thread-safe fork timeout | CLOSED | the two `test_checker_timeout` tests are flaky under heavy machine load (pass alone and on re-run) |
| A8 eval cadence in epochs, max_hours 11 | CLOSED | |
| A9 base_revision pinned | CLOSED | |
| A10 midcheck bundled | CLOSED | |
| A11 trap, terminal markers, INSTANCE_MAX_HOURS | CLOSED | |
| A12 content guard | CLOSED | extended by cd37f39 (Jaccard, same-name, same-author) |
| B1/B3/B4/B5 scorer, CIs, v1/v2 relabel | CLOSED | bootstrap + Wilson CIs |
| C1 sandbox runtime hardened | CLOSED | |
| C2 hitcheck hardened | CLOSED | `hc_safe`; probed live on the Dell, see `scripts/docs/SANDBOX_PROOF.md` |
| C3 /tmp sys.path, shell=True, eval | CLOSED | |
| D1 regex | CLOSED | |
| D2 refpaths raises ReferenceTreeMissing | CLOSED | |
| D3-D8 | PARTIAL | only D1-D6 evidenced in 8b4b31d; D7/D8 not independently verified |
| D7 broad `except Exception` | OPEN | about 89 in scripts, 56 in models remain |
| D9 pardons | PARTIAL, needs Harris | opt-in `FT_STRICT_D9`; default pardons unchanged (`docs/POLICY_D9.md`) |
| E strict attribution | CLOSED | b32af72 |
| F1/F3/F4/F8 | CLOSED | 1dbcb80 |
| F2 raw generations | OPEN | still 13 matches |
| F5 release tags | CLOSED (plan only) | no tags exist, per rule |
| F7 legacy | PARTIAL | legacy/ moved; 53 tracked .log files remain |
| G pyproject/pin | CLOSED | rest of G deferred by design |
| H lock/pins | PARTIAL | uv.lock done; hard-coded `/workspace` remains in `export_gguf.py` (9), `paths.py` (4), `export_parity.py` (1) |
| I | DEFERRED by design | |
| J CI | CLOSED | tests.yml fixed in dd1e786 |

Environmental test note: `test_launch_vast::test_failed_rent_destroys_instance` fails on this box only because its subprocess python lacks `pyyaml`; not a repo defect.
