# Packaging: how the two repos fit together (audit G)

`usuba-checker-scripts` is an installable package (`usuba-checker`, import `usuba_checker`, stdlib only; see its README "Install as a package").
This repo consumes it and owns data, training and release.

* **Pin:** `requirements-checker.txt` pins `usuba-checker` by full commit SHA. Locally use `pip install -e ../usuba-checker-scripts`.
  The Omarchy reference tree is not in the wheel: set `FT_OMARCHY` (an editable/sibling checkout uses the in-repo `dell-ref/`).
* **Contract test:** `tests/test_checker_contract.py` checks that the sibling checkout is at or after the pin and that `usuba_checker.check_files()` returns a versioned
  report (`schema_version`, `rules_hash`, reference-tree hash, `policies`) plus `holdout_ids()` and `scoring`. It is skipped when no sibling checkout exists.
* **What is NOT done yet:** `code_blob`, the prompts and `checker_report` still live in this repo's `train/` and the scripts repo's `run_eval.py` imports them from here,
  so the dependency is still two-way. Moving them behind `usuba_checker` (so the eval imports a single renderer from one package) is the next step; it needs the
  r5 prompt and `code_blob` to be frozen first. CI cannot check out the private sibling with the default `GITHUB_TOKEN`; a read-only deploy key/PAT would let
  the contract test run in CI (Harris's call).
* Bump the pin deliberately in one commit together with the change that needs it.
