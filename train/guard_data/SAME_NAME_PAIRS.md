# Same-name repo pairs (audit A12), compared by content at HEAD

| training-side repo | sealed holdout repo | files with Jaccard >= 0.6 |
|---|---|---|
| jankeesvw/omarchy-github-build-monitor | davidmessenger123/omarchy-github-build-monitor | 0 / 3 (max 0.03) |
| jankeesvw/omarchy-notification-center | apurvasaraiya/omarchy-notification-center | 0 / 10 (max 0.05) |

Different code under the same repo name, so the name match was not a content match. The content guard (`holdout_guard.py`) still checks every row against the holdout and Dell fingerprints, so these pairs are protected by content, not by name. Only HEAD was compared; earlier revisions of the jankeesvw repos were not available (history sources are the r4 intermediates).

## r6 rule (2026-10-15)
`holdout_guard.Guard` now also rejects any row whose repo name or manifest-id name equals a holdout / Dell-key plugin name (normalised, >= 6 chars) unless the pair is in
`SAME_NAME_ALLOW.json` (the two pairs above), rejects a row when ANY single file has shingle Jaccard >= 0.5 with a holdout / Dell-key file, and rejects a same-author row
at per-file Jaccard >= 0.3. `fingerprints.json.gz` gained `holdout_meta` / `dell_meta` (repo + manifest id per tree; hashes arrays unchanged, verified byte-equal on rebuild).
Applied to the final r5 train+val: 51 of 473 rows fail (file 27, same-name 19, same-author 4, content 1), so r5 is not re-publishable as is.
