# Commit-attribution hand spot-check (item 5, 2026-10-15)

Question: for the 174 plugins whose reviewed SHA changed between the legacy loader and the r5 'strict' loader, is the r5 strict SHA right? 20 plugins drawn with `random.Random(2026)` from the 174 (sorted URL list), each read by hand (every reviewer comment, date, the SHA it names and the context of the mention).

**Result: 18 of 20 wrong or unsupported, 2 defensible (one of them with a contaminated finding). Threshold was 2+: it is exceeded by a wide margin.** Cause: the loader counted SHAs *carried forward* to comments that name no SHA (or only a fixed-in SHA), so the plurality came from inheritance, and most plugins are serial re-reviews at a new HEAD per comment (1 finding per SHA). Ties broke arbitrarily.

Fix in the r6 builder (`label_filters.plurality_table`): plurality over SHAs the finding comment itself names (no carry-forward, no back-fill); DROP ties, unresolvable and sha-after-review plugins; the row commit must equal the plurality SHA; the cited line must exist at that SHA. Over all 4,799 reviewed plugins: ok 2,382, tie 1,989, unresolvable 428.

| # | plugin | legacy SHA | r5 strict SHA | explicit mentions | verdict | note |
|---|---|---|---|---|---|---|
| 1 | original-david-knight/omarchy-arctis-headset | 923a0f4d | a12c48d8 | ok 923a0f4d [2, 1] | W | explicit mentions 923a x2 vs a12c x1; the strict loader counted a12c twice via carry-forward |
| 2 | mtolhuys/fathom | 6e032d00 | f411d9a6 | tie [1, 1, 1] | W | every comment names a different HEAD (6e03/f411/a7fc, one mention each): choice arbitrary; strict count came from a comment about a later fix |
| 3 | IM0001GT/omarchy-screens | 67ec4938 | f1f7eae6 | ok 67ec4938 [2, 1, 1, 1] | W | strict f1f7 had 3 'findings' but 2 are comments about later commits (bd83.., 1138..) inherited by carry-forward; explicit plurality is 67ec |
| 4 | TomFaulkner/lotus | 61f3f06e | e30c9253 | ok e30c9253 [2, 1, 1, 1] | OK* | e30c explicit x2 is the plurality, but one of its findings is a re-review of 06c6.. mis-read as e30c: right SHA, one contaminated finding |
| 5 | rdoupe-omarchy/omarchy-underpants | 665d2d17 | aab69655 | tie [1, 1, 1, 1] | W | explicit 1 mention per SHA (tie); the 09-12 comment reviews ca617.. but was attributed to aab6.. |
| 6 | ByteMirror/omarchy-kirinuki | 8f79c9bd | c7faf22f | tie [1, 1] | W | tie c7fa / f994 (1 each) |
| 7 | TECHNOCRAFT27/floating-waybar | 953a2bd9 | d2afa8dd | tie [1, 1] | W | tie d2af / 953a; strict d2af only wins via an inherited comment about 953a |
| 8 | mahan2079/omarchy-troubleshooter | c69c5c77 | d06e93cd | ok c69c5c77 [2, 1, 1] | W | explicit plurality is c69c (2) = legacy; strict d06e got its 3 from 2 inherited comments about 80bd/a11d fixes |
| 9 | hpolthof/omarchy-plugin-totp | e90bed7b | d9ad6b99 | tie [2, 2, 1, 1] | W | tie e90b / d9ad (2 each) |
| 10 | ArtMoreno/omarchy-trackpoint | 24209b08 | acbe73ab | ok acbe73ab [2, 1, 1] | OK | acbe explicit x2 (target-commit correction + complete review): defensible |
| 11 | eddygarcas/omarchy-workspaces-preview | 13aa753f | 5e2ffda9 | tie [1, 1, 1, 1] | W | tie, 1 mention each; strict 5e2f carries a comment about 42c9 |
| 12 | C0d3C0r34u5/VMaker | 84fa2b65 | a5ff05cd | tie [1, 1, 1, 1] | W | tie, 1 mention each across 4 HEAD re-reviews |
| 13 | akafrmn/omarchy-galaxy-buds-pro | 3afc31a4 | 0ea73249 | tie [1, 1] | W | tie 3afc / 0ea7 |
| 14 | BibekBhusal0/omarchy-better-lock | 45b93366 | 96911032 | tie [1, 1, 1, 1] | W | tie, six SHAs x1 |
| 15 | yeet-src/omarchy-yeet-ai | 782f1b24 | 3d51f9b0 | tie [1, 1, 1] | W | tie, three SHAs x1 |
| 16 | derekross/opal | 93483ddd | 1102c5a0 | tie [1, 1, 1, 1] | W | tie, 18 SHAs x1 (serial re-reviews) |
| 17 | mbradaschia/oma-zotero-launcher | 30c963b9 | bd055834 | tie [1, 1, 1] | W | tie, three SHAs x1 |
| 18 | BearThomas/omarchy-luogu | 2e93e192 | 8166ae9b | tie [1, 1, 1, 1] | W | tie, six SHAs x1 |
| 19 | joeyvigil/omarchy-taskbar | 724c8f31 | 4b901f1d | tie [1, 1] | W | tie 724c / 4b90 |
| 20 | KOUSTAV2409/omnicast | a476a74e | b1fd23cd | tie [1, 1, 1, 1] | W | tie, four SHAs x1 |
