# Same-name repo pairs (audit A12), compared by content at HEAD

| training-side repo | sealed holdout repo | files with Jaccard >= 0.6 |
|---|---|---|
| jankeesvw/omarchy-github-build-monitor | davidmessenger123/omarchy-github-build-monitor | 0 / 3 (max 0.03) |
| jankeesvw/omarchy-notification-center | apurvasaraiya/omarchy-notification-center | 0 / 10 (max 0.05) |

Different code under the same repo name, so the name match was not a content match. The content guard (`holdout_guard.py`) still checks every row against the holdout and Dell fingerprints, so these pairs are protected by content, not by name. Only HEAD was compared; earlier revisions of the jankeesvw repos were not available (history sources are the r4 intermediates).
