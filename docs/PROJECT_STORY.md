# The Usuba project: the full story so far

**Status date: 2026-10-15 (Thursday), written ~23:05 MT. Author: Harris Kenny, OutboundSync.**
This document replaces the planned blog post. The earlier draft (`docs/post/draft.md`, Fizzy card #121, "Usuba technical post") is kept for history and marked superseded. This is a *working* history, not a launch announcement. It is meant to be safe to publish: it contains no keys, no personal contact details, and no private device data.

---

## 0. Status at the top (2026-10-15)

**Short version: the Checker model has not cleared the bar. It is "In Training". We are publishing that either way.**

| Item | State on 2026-10-15 ~23:05 MT |
|---|---|
| Checker scripts (deterministic static + runtime checks, `usuba-checker-scripts`) | Working and hardware-verified: agrees with the Dell answer key on 90/90 decided plugins (measured, Oct 13). This is the real, measured win of the project. |
| Checker model (LoRA on Qwen3.5-9B, this repo) | **Did not clear the bar.** Two adapters trained so far (v1, v2). Neither is a usable gate; see section 5. The r7 training data is still being built. |
| r7 training data | **Final shard rebuild running** (shards 0-8 of 40 built, shard 9 in progress at the time of writing). Mining of later plugin versions finished at 22:09 MT. |
| Post-merge chain | **Armed** (the `r7_post_chain.ARMED` file exists, created 22:56 MT). When the final merge and tradeoff table finish, it runs hard checks and launch gates, and if all pass it launches training with no further human step. Scripts are in `v3/r7/chain/`. |
| Row count | **Unknown (TBD).** Final merge has not run. Policy decided by Harris: **we train regardless of row count** (the old "stop below 300 rows" rule now only warns). |
| B0 baseline (stock Qwen3.5-9B, same prompt, schema and post-filter) | On the earlier draft data it is measured (section 8). The r7 B0 run's first job ended with an error on 2026-10-15 22:57 MT (a transient parse error in the log); a Dell-set summary was written but is not published here. Full r7 B0 numbers: **TBD**. |
| Result publication | Whatever the outcome (clears the bar or not), the result goes out under the label **"In Training / did not clear the bar"** and we **invite contribution** (section 15). An announcement is tentatively considered for **Monday 2026-10-19**; that is not committed. |
| Release | Nothing is released. Adapter weights are withheld (hashes only). Repos are private. |

**What "the bar" is.** Defined in `docs/DEFINITION_OF_DONE.md` (gates M1-M7) and, for the earlier verdict-style adapters, in `docs/TRAINING_PLAN.md` (right-reason catches of flagged >= 0.60, false alarms <= 0.15, beats stock Qwen3.5-9B, invented SHA/name rows 0, JSON valid >= 0.98). The hand-labelled sets the final gates need (S1 >= 300 labelled findings, S2 >= 150 reviewed clean plugins, S3 >= 100 adjudicated added findings per eval, S4 >= 50 hand-verified bug locations) **do not exist yet**; every gate computed so far is therefore "provisional", never "pass".

---

## 1. How to read this document

- **MEASURED** = produced by a script or a hardware run, with a source file in this repo or in the cited run directory. Tables labelled *Measured* are only that.
- **CLAIM / PLAN / ASSUMED** = intent, forecasts, thresholds nobody has validated. Marked as such.
- **TBD** = not known today. No number in this document is invented; unknowns are written TBD.
- **Provisional** = produced by a machine (an LLM judge panel or a mechanical rule), not by a human.
- Historic names: the earlier adapters were called "Usuba v1" and "Usuba v2". Under the settled scope (`docs/MODEL_SCOPE.md`): **Checker scripts** = `usuba-checker-scripts`; **Checker model** = the LoRA on Qwen3.5-9B; **System** = both.
- Plugin names, other people's code and review text are not reproduced here beyond what is already in this repo's reports.
- Some numbers come from an internal progress ledger compiled on 2026-10-14 (not in the repo). Where it flagged something "unverified", that flag is kept.

**Vocabulary.** *Omarchy* is the Linux desktop distribution; *Omarchy 4 / Quattro* has a Quickshell/QML shell with plugins. *HANCORE* is the corpus of public reviewer findings on marketplace plugins that we mined and froze a 329-plugin sealed holdout from (300 with findings, 29 without). The *Dell key* is a hardware-labelled answer key: real plugins run on a real Dell laptop under Omarchy 4.0.4 and labelled WORKS or BROKEN by eye.

---

## 2. Timeline (all times MT; sources are git logs of both repos plus run notes)

| Date | What happened |
|---|---|
| Sun 2026-10-11 | Idea: a small local model that writes Omarchy plugins ("Santoku" / `omarchy-specialist`). Dataset v1 with a license-provenance rule: 254 examples, all validator- and qmllint-clean. Vast GPU credit bought. |
| Mon 10-12 (early) | Overnight smoke fine-tunes (7B, 14B). Frontier panel on a static validator. |
| Mon 10-12 (morning) | First test with real Quickshell: the validator scores collapse (e.g. tuned 7B 42/56 on the validator, 8/56 in the functest). Dataset v2 rule: merged and reviewed code only (593 rows, holdout deduped to 49). |
| Mon 10-12 (midday-afternoon) | First clean 7B fine-tune: 10/49 vs GPT 24 and Opus 23 on the old grader. The Dell laptop becomes ground truth; grader rebuilt: old grader 44/58, rebuilt 58/58; sealed blind round 30/32; 90/90 after a fix. Honest rescoring drops everything. Decoding sweep, best-of-16, loop detector. |
| Mon 10-12 (evening) | Dataset v3 + Omarchy 4.0.4-1 refresh; 20 models rescored on the 4.0.4 grader. |
| Tue 10-13 | 27B fine-tune (loops on 31/49). Grader-feedback fix loop: grader passes 5 -> 13, hand-checked real 4. **Pivot: Checker first** (Checker v0.1, standard v0.1 for Omarchy 4.0.4). Frontier uplift study (12 models x 49). Corpus sweep and HANCORE mining. HANCORE holdout frozen (329). Dell sweep: Checker scripts vs key 45/52 -> 52/52. Checker-model training set built (4,592 train / 148 val). Usuba v1 training started. |
| Wed 10-14 | Usuba v1 exam. Right-reason grading shows v1 names the real cause for 1 of 31 flagged-broken plugins. Retrain plan v2. v2 distillation data (open-weights teacher only). Train-launch infrastructure hardened on a GPU instance. |
| Thu 10-15 (early) | Usuba v2 exam: fixes v1's measurable failures but **fails the right-reason bar (2/33 vs stock 8/33)**. Diagnosis, rules v2, v3 data drafts r2-r4. |
| Thu 10-15 (late morning-afternoon) | Public-release scaffolding. Anthropic-terms compliance audit. **Opus 5.5 code audit** and its closure (r5 data builder, shared code_blob, fail-closed LLM client, stricter attribution). Scope settled (triage / extend / explain, advisory). Stock-model baseline (B0) on draft data. |
| Thu 10-15 (afternoon) | **Judge panel** (3 open-weights judges). r6 scope-v4 builder (90 rows). |
| Thu 10-15 (evening) | **r7 history mining** (pilot, then 5,000+ plugins). Train-launch smoke test on a GPU (kill/resume passed). Final shard rebuild started 22:10; post-chain armed 22:56. |
| (planned) | r7 training starts automatically when the chain passes; result published as "In Training / did not clear the bar"; announcement maybe Monday 10-19. |

---

## 3. Epoch 1: Santoku, plugin-generation fine-tunes (Oct 11-13)

**Goal.** A small open model that writes Omarchy Quattro plugins that actually work.

**Data rule v1 (Oct 11).** Every example carries a paper trail: licence at a pinned commit. 254 examples (198 train / 56 holdout), 254/254 validator-clean and qmllint-clean. *(Measured: ledger rows 1; `DATASET.md`.)*

**Overnight smoke fine-tunes (Oct 12, 03:36-06:26).** Qwen2.5-Coder 7B and 14B LoRA fine-tunes. On the static validator the "rejection-sampling" 7B scored 42/56 (stock 7B 31/56), and the 14B 42/56 (stock 24/56). The training data for the "winner" was written by the model itself.

**First real-Quickshell test (Oct 12, ~08:16).** The same outputs, run in headless Quickshell:

| Model | Validator /56 | Functest /56 |
|---|---:|---:|
| Tuned 7B | 42 | **8** |
| Tuned 14B | 42 | **12** |
| Stock 7B / stock 14B | - | 8 / 8 |
| GPT-5.6 | 40 | 29 |
| Opus (big) | 34 | 28 |
| Reference (real plugins) | - | 51 |
*(Measured: `functest/results.json` as recorded in the ledger. Validator column for frontier models: the Oct 12 05:24 panel.)*

> **Own mistake #1.** The static validator said a 7B beat GPT-5.6. It did not: it only passed a pattern check. We trusted a green number before running the code on the real shell. The functest erased the "win".

**Dataset v2 rule (Oct 12, 09:44): merged and reviewed code only.** The RFT set and synthetic rows were dropped; no frontier-model distillation. 593 rows with provenance; holdout deduped from 56 to 49.

**First clean 7B fine-tune.** On the 49-plugin holdout with the then-current grader: **7B 10/49 vs GPT-5.6 24 and Opus 23**, with 40 answers truncated and 41 looping. *(Measured, old grader; `runs/clean/results49_oldft.json` per ledger.)*

**The Dell becomes ground truth (Oct 12, midday-3:38 PM).** Real captures from a Dell laptop on Omarchy 4.0.4 showed the grader passing plugins that visibly did nothing (for example a layout bug). Grader vs hardware on labelled plugins: **old grader 44/58 decided; after the Dell-calibrated rebuild 58/58**; a sealed blind round of unseen plugins agreed **30/32**, **89/90 after a deno fix**, later **90/90** on the 4.0.4 refresh. *(Measured; the ledger notes that an earlier claim of "49/61" could not be reproduced and is not used.)*

**Honest rescoring.** Once loops and truncations counted as failures: 7B fine-tune **6/49**, GPT-5.6 22, Opus 21, stock 14B 5, stock 7B 3. On the Omarchy 4.0.4 grader: human reference 26, GPT-5.6 20, Opus 18, Sonnet 10, Grok-build 10, stock 14B 4, stock 7B 3; v3 7B fine-tune **4/49 with 32 loops**.

| Experiment | Result (Measured) |
|---|---|
| Decoding sweep (6 settings, up to 28k tokens) | all 6-7/49, 30-45 truncated: looping is learned, not a sampling accident |
| Best-of-16 (7B) | pass@1 0.006; pass@16 3/32 (grader) |
| Stock open-base tryout (6 base models) | best stock Qwen3.6-27B 6/49, 0 loops |
| 27B fine-tune (H100, ~3.9 h, about $11.8) | 4/49 by hand (below stock 6/49); **31 of 49 looped** vs 0 for stock |
| Stock 27B + grader-feedback fix loop | grader passes 5 -> 13/49; **hand-verified real passes: 4/49** |
| Rejection-sampling harvest | 398 samples -> 132 grader-pass -> 77 kept; spot check: real 10/30 |

> **Own mistake #2.** In the fix loop the model learned to game the grader (stubs, hardcoded "weather", invented APIs on paths the grader never exercised). 13 grader passes, 4 real. Our harvest likewise kept rows that were not real. A grader that is perfect on real plugins can still have holes once something is searching for them.

> **Own mistake #3.** Some intermediate numbers in our own early drafts were later corrected or could not be reproduced (the 49/61 grader agreement; "2/32" vs 3/32 best-of-16). We record corrections rather than keep the better-looking figure.

**What Epoch 1 taught us.** No Santoku model ever beat its own stock base on real working plugins. A loop is a recipe problem that can make a good base worse. The most valuable output was a grader we could check against hardware.

---

## 4. Epoch 2: the pivot to the Checker (Oct 13)

Because a trustworthy test mattered more than a weak builder, the project pivoted: **build the checker first**, a public, versioned standard for "a working Omarchy plugin" (v0.1 targets Omarchy 4.0.4), where every rule has an id, a reason and a fix hint.

*Measured.* Checker v0.1 (ledger rows 21-27): Dell key **90/90**, fixer calibration 31/31, human reference 27/49 on the new grader; after a full Dell sweep (runs 6-30, 3,942 works / 1,001 broken / 589 unsure labels) the Checker scripts agreed with the sweep key **45/52 -> 52/52**, and **90/90** held after a key regression on the new runtime.

**The uplift study (Oct 13, 12 builder models x 49 prompts, with Checker error messages fed back).** First try -> after Checker fixes (working plugins /49): GPT-5.6 21 -> 40, Opus 17 -> 36, Sonnet 9 -> 35, Kimi K3 3 -> 32, Qwen3.6-27B 4 -> 5, Qwen3-Coder 4 -> 4. Cost about $70 (the run stopped once on credit exhaustion). The point: a good checker lifts frontier models a lot and small ones very little.

Corpus work: 1,452 -> 5,520 catalog rows run through the Checker; HANCORE: 14,692 reviewer items mined; the sealed 329-plugin holdout frozen (300 positive / 29 negative); 4,011 non-holdout reviewer plugins kept for training.

---

## 5. Epoch 3: the Checker model, v1, v2 and the failure (Oct 13-15)

**Plan.** Fine-tune Qwen3.5-9B (Apache-2.0, small enough for a 32 GB laptop at Q4_K_M) to review a plugin on top of the Checker scripts' report. 4,592 train / 148 val rows, each with provenance.

### Usuba v1 (bf16 LoRA, 568 steps, val loss 1.073, about $34 of GPU by log estimate)
*Measured, re-scored with the current three-way scorer (invalid output is never an approval):*

| System (HANCORE 329) | verdict acc | false alarm (of 29 clean) | category recall | invalid |
|---|---:|---:|---:|---:|
| Checker scripts alone | 0.650 | 0.586 | 0.131 | ~0 |
| Stock Qwen3.5-9B | 0.699 | 0.690 | 0.173 | ~77 |
| **Usuba v1** | 0.809 | **0.931** (27 of 29 flagged) | 0.402 | 30 |
| Always "changes requested" | 0.912 | 1.000 | - | - |

Always answering "changes requested" scores 0.912 on this holdout, so accuracy proves little; v1's false alarm rate showed it flags nearly everything. On the Dell key (historical 90-row key, Haiku-judged): accuracy 0.756, broken caught 0.939 (31/33), false alarm 0.351. **Right reason: 1 of 31 flagged-broken plugins** (stock 9B: 9, Sonnet 5.5: 13), and it invented commit SHAs in 44 rows. Diagnosis: ~68% of training rows were HANCORE-style rows with ~98.7% `changes_requested` targets and no clean HANCORE examples; the target template said "Security review at exact commit ..." and the model copied the template.

### Usuba v2 (prompt v2, open-weights teacher data, rebalanced)
*Measured (Dell key, historical 90-row key; right-reason column Haiku-judged, historical):*

| System | verdict acc | false alarm | broken caught | **right reason** | of flagged | invented SHA rows |
|---|---:|---:|---:|---:|---:|---:|
| **Usuba v2 (Q4_K_M)** | 0.844 | **0.018** | 20/33 | **2/33** | 0.10 | 0 |
| Qwen3.5-9B stock | 0.800 | 0.088 | 20/33 | **8/33** | 0.40 | 0 |
| Ministral 14B | 0.822 | 0.175 | 27/33 | 15/33 | 0.56 | 0 |
| Usuba v1 (whole files) | 0.678 | 0.386 | 26/33 | 0/33 | 0.00 | 43 |

**Verdict: v2 failed the right-reason bar.** It fixed what v1 broke that we could measure (false alarms 0.386 -> 0.018, invented SHAs 43 -> 0, JSON valid 1.000), but it mostly approves, and when it flags it is generic: on its 20 flagged plugins 14 findings had **no file** at all (stock: 0 of 20), 13 of 20 used marketplace "security review" boilerplate, and only 6 were concrete load-bug claims with file and line. It never caught the missing-file / manifest `entryPoints` class that stock catches. The open-judge regrade on the 86-row key (after excluding Claude-built plugins) gives v2 right-reason **1/31** vs stock 9/31 on prompt v3. On HANCORE v2 had false alarm 0.586 and category recall 0.106.

**Why (measured, `docs/TRAINING_PLAN.md` "v2 exam diagnosis").** The v2 HANCORE training rows carried **no file:line in 100% of rows**, so the model learned the generic register; most of the training mix was that kind of row. Quantization is not the cause (bf16 merged: right-reason 1/33, false alarm 0.070). *Note: an earlier summary of this failure said "66% of rows generic". We did not find that figure in the sources; the numbers above are the ones in the repo.*

> **Own mistake #4.** We measured accuracy first and read the answers second. Accuracy hid the failure for a full cycle (v1 looked "better" than stock at 0.81 while flagging 27 of 29 clean plugins). From v2 on we gate on right-reason, false alarm and category recall together.
> **Own mistake #5.** We trained v2's targets without file:line, then were surprised the model did not cite files. The data had no teaching signal for the thing we wanted.

---

## 6. Epoch 4: the Opus 5.5 audit and its closure (Oct 15)

An outside read-only review by Claude Opus 5.5 of both repos (models `8029325`, scripts `15e538b`) found many silent failure modes between data and score. The review praised the research practice (documented provenance, a sealed holdout, honest metrics) but found that the code that turns data into a trained model and then into a score has many silent failure modes, some able to make the next model worse or a score wrong without raising an error. Top items: truncation and file order leaking the label (A1); the "approve" training data being the wrong kind, 0 HANCORE-style approves (A2); example weights doing nothing at batch 1 (A4); an invalid answer on a clean plugin counting as a correct approval (B1); the LLM line-check gate passing rows when the API call failed (A5); the eval defaulting to prompt v1 (A7); two watchdogs fighting (A11); the holdout guard matching only `owner/name` (A12); a sandbox that could read the real home directory (C1).

Each item was then checked against HEAD by grep and tests (`docs/OPUS_AUDIT_CLOSURE.md`). *Measured status:* most items **CLOSED** (shared label-independent `code_blob`, fail-closed LLM client, three-way scorer with bootstrap CIs, hardened sandbox and hit-check, stricter commit attribution, content guards including Jaccard/same-name/same-author, CI repaired). **PARTIAL:** D7 (broad `except`, narrowed on active paths only), D9 (pardon default needs Harris), F7 (53 tracked `.log` files remain). **OPEN:** F2 (13 raw-generation matches). The full test suite passed (126) after the fixes.

Related, same day: the Anthropic-terms audit (`docs/ANTHROPIC_TERMS_COMPLIANCE.md`): no Claude output is used as training data or labels; an early Sonnet teacher was removed from history (private repos, approved); Haiku as the right-reason judge was replaced by an open-weights judge; Claude-built plugins were removed from the Dell key (90 -> 86 decided rows).

> **Own mistake #6.** Several of those silent failures were ours (a test of mine leaked a global `time.sleep` patch and made a timeout test look flaky; "gates" that passed on failed calls). We would rather list them than have them found.

---

## 7. Epoch 5: the judge panel (Oct 15)

Labelling by hand is the bottleneck, so a provisional panel of three open-weights judges (Qwen3.5-397B-A17B, gpt-oss-120b, DeepSeek-V3.2, via OpenRouter with zero data retention; no proprietary judges) voted on Checker findings, added findings and clean candidates (`docs/JUDGE_PANEL.md`, tool `tools/judge_panel.py`). Spend **$13.84 of a $25 cap** over 3,195 calls, with an in-flight cap reservation after the first run overshot by $0.07.

*Measured:*

| Set | n | unanimous | Fleiss kappa | needs human |
|---|---:|---:|---:|---:|
| S1 warn-level (scope drafts) | 52 | 48% | 0.28 | 29 |
| S3 added findings | 217 | 49% | 0.38 | 113 |
| S1 hardware-observable items | 378 | 38% | 0.37 | 278 |
| S2 clean candidates | 267 | 53% | 0.30 | 125 |

Against hardware truth, reading code plus the Checker message did not recover the hardware false-alarm labels (for example 18 of 81 "no symptom" items judged false alarms; 49 unsure or no majority). **Conclusion: agreement is moderate to low; the panel orders human review and is not truth.** Roughly half of all items need a human. Panel labels are never used as final labels.

---

## 8. Epoch 6: data builds r2-r6 and the scope settled (Oct 15)

Dataset sizes by build (rows): v1 legacy 1,054 | r2 543 | r3 582 | r4 1,034 | r5 473 | r6 draft 647 | scope-v4 **90**. Each build exposed another honest loss: r5 turned 4.4k candidates into 473 after visibility, guards, caps and attribution. In r6 a strict attribution rule (plurality over commits the comment itself names) and a a hand spot-check of 20 plugins whose attribution changed found **18 wrong under the r5 loader**. We fixed it and accepted the smaller data.

**Scope settled by Harris (`docs/MODEL_SCOPE.md`).** The Checker model **triages** each Checker-scripts finding (confirm, or dismiss with an exact quote), **extends** with findings scripts cannot see, and **explains and fixes**. Release 1 is advisory: the scripts' verdict is the System verdict. Runtime prediction is out of scope.

**B0 baseline, stock Qwen3.5-9B on the same prompt, schema and post-filter (`eval/scope/B0_RESULTS.md`).** About $1.15 of a $5 cap. *Measured, on machine-draft label sets below the Definition-of-Done minimums, so every gate is provisional:*

| B0 result | value |
|---|---|
| Schema-valid answers (Dell / S4 security / holdout) | 0.840 / 0.600 / 0.650 (gate is >= 0.99) |
| Clean plugins that get an added blocker (Dell, 47 plugins) | 14/47 = 0.298 (gate <= 0.15): provisional fail |
| Dismissed real Checker failures | 0/6, meaningless at n=6 |
| S4 bug recall within 3 lines (security kind / all kinds) | 3/60 = 0.050 / 1/60 = 0.017 |
| Holdout category precision / focus-category recall (proxy) | 0.243 / 0.036 |

**r6 scope-v4 gate report (draft, machine labels):** 110 rows (98 train / 12 val): clean 11, extend 44, triage 55; 60% have empty added-findings (spec needs >= 50%); dismiss share 41.2% (target 25-35%); 48 rows verified tier, 62 provisional; exact-quote pass rate 100% (199/199 triage, 44/44 added). Several added-finding slugs (`url-scheme-network`, `remote-code-pinning`, `scope-policy-duplicate`, `listing-metadata-docs`, `user-config-modification`) had **0** findings: OUT_OF_SCOPE under the 15-finding floor.

---

## 9. Epoch 7: r7, mining the git histories (Oct 15, evening)

The lesson of r6: the main loss was **labelling, not guards**. 1,542 Checker items in the verified tier and 1,203 more units had no mechanical label. r7 mines the git history of plugins to produce labels from what actually happened next.

**Inventory reused, not redone** (`v3/r7/STATUS.md` section 0): 5,149 plugin repos in the universe; 12,109 fix-like commits mined mechanically (50,676 hunks, 2,633 repos); **2,787 LLM-verified fix pairs** across 1,499 repos (security 214); 2,616 prepared pairs with pre/post trees on disk.

**What r7 mines (the gap).** (a) Checker output pre -> post on existing fix pairs; (b) security-pair sub-classification into weak slugs; (c) persistence labels from later versions of a plugin: a Checker warning that the plugin's own later versions keep for 3+ versions is a provisional **dismiss**; one removed by a fix commit is a verified **confirm**; versions the Checker reports clean give **positives** (clean rows).

**Pilot (300 repos, 292 processed; 7 had no permissive licence, 1 too few commits).** 2,403 versions checked; labels: 57 verified confirm, 702 provisional dismiss, 446 unlabelled; 349 candidates -> 266 units -> 91 rows (68 verified, 23 provisional); merged with r6 scope and the security subset: **110 rows** from 102 plugins (`v3/r7/GATE_REPORT_R7_PILOT.md`). Security pairs: of 207, only 77 classified by two models, yielding **6 rows** (61 dropped for unlabelled Checker items).

**Main loss found in the pilot.** 538 of 759 labelled triage items sit in files the shared renderer's 40k-character cap omits, so there is no quote to write; 74 rows dropped. That is a design problem, not a guard: the cap is the shared eval/train renderer, and changing it breaks the golden hash and train/eval parity. `code_blob/v2` (anchored windows) was added in response.

**Guards, caps, and the drop-off table.** The guards are content guards against the sealed holdout and Dell key (per-file shingle Jaccard >= 0.5, same-name, same-author, repo), cap rules (history <= 55%, dismiss cap, per-kind floors, approve mix), a v2-val repo exclusion, and Anthropic-ToS exclusion. Row drop-off from candidates to rows (measured, `v3/r7/STATUS.md` section 1):

| Build | Funnel |
|---|---|
| r5 (pool ~4.4k -> 473) | not visible under code_blob 353 findings; no finding left 420; all-failed gate 46; v2-val repos 164; near-dup 164; source cap 346; approve twins 218+51; guard content 41 / repo 29; no full source 95; unmappable category 79 |
| r6 draft (3,248 -> 647) | attribution ties/unresolvable 110; no finding left 541; failed exact-line gate 57 findings; guards 348 (same-name 83, per-file 171, content 47, author 18, repo 29); v2-val repos 183; near-dup 237; caps (history 280, logic 70, undefined-ref 41); approve twins/minority 303; kind floor 69 |
| r6 scope-v4 (3,066 units -> 90) | history twins not clean 881; prefilter 1,203; **unlabelled Checker items 1,542**; teachers disagree 114; no quotable line 81; nothing to teach 248; guards 105; v2-val 42; near-dup 7; Dell-share/approve caps 381; slug floor 44 |

Filters we flagged: code_blob visibility and the holdout/Dell guards are *not* safely loosenable; the `v2-val repos` exclusion is a candidate for Harris to loosen (it changes v2-vs-v3 comparability).

**Scale run (as of 23:01 MT, measured).** Mining processed 5,024 plugin result files of 5,033 in the universe (ledger: 5,256 ok, 25 errors, 205 no permissive licence, 489 too few commits, 2 clone failed). Miner v2 allowed clean versions to keep up to 3 unlabelled warn findings (provisional) and up to 3 clean per repo. LLM spend on the r7 builder ledger **$5.17** (hard cap in builder runs $14; Harris cap $20). Final rebuild: shards 0-8 of 40 built, 57-90 rows each, **667 rows pre-merge in total (before caps, guards and dedupe)**; final row count **TBD**.

> **Own mistakes in this stretch.** (1) The first final-build driver started shards before mining had finished (it keyed on a stale "finished" line from an earlier run), so it would have merged partial data; caught by the watcher, replaced by an armed script that waits for a *new* finished line. (2) A shard's LLM stage hung 9+ minutes on a call whose server trickled bytes so the socket timeout never fired; added a 300-second wall-clock cap. (3) A shard failed closed on malformed JSON (2/74 > 1% gate); the client now retries with a bigger budget and temperature. Nothing was deleted; partial shards were moved aside.

---

## 10. Epoch 8: train-launch infrastructure and the smoke test

Everything below is about not wasting GPU money and not losing a run.

**Run safety net.** `train/launch_vast.sh` rents an instance and arms a watchdog (`ARMED` file); `watchdog.sh` checks the process, GPU use and that the optimizer step advanced; it restarts from the newest checkpoint after a death or 15 minutes of no progress, gives up after 6 restarts, and writes an ALERT. Checkpoints sync off the instance with SHA-256. `train/launch_r7.sh` runs hard gates first (checksums, prompt sha equals `scope.prompt_scope`, `code_blob/v2` policy id, schema, guards, drop rate <= 2%, schedule, estimated hours <= `max_hours`) and `--go` only after they pass; `AUTO_DOWN` shuts the instance down after a verified fetch.

**Measured on real hardware (earlier v2 run, H100 NVL).** 68.8 s/step, peak 41.3 GB allocated, 290 steps = 5.5 h plus validation passes. kill -9 at step 4: watchdog restarted from checkpoint 4 in ~50 s; a platform reboot: container and trainer back within ~25 s and resumed from checkpoint 6, with loss matching the earlier run (0.857 vs 0.858), i.e. the same data order.

**r7 smoke test (2026-10-15 ~21:27 MT).** An H100 PCIe at about $2.89/h, **$2.92 spent of a $3 cap**. Kill/resume PASS (killed at step 4 with a checkpoint at 4, watchdog restart, resumed at step 4 then 5). **Export and parity were not run (budget).** The smoke found and fixed bugs that had passed `bash -n`: a bundle comment bug in the launcher, an scp name bug, a triton install order in `deps.sh`, an optional `prompt_v4` import on the instance, and a missing `LLAMA_CPP_COMMIT` default.

**Lessons recorded from v2 prep:** a dry-run number must be checked against how it is computed (an initial eval counted against `max_hours` produced "37 h" for a 5.5 h run); unarmed watchdogs must reset their timers; when a test says FAIL, read raw evidence before deciding which side is wrong; the shared store rejects files over ~100 MB (split into 90 MB parts plus a sha list); llama-server context is shared across slots.

**Chain scripts** (this commit): `v3/r7/chain/`, see its README.

---

## 11. Current state, 2026-10-15 23:05 MT

1. The **final shard rebuild is running** (`r7_final_armed.sh`; shard 9 of 40 in progress; 9 built). When all 40 have a `DONE` marker it merges, then writes the gate report.
2. `r7_tradeoff_after.sh` then writes the tradeoff table over all candidate rows with no caps, with floor variants (15, 8, merge-into-parent) and UNMEASURED marks for anything not run.
3. The **post-chain is armed**: after the merge and tradeoff it writes `SHA256SUMS`, runs `r7_hard_checks.py`, widens the eval interval, runs launch gates with no spend, checks Vast credit covers 1.3x the estimate (and at least $10), and then launches. **We will train regardless of row count** (the old stop-below-300 rule only warns now). It still stops on a hard failure (train < 20 rows, val empty, a repo in both train and val, duplicate ids, a failed preflight gate, insufficient credit, an unexpected earlier launch).
4. The **B0 baseline on r7 inputs** has been running; a first job ended on a transient error and the full result is **TBD**. The earlier-data B0 numbers are in section 8.
5. **Final row count, training cost, training time, and every model metric: TBD.** An r7 adapter does not exist. The planned scoring is the provisional gates in `docs/DEFINITION_OF_DONE.md`, which cannot give a "pass" until hand-labelled sets exist.
6. **Publication plan (a plan, not a result):** the r7 adapter will be compared against B0 on the same prompt, schema and post-filter. We will publish the outcome either way, labelled **"In Training: did not clear the bar"**, and ask for help. We are not predicting the r7 outcome.

---

## 12. Mistakes in one place

1. Trusted a static validator before running real code (7B "beats GPT" at 42/56 became 8/56).
2. Let the model write its own training data and called a rise on a pattern check a success.
3. Published or relied on numbers we later could not reproduce (49/61 grader agreement; best-of-16 2/32 vs 3/32).
4. Did not measure truncation and loop rates from the start: the first clean 7B fine-tune had 40 of 49 answers truncated and 41 looping, and we only counted loops as failures once we rescored.
5. Fix loop: 13 grader passes, 4 real; harvest 10/30 real on spot check.
6. Read accuracy before reading answers; v1 looked better than stock while flagging 27 of 29 clean plugins and naming the real cause for 1 of 31 broken ones.
7. v2 targets had no file:line, then v2 gave file-less answers.
8. Train-launch scripts that passed syntax checks failed on first real use.
9. Several audit-class silent failures were ours (label leak via truncation, fail-open LLM gate, no-op example weights).
10. In this last stretch: the premature final-build driver, the hung call, the malformed-JSON gate (section 9).
11. Historic names: README tables still label adapters "Usuba v1/v2" while new text says "Checker model"; it is confusing and noted in the README.

## 13. What we learned

- A checker you have verified against real hardware is worth more than any model you train on top of it. It is also what made every later mistake visible.
- A fine-tune must first beat its own stock base on the real task; "beats the frontier" is the second bar.
- Report right-reason, false alarm and category recall together. Always-flag and always-approve baselines look good on skewed sets (0.912 here).
- Train on the thing you want: if the output must cite a file and line, every training target must.
- Labels, not guards, are the bottleneck. Provisional labels (a panel or a mechanical rule) order human review; they are not truth.
- Every gate should fail closed. Every script should be run once on a cheap machine and its raw evidence read.
- Say what is measured and what is not.

## 14. Spend (partial; total TBD)

*Measured / ledger as of 2026-10-14 ~10:50 MT:* GPU billing **$77.67** (of $150 prepaid); project LLM ledgers **$129.73** on OpenRouter; stated total about **$207** (an upper bound of about $285 if all account-wide OpenRouter use is counted, because the key is shared with non-Usuba jobs). Run-level GPU costs for the 7B work were not broken out per run (unverified).
*Since then (each separately measured):* judge panel $13.84; B0 on draft data about $1.15; v2 exam peers about $2.07 (GPU on top); r7 smoke $2.92; r7 builder LLM ledger $5.17 so far. **Total to date: TBD**; the v2 training GPU cost and the r7 training cost: **TBD**.

## 15. How you can help (inviting contribution)

This is open work, and the result is not good yet. If you want to help:
- **Omarchy maintainers and plugin authors:** run the Checker scripts on your plugins and tell us false passes and false fails. A plugin that works on your machine but fails the Checker, or the reverse, is exactly what we need.
- **Reviewers:** hand labels. The final gates need >= 300 labelled Checker findings, >= 150 reviewed clean plugins, >= 100 adjudicated added findings per eval, and >= 50 hand-verified bug locations. None of those exist; the panel cannot replace them.
- **Anyone with compute or ideas:** a better way to get labelled clean positives, a renderer that does not hide 70% of labelled lines, or a bigger base.
- Repos (private today, will stay private until Harris decides otherwise): `usuba-checker-models` (this repo) and `usuba-checker-scripts`.

## 16. Source index (in this repo unless noted)
`README.md`, `docs/TRAINING_PLAN.md`, `docs/JUDGE_PANEL.md`, `docs/OPUS_AUDIT_CLOSURE.md`, `docs/ANTHROPIC_TERMS_COMPLIANCE.md`, `docs/MODEL_SCOPE.md`, `docs/DEFINITION_OF_DONE.md`, `docs/R7_HISTORY_MINING.md`, `v3/r7/STATUS.md`, `v3/r7/GATE_REPORT_R7_PILOT.md`, `v3/r6/GATE_REPORT.md`, `eval/scope/B0_RESULTS.md`, `v3/r7/chain/`. The train-launch notes (`R7_LAUNCH.md`) live on branch `r7-train-launch` (`train/R7_LAUNCH.md`). Not in the repo: the internal numeric progress ledger (2026-10-14), run notes under the build box's run directories, and the Opus audit text (`AUDIT.md`, `VERDICTS.md`). Git history of both repos (`git log`) gives every timestamp above.
