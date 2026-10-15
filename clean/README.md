# clean/ — functest + provenance-cleaned training data (2026-10-12)

Rule (Harris): train only on code merged/reviewed upstream (basecamp/omarchy main, or verified listings in the official
registry plugins.omarchy.org) plus REFERENCE. No synthetic/model-generated rows, no unmerged forks, no unknown provenance,
no frontier (GPT/Claude) outputs. candidates_frontier.jsonl was intentionally NOT produced.

Files
- score_train.py / score_train.json — functest of every gold answer in data/train.jsonl (198 rows). Tree tasks are overlaid on the upstream tree; failures already in the pristine upstream tree are subtracted. House trees are at /workspace/omarchy-<name>.
- build_clean.py → train_clean.jsonl (145 after asset fix) + train_clean_manifest.json (per-row provenance, functest result, drop reasons).
- dedupe2.py → holdout_dupes_all.json (best train match per holdout row), holdout_dupes.json (7 removed, answer line-jaccard >= 0.7), holdout_clean.jsonl (49 rows, has holdout_i). data/holdout.jsonl and functest/results.json are unchanged.
- registry/: catalog_live.json (plugins.omarchy.org/catalog.json, generated 2026-10-12T14:28Z: 5,416 listings, 3,873 verified, 38 builtin),
  scan.py (clones at listingValidatedCommit, classifies LICENSE text, runs functest), selected_ids.json (418 curated), scan.jsonl (results; 1,000 rows incl. 582 from the earlier uncurated pass).
- build_pool.py → pool_registry.jsonl (152 build_from_spec examples) + pool_registry_manifest.json. Clones of kept plugins: /workspace/registry_repos/.

Curation criteria (registry): verified listing; status Available/Manual setup; updated >= 2026-08-15; stars >= 4 (or >= 2 for
panel/service/overlay/bar kinds); max 3 per GitHub owner; LICENSE file text permissive (MIT/Apache/BSD/ISC/MPL) with a copyright line and not a DHH-only fork;
functest pass; >= 2.5k chars of non-manifest code and no placeholder text; <= 90k chars; not a holdout repo; line-jaccard < 0.5 vs every holdout answer, < 0.8 vs train/pool.

Caveats
- "verified" in the registry is the directory's automated snapshot verification, not necessarily human review.
- fix_manifest rows (answer is real, prompt is a synthetic corruption) were dropped as synthetic; restoring them adds 10 passing rows.
- REFERENCE answers = holdout golds; not added to training (would leak the eval).
- runs/fix/train_rft.jsonl (169 rows) is model-generated -> dropped by rule (not scored).
- 107 curated plugins passed but are >90k chars; they need chunking (as build_dataset.py does) to be usable.

## Update 2026-10-12 (round 2)
- Registry "verified" label = reviewed (Harris).
- fix_assets.py: 6 train answers failed only because binary assets (svg/png) can't be in a text answer; re-tested with the upstream
  asset files installed alongside -> all 6 pass. Train functest now 180/198. Remaining 18 failures are real behaviour
  (sudo/pkexec, /etc/pam.d writes in first-party lock/polkit, ~/.config/hypr write, unknown module, fix_manifest trees) and stay excluded.
  score_train.before_assetfix.json keeps the previous scores.
- build_chunked.py → pool_chunked.jsonl (334 rows built, all distinct; 313 after the sealed-holdout guard, see docs/DATA_HOSTING.md; an earlier "328 after final dedupe" figure was stale) from the 107 large curated plugins, using build_dataset.chunk_tasks
  with community limits (manifest+entry, entry file, add-kind, 2 largest components). All 107 were already license-OK (0 license exclusions);
  36 chunks dropped for overlapping a holdout answer (overlap >= 0.5). Rows are slices of plugins that pass functest as a whole; individual chunk rows were not re-run.
- build_final.py → train_final.jsonl (593 rows) + train_final_manifest.json (per-row provenance; exact dups and same-task answer near-dups at
  >= 0.9 line-jaccard removed, which also collapses the paraphrase repeats in our own data: 32 rows).
- Third-party code is now in training text: extend ../NOTICE with the registry repos listed in pool_*_manifest.json before any public release.
