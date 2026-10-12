# Building Usuba: what the first two days of trying to teach a small model to write Omarchy plugins actually looked like

*By Harris Kenny · OutboundSync · DRAFT v0.1, written Monday, Oct 12, 2026, 4:37 PM MT · usuba.dev*

> Draft status: this is a work-in-progress log, not a launch post. The last section describes a training run that is still going. Every number below comes from files in our working repo. Anything we couldn't confirm from a source is marked [TK].

Here's the short version. We're building **Usuba**, a small, open model that runs locally and does one job: writing Omarchy shell plugins that actually work. That means Quickshell/QML plugins for the Omarchy 4 "Quattro" shell, which runs on Hyprland. We plan to release it publicly from OutboundSync at usuba.dev.

Here's the honest version. As of this afternoon, our best fine-tuned model doesn't beat the frontier models yet. It doesn't even reliably beat its own base model. Most of the past two days went into finding out *how* wrong we were about our own numbers and building tools that won't lie to us. This post walks through that work in order, one lesson at a time.

(On the name: the repo still says "Santoku" in places, and for a while we talked about "knife tiers" for different model sizes. Neither stuck. Usuba is the name.)

---

## 1. The idea: a local specialist for one very specific kind of code (Sunday, Oct 11)

Omarchy 4 ("Quattro") ships a new shell built on Quickshell, which means QML plus a little JavaScript. Almost everything you see is a plugin: the bar, the widgets in it, the menus, panels, overlays, and background services. There's a public marketplace at plugins.omarchy.org. When we pulled its catalog on Sunday night it listed 5,411 plugins.

I've written six of these myself: Rocketlauncher, Sparklekeys, Enricherino, Compliantish, Encyclopedic and Scriptural. Every one of them taught me that the hard part isn't QML in general. It's *this* QML: the specific `qs.Commons` singletons, the theme tokens, the bar API, which binaries actually exist on a stock install, and the manifest contract. General coding models know QML. They don't know Omarchy, and when they guess, the guesses look plausible and fail quietly.

[TK: the origin moment. What happened on Sunday, Oct 11 that kicked this off? The repo's first hard timestamp is the Omarchy snapshot at 2:07 PM MT, and the catalog pull is from about 9:38 PM MT; no conversation transcripts from the project were found to fill this in.]

So the bet was simple. Take a small open coding model (we started with Qwen2.5-Coder-7B-Instruct and later added the 14B), fine-tune it only on real, working Omarchy plugins, and see whether a model you can run on your own laptop can write plugins that load and work. That's Usuba.

A few constraints were there from the first hour:

- **Small and local.** It has to run on a normal developer machine. [TK: Harris, one or two sentences on why local matters to you: privacy, cost, offline use, or the Omarchy ethos.]
- **Open and publishable.** Every byte of training data has to be something we're allowed to redistribute. That forced the provenance work in the next section.
- **Measured honestly.** From day one we wanted a scoreboard that included the best frontier models, so "it's pretty good for a 7B" couldn't become the excuse.

Before training anything we wrote down the contract a plugin has to satisfy. Omarchy ships a validator (`omarchy plugin validate`, a bash + `jq` script). Its rules: `manifest.json` at the root; `schemaVersion` must be the *number* 1 (the string `"1"` is rejected); required `id`, `name`, `version`, `kinds` and `entryPoints`; ids may not use the reserved `omarchy.*` namespace; every declared kind needs a matching entry point (`bar-widget` → `barWidget`, and so on); and no symlinks. We ported it line by line to Python so we could validate in memory, then ran both versions side by side on 25 cases. They matched 25/25.

That validator turned out to be the first of several measuring sticks we'd outgrow. More on that soon.

**What we learned:** The niche matters more than the model. Omarchy plugin code is a small, fast-moving dialect with a strict contract, which is exactly where a general model's confident guessing hurts most, and where a specialist could plausibly win.

**Suggested figures:**
- Screenshot of an Omarchy Quattro desktop with a few plugins in the bar (one of Harris's, one community plugin).
- A minimal annotated `manifest.json` showing `kinds` ↔ `entryPoints`.
- [TK: optional photo of the reference laptop running Omarchy, which comes up later.]

---

## 2. The data rule, version one: 254 examples, each with a paper trail (Sunday night, Oct 11)

If we're going to give the model away, the training data has to survive scrutiny. So the first rule wasn't about quality. It was about **provenance**: every example has to trace back to a specific repo, at a specific commit, under a license that allows it.

Here's what that looked like in practice:

- **First-party Omarchy code**, pinned to `basecamp/omarchy` at commit `9480d1b` on the `quattro` branch (the merge of PR #15065, Sunday 2:07 PM MT). MIT licensed.
- **My six plugins**, all MIT. Five go into training. Scriptural is held out so we can check whether the model picks up "house style."
- **Community plugins**, but only where the actual LICENSE file *at the pinned commit* is permissive (MIT, Apache-2.0, BSD, ISC or MPL-2.0), has a copyright line, and doesn't conflict with the manifest. We classified licenses from the LICENSE text itself, not the marketplace label, and the labels were wrong a lot. Twenty-one repos labeled "See repository" had a real MIT file. One labeled GPL-2.0 was actually a noncommercial license, so we excluded it.
- **Reference only, never in training text:** GPL/AGPL/LGPL, repos with no license, and anything custom or unclear. We also excluded six forks of Omarchy itself.

We verified 117 candidate repos: 105 usable for training, 6 forks and 4 copyleft repos kept as reference only, 2 excluded. Fifty-five sources made it into the set (Omarchy, my 6, and 48 community repos), and each got a line in a `NOTICE` file plus its full LICENSE text, to ship alongside the model.

From those sources we built **254 chat-format examples**: 198 for training and 56 held out for evaluation. The holdout split works by plugin, so no plugin shows up on both sides, and it's stratified so every plugin kind appears in both. The tasks are a mix of what you'd actually ask for:

| task | train | holdout |
|---|---|---|
| build a plugin from a spec (`build_from_spec`) | 56 | 27 |
| write one component of a big plugin (`chunk_component`) | 80 | 10 |
| write a manifest + entry file (`chunk_manifest_entry`) | 28 | 5 |
| fix a broken manifest (`fix_manifest`) | 19 | 5 |
| add a panel to an existing widget (`add_panel`) | 10 | 6 |
| add a new kind to a plugin (`chunk_add_kind`) | 4 | 3 |
| write an entry file (`chunk_entry_file`) | 1 | 0 |

Every answer passed the validator, 254/254. Every one of the 290 QML files in those answers was also clean under `qmllint`'s syntax checks. (Debian doesn't ship the Qt dev tools, so we used PySide6's `qmllint` with plugins disabled. The default plugins hang on real Quickshell files.)

A couple of uncomfortable facts were already in the stats, and we didn't fully take them seriously yet. 197 of the 254 examples were "large." The biggest plugins had to be chunked, and the answers ran to tens of thousands of characters. Keep that in mind. It matters a lot later.

**What we learned:** A provenance rule is cheap to write on day one and nearly impossible to retrofit. Checking the real LICENSE file at a pinned commit, instead of trusting a label, changed the answer for dozens of repos. Version one of the rule covered *licensing*. It didn't yet say anything about who *wrote* the code, and that gap bit us within hours.

**Suggested figures:**
- Funnel: 5,411 catalog listings → 117 verified candidates → 55 sources → 254 examples (198 train / 56 holdout).
- Small table: "catalog license label vs. actual LICENSE file," with the 21 "See repository" → MIT cases and the GPL-labeled noncommercial one.
- A sample provenance record (repo, commit, license, path).

---

## 3. The overnight smoke run: endless loops, a red herring, and a "success" that wasn't (early Monday, Oct 12)

At 2:51 AM Monday we rented our first GPU on Vast.ai, an A100 at $1.07/hour, and ran a smoke test. The goal wasn't a good model. It was to prove the pipeline works end to end.

Quick vocabulary for anyone who hasn't done this:

- **SFT (supervised fine-tuning)** means showing the model a prompt and the exact answer we want, over and over, and nudging its weights so that answer becomes more likely. We use **LoRA**, which trains a small add-on set of weights instead of the whole model. It's much cheaper and you can swap it in and out.
- **Greedy decoding** means the model always picks its single most likely next token, so the output is deterministic. **Sampling** adds randomness, controlled by a temperature setting.

The first sanity check is an overfit test: train on a handful of examples and see if the model can reproduce them. It couldn't. On three *training* prompts the tuned model looped, repeating one import line 877 times and running to 67-148k characters until it hit the length limit. The stock model stopped cleanly. Our conclusion at the time: "pipeline broken, not underfit."

Then we chased a red herring for about an hour:

1. The adapter served through vLLM looped, but the same adapter run through plain Hugging Face code produced coherent text. So we blamed vLLM's LoRA serving.
2. We merged the LoRA into the base weights and served that instead. It still looped (`Io.Io.Io…`).
3. New theory: Hugging Face silently applies Qwen's default repetition penalty (1.05), and vLLM doesn't. With the penalty turned on, the merged model scored 18/56 on the validator, and 42 of 56 answers still hit the length limit.

Our 4:02 AM note got the real diagnosis right: *"loop is model behavior, not serving."* The gold answers in our data were huge files, 19k to 74k characters, while the stock model writes about 3k and stops. We were teaching a 7B to write enormous files, and it drifted into repetition trying to do it.

What we did next is the part I'm least proud of, and the most useful to share. To get shorter, cleaner targets, we used **rejection sampling** (often called RFT): let the *stock* model attempt the training prompts, keep only the answers that pass the validator, and fine-tune on those. That gave us 156 model-written samples plus 13 short gold answers. We trained, and at 4:26 AM the log says, in capital letters, **SUCCESS**: 42/56 on the validator, 19/33 on full plugins, only 2 truncated, zero QML syntax errors.

We repeated the recipe on the 14B before 6:30 AM. Stock 14B scored 24/56, the tuned 14B scored 42/56, and none of its answers were truncated. That GPU session cost about $0.79.

Two problems, which we saw within hours:

- **The validator only checks the manifest.** It confirms the JSON is shaped right and the entry files exist. It never runs the plugin.
- **We had trained on model-written answers.** That's not technically against the license rule, but it's against the spirit of "learn from real, working Omarchy code." Section 6 explains how we fixed it.

**What we learned:** When your fine-tune loops, check the training targets before you blame the inference server. And a score that jumps from 13 to 42 overnight deserves suspicion, not a celebration in all caps.

**Suggested figures:**
- Excerpt of a looping output (the 877× repeated import line, or `Io.Io.Io`), shown with a scrollbar so the length lands.
- Timeline strip, 2:51-6:26 AM: overfit loop → vLLM theory → merge theory → rep-penalty theory → "model behavior" → RFT "SUCCESS."
- Bar chart of validator scores (stock 31, tuned 13, tuned_rp1.1 18, tuned_rft 42, stock14b 24, tuned14b 42, all /56). Label it clearly as **the grader we later threw out**.

---

## 4. The frontier panel: who are we actually competing with? (Monday morning, Oct 12)

A specialist model only matters if it beats what people already use. So we ran the same 56 holdout prompts through a panel of frontier and open models via OpenRouter: Claude Opus 5.5, Claude Sonnet 5.5, GPT-5.6, Gemini 3.1 Pro (preview), DeepSeek V4 Pro, Kimi K3, Qwen3-Coder and Qwen2.5-Coder-32B. We also ran Grok 4.3 and Grok Build 0.1 directly against xAI's API.

One non-negotiable: **zero data retention (ZDR) stays on.** Our prompts include other people's open-source code and the eval set itself. We didn't want either one retained or trained on by a provider. That setting has real costs:

- Qwen2.5-Coder-32B errored on all 56 prompts. Its only available endpoint didn't meet the account's ZDR requirement, and we left the setting alone instead of loosening it.
- Later, when we asked other models to review our plan (section 7), GLM 5.3 Prime was blocked for the same reason, so we used regular GLM 5.3. Meta's newest model was blocked behind an age-attestation setting, and we didn't change that either.

The run itself was a little chaotic. The OpenRouter account ran out of credit partway through ($38.49 of $40 spent account-wide), so Opus, GPT, Sonnet and Kimi returned payment errors on 40-54 rows each. We added credit and reran just the failed rows. We held Opus until we'd checked spend, since it's the expensive one. A few models also hit the length limit on the biggest plugins, so we reran those rows with a bigger output budget (the `_big` runs).

From our per-call cost logs, the whole panel (first pass, reruns and big-budget reruns) came to roughly $33.50. Kimi K3 was the most expensive at about $10.68, and Qwen3-Coder the cheapest at about $0.08. [TK: confirm against the OpenRouter dashboard; the logged per-call costs may not match the invoice exactly.]

On the validator, the panel looked like this (/56):

| model | validator pass |
|---|---|
| GPT-5.6 | 40 |
| Gemini 3.1 Pro | 37 |
| Grok Build 0.1 | 36 |
| Sonnet 5.5 | 35 |
| Opus 5.5 | 34 |
| Grok 4.3 | 32 |
| stock Qwen2.5-Coder-7B | 31 |
| Qwen3-Coder | 29 |
| DeepSeek V4 Pro | 28 |
| Kimi K3 | 9 (46 truncated) |
| Qwen2.5-Coder-32B | 0 (blocked by ZDR) |

Look at that table for a second. On this grader, our tuned 7B (42) "beat" GPT-5.6 (40), and the *untuned* stock 7B (31) landed within a few points of Opus. If that sounds too good to be true, it's because it was.

**What we learned:** Benchmark against the best models from the start, and keep privacy settings on even when they cost you a data point. The other lesson, which we only saw clearly an hour later: when a 7B ties the frontier, check the ruler before you announce anything.

**Suggested figures:**
- The panel table above, labeled "validator-only scores (superseded)."
- A small cost bar chart per model from the logs, with the [TK] caveat.
- Callout box: "Why ZDR stays on: the two models we couldn't test, and why that was the right call."

---

## 5. The first box test with real Quickshell: the validator was lying (Monday morning, Oct 12)

Right after the panel, we started building a real functional test, the "functest." The idea: don't just check the manifest. Install the plugin into a *real* Omarchy shell running under Quickshell on our Linux box, with a headless compositor, and see what happens. Does it load? Does the widget actually show up on screen with nonzero size and visible pixels? Does the panel open? Does the log show real errors (TypeError, ReferenceError, missing files, missing types)? On top of that, static checks catch things like made-up APIs, Qt5-era properties, placeholder UIs and dangerous file writes.

By about 8:15 AM we'd rescored everything with it. Here are the 56 holdout prompts again, validator score next to functest score:

| model | validator /56 | functest /56 |
|---|---|---|
| reference answers (the real plugins) | n/a | 51 |
| GPT-5.6 | 40 | 29 |
| Opus 5.5 (big budget) | 34 | 28 |
| Sonnet 5.5 | 35 | 22 |
| Grok Build 0.1 | 36 | 17 |
| tuned 14B (RFT) | 42 | 12 |
| Gemini 3.1 Pro | 37 | 11 |
| Grok 4.3 | 32 | 11 |
| DeepSeek V4 Pro (big budget) | 28 | 9 |
| Qwen3-Coder | 29 | 9 |
| stock 7B | 31 | 8 |
| stock 14B | 24 | 8 |
| **tuned 7B (RFT, the "SUCCESS")** | **42** | **8** |
| Kimi K3 | 9 | 8 |

The 4:26 AM "SUCCESS" went from 42 to 8, no better than the stock model. On full plugins it scored 0/33. The tuned 14B fell from 42 to 12. Meanwhile GPT-5.6 and Opus held up, and the real plugins passed 51 of 56.

Around the same time, we packaged the nine plugins the RFT model wrote for the `build_from_spec` holdout (the ones that passed the validator) for a hand test on my Omarchy laptop. Just reading them before installing anything was enough:

- **Four of the nine were JavaScript, not QML.** They imported a made-up `omarchy` JS module, Node's `child_process`, and the browser's `document`. Quickshell can't load any of that.
- One called `hyprctl getbinds`, which isn't a real subcommand. The real one is `binds`.
- One tried to use C++'s `QNetworkAccessManager` from QML.
- And one, `bobbynicholas.omaland`, would have **overwritten my Hyprland look-and-feel config** with a one-line `print` statement via unquoted shell interpolation, if its JS had ever loaded. The test instructions flagged it in bold: skip it, or back up `~/.config/hypr` first.

Every one of those plugins passed the official validator.

[TK: did Harris actually install any of the 9 dell-smoke plugins, and what happened? The checklist in `dell-smoke/README.md` is blank in the repo.]

**What we learned:** "Valid" and "works" are different properties, and a cheap grader that measures the first will happily reward a model for gaming it. The validator is fine as a gate, but it's useless as a score. Also: read model-written code before it touches a real machine. A config-wiping plugin got through a "passing" check.

**Suggested figures:**
- Slope chart: validator score → functest score for each model. The tuned 7B's drop from 42 to 8 is the headline.
- Screenshot or code excerpt of the `omaland` service writing over `looknfeel.lua`, redacted and annotated.
- Diagram of the functest harness: plugin → real Omarchy shell under Quickshell → headless compositor → screenshot + log + probes → verdict.

---

## 6. The data rule, version two: merged and reviewed code only (Monday morning, Oct 12)

After the box test, we rewrote the data rule. Here it is as committed at 9:44 AM:

> Train only on code that was merged or reviewed upstream: basecamp/omarchy main, or verified listings in the official registry at plugins.omarchy.org. No synthetic or model-generated rows, no unmerged forks, no unknown provenance, and no frontier (GPT/Claude) outputs.

That means:

- **The 169-row RFT set from section 3 is out.** It was model-written.
- **We never built a "distill from GPT/Opus" set.** It would have been the obvious shortcut: GPT-5.6 had the best functest score, so why not train on its answers? But then Usuba would be a compressed copy of someone else's model, trained on outputs nobody reviewed, and any public release would raise questions we can't answer. The repo notes say the frontier-candidates file "was intentionally NOT produced."
- **The synthetic `fix_manifest` rows are out.** The answers were real, but the prompts were corruptions we generated ourselves.
- **Every gold answer had to pass the functest itself.** We ran all 198 training answers through it. 180 passed, after we fixed a harness issue: six answers failed only because binary assets like SVGs and PNGs can't live in a text answer. The other 18 failures were real behavior (sudo/pkexec, writes to `/etc/pam.d` in first-party lock screens, writes to `~/.config/hypr`), and they stayed out.

To make up for the rows we dropped, we went to the registry. From a live catalog snapshot (5,416 listings, 3,873 verified), we curated 418 plugins. To qualify, a plugin had to be verified, recently updated, starred, permissively licensed with a real LICENSE file, passing the functest, not a placeholder, and not too similar to anything in the holdout. Each GitHub owner got at most three. That produced 152 new full-plugin examples, plus 328 chunked examples from 107 plugins that were too big to use whole.

We also **deduplicated the holdout against training**. Seven of the 56 holdout answers overlapped a training answer too closely (line-level Jaccard ≥ 0.7), so we removed them. **From here on, the eval set is 49 prompts.**

The cleaned training set came to **593 rows**, each with its own provenance record: repo, commit, license, functest result, and the reason for any exclusion.

One honest caveat we wrote down at the time: "verified" in the registry means the directory's automated snapshot verification, not necessarily human code review. I decided to treat the registry's "verified" label as "reviewed" for our purposes. That's a judgment call, and readers should know we made it. And since third-party code is now in the training text, the NOTICE file has to cover every registry repo before release. The current working copy has that update in progress (about 330 new lines).

**What we learned:** "Don't train on model output" sounds obvious until a model-written dataset produces your best score. Writing the rule down, with reasons, is what kept us from quietly keeping the shortcut. Deduplicating the eval set also matters: 7 of 56 holdout answers were near-copies of training data.

**Suggested figures:**
- Before/after table: v1 (254 examples, license rule) vs. v2 (593 train rows / 49 holdout, merged-and-reviewed rule), showing what was dropped and why.
- Registry funnel: 5,416 listings → 3,873 verified → 418 curated → 152 full + 328 chunked rows.
- One redacted provenance record from `train_final_manifest.json`.

---

## 7. The first clean fine-tune: 10 out of 49, and it never stops talking (Monday late morning, Oct 12)

With clean data, we trained again. The 7B (`clean_b`) got LoRA rank 16, learning rate 1e-4, two epochs, on 454 rows of the cleaned set. [TK: confirm how the 454-row `train_b` was derived from the 593-row `train_final`; the run log shows 454 of 454 rows used.] We also did a 14B "warm-up" (`clean_w14`) on 252 rows for three epochs, meant as the starting point for reinforcement learning later.

On the functest as it stood that morning (we'll call it the *old grader*, because we rebuilt it that afternoon), here's where things landed on the 49 deduped prompts:

| model | overall /49 | full plugins /32 | truncated | looping | median output |
|---|---|---|---|---|---|
| GPT-5.6 | 24 | 15 | 0 | 0 | 20.5k chars |
| Opus 5.5 | 23 | 14 | 4 | 0 | 14.3k chars |
| **7B clean fine-tune** | **10** | **1** | **40** | **41** | **60.8k chars** |
| 14B warm-up | 7 | 0 | 36 | 31 | 59.9k chars |
| stock 14B | 6 | 1 | 1 | 1 | 1.9k chars |
| stock 7B | 3 | 0 | 0 | 0 | 1.7k chars |

Some explanation of those columns:

- **Truncated** means the model was still writing when it hit the maximum output length, so the answer just ends, often in the middle of a file. A truncated plugin almost never works.
- **Looping** means the model got stuck repeating itself, either the same line over and over or the same pattern with a counter ticking up.

The fine-tune *did* learn things. It moved from 3 to 10, and from writing almost nothing to writing plugin-shaped answers. But 40 of 49 answers ran to the length limit, and 41 looped. The median answer was 60.8k characters, about 15k tokens, which is roughly **twice as long as the real answers it was trained to imitate**. So the model wasn't hitting a cap that was too tight. It had learned to keep going.

We asked two outside models to review the plan: DeepSeek V4 Pro and GLM 5.3, through OpenRouter with ZDR on, for $0.12 total. Then we checked every claim they made against the code and data, and several were wrong. GLM said the Qwen end-of-sequence token was `<|endoftext|>`, but it's `<|im_end|>`. It estimated a median prompt of 5-7k tokens, and the real median is 392. DeepSeek called the 16k output cap "the main reason," but only 4 of the 49 reference answers are over 16k tokens.

What held up, and what we adopted:

1. **Long training targets teach over-elaboration.** 108 training answers were over 12k tokens and 57 were over 16k. Cut or chunk them.
2. **Run a cheap decoding sweep before training anything else.** (Section 10.)
3. **Our loop detector had a hole.** It only counted exact duplicate lines. (Section 11.)
4. **Before spending real money on reinforcement learning, check whether the model can produce a working answer at all.** (Section 12.)
5. **The grader could be gamed.** Some of its leniency rules could be exploited by a model under RL pressure. That pushed us toward the hardware ground truth in the next section.

**What we learned:** Fine-tuning on long, complete files teaches a small model to write long files, not complete ones. The thing that's actually missing is knowing when to stop. Also: outside reviewers are useful for ideas but unreliable on facts. Treat their claims as hypotheses and check each one against the data.

**Suggested figures:**
- Grouped bar chart from the table: overall vs. full-plugin, with truncated/looping counts as a stacked overlay.
- Histogram of answer lengths: training targets vs. holdout references vs. 7B fine-tune outputs (medians about 5.8k tokens, 7.4k tokens and ~15k tokens).
- Side panel: "What the AI reviewers got wrong," with three bullets, each with its measured correction.

---

## 8. The Dell becomes ground truth: 76 labeled plugins, a rebuilt grader, and a blind test (Monday midday to afternoon, Oct 12)

By midday the problem was clear. Every decision we make, about what data to keep, which model is better, and eventually what reward to use for RL, depends on the grader. And we had no proof the grader matched reality. The box runs a *simulation* of Omarchy. The only real reference is a laptop actually running it.

So the grader got a ground truth: my reference laptop running Omarchy 4.0.0.alpha on a 1920×1080 panel.

**Batch 2: can the grader be fooled?** We picked 15 plugins that *all passed* our functest: 10 real registry plugins and 5 model-written ones. I read every one before installing anything (no sudo, no network, no file writes; one adjusts live window gaps). Then we tested them on the Dell. The real plugins worked, or at least weren't clearly broken: 7 WORKS and 3 needing interaction to judge. But three of the five model-written ones were broken on real hardware even though all of them had passed.

The best example is a plugin called `flush-bar`. Opus wrote a version and GPT-5.6 wrote another (in batch 3). The job is simple: set the top window gap to zero so windows sit flush under the bar. Both versions read the current gap with `hyprctl getoption general:gaps_out` and expected a line starting with `custom type:` or `int:`. Real Hyprland prints `css gap data: 16 16 16 16`. So both plugins quietly parsed nothing and exited. No error, no effect, and a pass from a grader whose fake `hyprctl` printed the wrong format.

**Capturing the real environment.** Next we pulled reference data off the Dell: the real `hyprctl` replies, the installed binary list, the environment, and a full copy of the Omarchy shell tree. From then on the box harness could replay *real* captures instead of guessing.

**Batch 3: 61 plugins, hands off.** We wrote a script that runs on the laptop, one plugin at a time (about 30 minutes in total). For each plugin it installs, validates, enables, and adds the plugin to the bar. Then it restarts the shell, screenshots the screen before and after toggling, records the gap setting and the logs, and finally puts everything back and removes the plugin. A trap restores the config if anything dies mid-run. The 61 plugins were 36 verified registry plugins plus 25 model-written ones: our 7B, our 14B, GPT-5.6 and Opus 5.5. Then we labeled each one by eye from the screenshots and logs as WORKS, BROKEN or UNSURE. UNSURE covers plugins that need a touchscreen, a hover, a missing optional app, or user config before they do anything visible.

Across the 76 labeled plugins (batches 2 and 3), the old box grader's record against hardware looked like this:

| old box grader vs. Dell | WORKS | BROKEN | UNSURE |
|---|---|---|---|
| box PASS | 27 | 3 | 15 |
| box FAIL | 11 | 17 | 3 |

Of the 58 plugins with a clear real-world verdict, the old grader agreed on 44. On batch 3 alone it agreed on 34 of the 46 clear verdicts. [TK: Harris's notes say "49 of 61" for the old box test vs. hardware. We couldn't reproduce that figure from `dell-batch3/labels_final.tsv` (34/46 decided, or 44/61 if likely-works UNSUREs count as works). Confirm which number and definition to publish.] It failed in both directions:

- **3 false passes.** Two registry plugins call binaries that aren't on a stock install (`cava`, `voxtype-audio-bridge`), and the third was GPT-5.6's `flush-bar`.
- **11 false fails.** Mostly harmless warnings counted as errors, workspace widgets measuring zero width because the fake Hyprland had no workspaces, and fake Hyprland JSON in the wrong shape.

**The rebuild.** In the early afternoon we rebuilt the grader around the Dell:

- It runs the real Omarchy shell (commit `c668141`, byte-identical to the Dell's) under Quickshell in a sandbox, with the real theme and fonts.
- A fake Hyprland IPC and `hyprctl` replay real Hyprland 0.56.2 reply shapes from the captures, including that `css gap data:` line.
- Every binary on the Dell gets a logging shim. Any binary that isn't there fails to start, just like on the Dell.
- New checks: any launched binary must exist on stock Omarchy; no `undefined`/`NaN`/`[object Object]` in commands or rendered text; widgets must be visible, on screen, with real ink and contrast; and a service that claims to change gaps has to actually issue the gap command.
- Warnings that appear on the Dell in plugins that *work* are downgraded to soft. Real load errors still fail.
- Anti-tamper: logs, probes and screenshots leave the sandbox on a pipe, never as files a plugin could rewrite.

Against the 58 clearly labeled plugins, the rebuilt grader scored **58/58**.

**The blind test.** Of course it scored 58/58. We tuned it on those 58. The real question is whether it holds up on plugins it has never seen. So we built a repeatable "Dell loop" and ran a blind round: 40 new plugins (28 community registry plugins and 12 fresh generations from our models). **Before running anything on the laptop, we sealed the grader's verdicts and committed them, with a SHA-256 hash, to git.** That's 23 PASS and 17 FAIL, locked in.

Results: 32 of the 40 got a clear verdict on hardware. The grader agreed on **30 of 32 (93.8%)**. And the number we care most about: **zero false passes**. Both misses went the safe direction (grader too strict). One was our binary inventory missing `deno`, which the Dell has. We fixed the data, and the original 58 still scored 58/58. The other was an undefined color global that broke a few color bindings while the plugin still rendered. After the `deno` fix, the grader agrees with hardware on 89 of 90 clearly labeled plugins.

**What we learned:** A grader you haven't checked against reality is just a guess. Two habits made ours trustworthy: (1) label real hardware runs by eye and treat that as the answer key, and (2) seal the grader's predictions *before* the blind run, so we can't fool ourselves afterward. When RL is coming, false passes matter far more than false fails, because a model under optimization pressure will find every false pass.

**Suggested figures:**
- Photo or screenshot grid: Dell bar strips before/after toggling for a few plugins (the `bar_strips/` crops), each labeled WORKS / BROKEN.
- The two confusion matrices side by side: old grader (44/58) vs. rebuilt grader (58/58, then blind 30/32 with 0 false passes).
- The `flush-bar` bug as a two-line diff: what the plugin expected vs. what real Hyprland prints.
- Diagram of the Dell loop: build round → seal verdicts (sha256, commit) → pack → laptop run → collect → label → score.

---

## 9. Honest rescoring: everything got worse, and that's the point (Monday afternoon, Oct 12)

Once the rebuilt grader passed its blind test, we reran every saved output through it on the 49 deduped prompts. Nothing was regenerated, so this was just a fairer ruler. The table to keep in mind for the rest of the post:

| model | overall /49 | full plugins /32 | build-from-spec /26 | truncated | looping |
|---|---|---|---|---|---|
| GPT-5.6 | **22** | 16 | 10 | 0 | 0 |
| Opus 5.5 | **21** | 14 | 9 | 0 | 0 |
| our 7B clean fine-tune | **6** | 0 | 0 | 40 | 41 |
| stock Qwen2.5-Coder-14B | **5** | 1 | 0 | 1 | 1 |
| our 14B warm-up | **4** | 0 | 0 | 36 | 35 |
| stock Qwen2.5-Coder-7B | **3** | 1 | 1 | 4 | 4 |

[TK: Harris's notes call the 6/49 model the "capped 7B." Confirm the label. In the results file it's `clean_b`, the 7B clean fine-tune, decoded greedily with up to 28k output tokens.]

The 7B fine-tune dropped from 10 to 6. Four of those six passes come from the easy `fix_manifest` task (4 of 5). On real plugins built from a spec, it scored **0 of 26**. The 14B warm-up went from 7 to 4, actually *below* the stock 14B it started from. The frontier models moved down by about two points each.

Two more notes:

- The grader is still being tightened. At 4:35 PM we closed one more loophole: for reserved-id manifest fixes, the grader used to accept a bare id like `time-machine`, but the contract requires a namespaced, non-reserved id. A rescore right after puts GPT-5.6 at 21 and Opus at 20. [TK: final rescored numbers for all models under the 4:35 PM grader change. The fix_manifest rule may also shift our 7B's score.]
- How high can anyone score? An earlier rescore of the *reference answers*, the real human-written plugins, put them at 25/49 under a stricter version of the grader, down from 44/49 on the old one. [TK: rerun the references under the final grader and publish that ceiling. If the references land around 25, then GPT-5.6's 22 is near the top, and our denominators need explaining.]

**What we learned:** A good grader makes your numbers worse, and you should want that. If you only remember one number from this post, make it this one: on building plugins from a spec, our fine-tunes are at 0 of 26, GPT-5.6 is at 10, and Opus is at 9. That's the gap Usuba has to close.

**Suggested figures:**
- The table above as a horizontal bar chart, frontier models in one color and local models in another.
- Small multiples of three scoreboards (validator → old functest → Dell-calibrated functest) for the same models, to show how much the ruler mattered.

---

## 10. The decoding sweep: looping is learned, not a settings problem (Monday afternoon, Oct 12)

The outside reviewers' best suggestion was also the cheapest. Before training anything new, re-decode the existing 7B fine-tune with different settings. Maybe the output cap was too short. Maybe the repetition penalty was wrong. Maybe a little randomness would shake it out of its loops.

A quick explainer: **decoding** is how you turn the model's next-token probabilities into text. **Temperature** controls randomness: 0 is greedy, higher values sample more freely. **Repetition penalty** makes recently used tokens less likely. A value of 1.0 means no penalty, and Qwen's default is 1.05.

We ran a grid of temperature {0, 0.6} × repetition penalty {1.0, 1.05, 1.1}, with a much larger output budget (up to 28k tokens), on all 49 prompts. Scored with the rebuilt grader:

| setting | overall /49 | full /32 | truncated | looping | median output |
|---|---|---|---|---|---|
| temp 0, rp 1.0 | 6 | 0 | 37 | 43 | 109k chars |
| temp 0, rp 1.05 | 6 | 0 | 36 | 44 | 100k chars |
| temp 0, rp 1.1 | 6 | 0 | 39 | 44 | 113k chars |
| temp 0.6, rp 1.0 | 7 | 1 | 32 | 35 | 117k chars |
| temp 0.6, rp 1.05 | 6 | 0 | 30 | 34 | 107k chars |
| temp 0.6, rp 1.1 | 6 | 0 | 34 | 34 | 104k chars |

Every setting lands at 6 or 7. A bigger budget didn't help the model finish. It just gave it room to write *more*: median outputs grew from about 61k characters to 100-117k. Truncation stayed at 30-39 out of 49. The 14B warm-up retrained with checkpoints (one epoch, 24k-token budget) told the same story: 7/49, 45 truncated, 44 looping.

On the practical side: at 28k-token outputs, vLLM's repetition-penalty path became CPU-bound, with the GPU sitting around 20% utilized. That's worth knowing if you run similar sweeps.

**What we learned:** No decoding setting fixes a model that has learned to ramble. The loops come from training, specifically from imitating very long targets, so the fix has to come from training too: shorter, complete targets, and eventually a reward that pays for finishing. This sweep cost us a few dollars and saved us from tuning knobs that don't matter. [TK: actual Vast cost of the sweep; the reviewers estimated $5-10.]

**Suggested figures:**
- A 2×3 heatmap of score, with truncation and loop rates as annotations. It's boring on purpose: it looks the same everywhere.
- Box plot of output length per setting next to the reference answer length (median about 7.4k tokens).

---

## 11. A compression-based loop detector (Monday afternoon, Oct 12)

All those "looping" counts depend on being able to detect a loop. Our first detector was naive. It flagged an answer only if a single exact line repeated more than 30 times and made up a big share of the output. One of the reviewers found a sample that grew like `…AndUnitAndUnitAndUnit…` on one line, and our detector scored it as `loop=False`. A worse case: counter loops like `prop785`, `prop786`, `prop787`, where every line is technically different.

The new detector (`loopdet.py`, shared by the scorer and the RL tooling) stacks four checks:

1. **Compression.** Take the last 20,000 characters of the answer and compress them with zlib. Normal code doesn't compress below a certain point. A loop, even one with a counter ticking up, compresses extremely well. The threshold is a compressed-to-original ratio under 0.06. We calibrated it on real outputs: our fine-tunes' loops compress to 0.002-0.015, while the lowest ratio we saw from any frontier model (GPT-5.6, Opus, Gemini, Kimi) was 0.118. There's a wide gap, and the line sits well inside it.
2. **Repeated lines.** The original check, kept as a backstop.
3. **Tandem repeats.** Any substring (up to 80 characters, containing a letter or digit) repeated back to back at least 8 times, covering at least 120 characters. That catches `AndUnitAndUnit`.
4. **Token n-grams.** Any 30-token sequence repeated at least 20 times and covering at least a quarter of the answer.

This matters beyond bookkeeping. If we use RL, the loop detector becomes part of the reward: a penalty the model will try to dodge. A detector with holes would teach the model to loop in ways the detector can't see.

**What we learned:** Compression is a surprisingly good, nearly free signal of degenerate text, because repetition is exactly what compressors exploit. Calibrate the threshold on real good and bad outputs, not on intuition. And any metric that will turn into a reward needs to be hardened *before* the optimizer sees it.

**Suggested figures:**
- Strip plot of compression ratios: fine-tune loops (0.002-0.015) vs. frontier outputs (≥0.118), with the 0.06 threshold drawn in.
- Three tiny excerpts, one per loop type: repeated line, `AndUnitAndUnit`, and `prop785/prop786`, each labeled with the check that catches it.

---

## 12. Best-of-16: why reinforcement learning can't learn from this model yet (Monday afternoon, Oct 12)

The obvious next step after SFT is **reinforcement learning (RL)**. Instead of showing the model the right answer, you let it try, score each attempt, and push it toward whatever scored well. Our grader can now say "this plugin works" with no false passes in the blind test, so it looks like a natural reward.

The specific method we planned is **GRPO (Group Relative Policy Optimization)**. For each prompt, the model generates a *group* of attempts (we planned 8). Each attempt is scored, and the model is nudged toward the attempts that beat the group's average and away from the ones below it. The key detail: **GRPO learns from differences within a group.** If all 8 attempts score zero, nothing beats the average, and that prompt teaches the model nothing.

So before spending money on GRPO, we ran the gate the reviewers suggested: **best-of-16**. Take 32 build-from-spec prompts from verified registry plugins (not the eval set), sample 16 answers per prompt at temperature 0.8, and score all 512 with the rebuilt grader.

Two terms:

- **pass@1** is the chance that a single random sample works, averaged over prompts.
- **pass@k** (here k = 16) is the share of prompts where *at least one* of the k samples works. It's a rough ceiling on what RL could find to reinforce.

Results for the 7B fine-tune [TK: confirm which checkpoint generated `gen_bo16_t0.8_rp1.05_n16.jsonl`; the results file labels it `bo16_7b`]:

| metric | value |
|---|---|
| pass@1 | **0.006** (3 passing samples out of 512) |
| pass@16 | **3 of 32 prompts** by the grader |
| truncation rate | 60.9% of samples |
| loop rate | 44.3% of samples |

[TK: Harris's notes say "2/32 prompts with a real working sample." The results file shows 3/32 grader passes, one sample each on 3 prompts. If one of the three failed a hand check, say so here and name it; that's a great detail for this section.]

That's the problem in one number. With groups of 8 and a pass rate around 0.6%, nearly every group would be all zeros. The plan already called for dropping prompts where all samples score the same, since they carry no signal. Applied here, that would throw out almost the whole training set. The reviewers flagged a second-order risk too: whatever survives would mostly be the easy tail, like manifest fixes the model already gets right, so RL would polish the part that already works.

Our written RL plan (TRL's GRPO trainer with vLLM, LoRA on the 14B, the functest as reward, penalties for truncation, loops and excess length, sandboxed scoring, a $150-250 budget with a hard stop at $300, and kill criteria if nothing improves by step 100) is still on the shelf. It stays there until the SFT model produces working answers often enough to learn from.

**What we learned:** RL amplifies what a model can already do sometimes. It can't create a skill from nothing. Measuring pass@k first turned "let's try GRPO" into a clear prerequisite: get the supervised model to a pass rate where groups actually have winners and losers. That cost us one cheap sampling run instead of a $150-300 RL run that would have learned nothing.

**Suggested figures:**
- A 32×16 grid of dots, one per sample, colored pass / fail / truncated / looped. Three green dots in a sea of red and gray tells the story.
- A simple GRPO diagram: one prompt → 8 attempts → scores → "above average gets reinforced," next to an all-zero group with "no signal."

---

## 13. The manifest `entryPoints` lesson (Monday afternoon, Oct 12)

When we went through the blind round's broken plugins by hand, one pattern stood out. **All nine** generations from the stock 14B wrote their manifest like this:

```json
"kinds": [{ "kind": "overlay", "entryPoint": "Overlay.qml" }]
```

The contract wants this:

```json
"kinds": ["overlay"],
"entryPoints": { "overlay": "Overlay.qml" }
```

It's a small difference, but the validator rejects the first form (`missing required field 'entryPoints'`), and then nothing loads. No amount of good QML underneath matters.

Once we went looking, the same family of mistakes showed up everywhere. Earlier that morning, while building rejection-sampling data for the 14B, we'd noted that "14B stock often omits entryPoints." In Dell batch 3, four frontier-model plugins (two from GPT-5.6, two from Opus 5.5) declared the `bar-widget` kind with no `barWidget` entry point and showed nothing at all. On the old grader, `rt-manifest-rejected` was the single most common failure for the stock 14B: 29 of 49 answers.

So for the retrain, the dataset builder enforces it. Every manifest in a prompt or answer must have a top-level, non-empty `entryPoints` object, and any nested form gets lifted to the top level. Then something interesting happened: **the fixer found zero rows to fix.** Our training data was already correct. The nested shape isn't something the model picks up from our data. It's a prior the base model brings from somewhere else, and the fine-tune has to *overwrite* it, not just avoid teaching it.

We also wrote down the other failure patterns from the blind round as things to train against:

- Degenerate, unterminated QML: files running to 1,200-1,500 lines that end mid-token, sometimes even when the model reported a clean stop.
- Referencing a type the plugin doesn't ship.
- Undefined theme globals (`ShellColor`) instead of the documented `Color.*` / `qs.Commons` API.

And patterns worth keeping, from real plugins that handled things well: graceful "missing dependency" panels, widgets that stay hidden until configured, and expensive first-run work deferred until the panel opens.

**What we learned:** The cheapest wins are in the contract, not the code. One manifest shape accounts for a large share of the gap between stock models and working plugins. And "our data is clean" doesn't mean "our model will be clean." Base-model priors have to be actively trained out, and the grader has to keep checking for them.

**Suggested figures:**
- The two JSON snippets side by side, wrong vs. right, with the validator's error message underneath.
- Bar chart: share of manifest-shape failures by source (stock 14B 9/9 in blind1; 29/49 `rt-manifest-rejected` for stock 14B on the old grader; 4 frontier plugins in batch 3).

---

## 14. Where we are right now: the SFT retrain is running (Monday, Oct 12, 4:37 PM MT)

As I write this, a third supervised retrain of the 7B, `v3`, is running on a rented GPU. [TK: confirm the instance is up and the run is progressing; the pipeline script was staged at 4:25 PM.] Everything above shaped it.

**Shorter targets.** Every training answer is capped at 8,192 tokens, down from 12,000 for the second 14B warm-up and from a 32,768-token limit (which dropped nothing) for the first clean 7B run. That came straight from section 7: long targets taught over-elaboration. We start from the 813-row merged-and-reviewed set and drop 206 rows (203 for length, 3 more as near-duplicates of a holdout answer). That leaves **607 rows**. The median answer is now 4,595 tokens, and the longest is 8,143. Every row is MIT (592), Apache-2.0 (12) or ISC (3), and each one carries its provenance record. The mix: 228 build-from-spec, 209 component chunks, 67 add-panel, 49 add-kind, 46 manifest + entry, 8 entry-file.

[TK: the builder references a `v3/README.md` justifying the 8,192 cap, and that file doesn't exist in the repo. Write a one-paragraph justification, or link the reviewer finding in section 7.]

**The manifest fix.** As described in section 13, every manifest must have a top-level `entryPoints`. The guard is in place, and it found nothing to fix in our data.

**Omarchy's built-in plugins.** We wanted to add Omarchy's own built-in plugins from a newer snapshot (`omacom/omarchy` at `defbf90`), re-namespaced from `omarchy.*` to `acme.*` so the model never learns to use the reserved namespace. Here's what happened when they went through the same gates as everything else: 38 candidates, and **zero made it in.** Eight were already in training from the earlier snapshot. Eight belong to holdout plugins, so including them would leak the eval. The other 22 failed our functest in the sandbox, mostly on imports and singletons that first-party code is allowed to use and third-party plugins aren't. So this retrain doesn't include new built-ins. [TK: decide whether to relax the gate for first-party code (e.g., a first-party functest profile) or leave it out and say so.]

**The recipe** is deliberately unchanged from the first clean 7B run (LoRA rank 16, learning rate 1e-4, 2 epochs), so the data is the only thing that changed. When training finishes, the pipeline automatically:

1. merges the adapter,
2. generates greedy answers for the 49 eval prompts (repetition penalty 1.05, up to 28k tokens), and
3. reruns best-of-16 on the same 32 build-from-spec prompts from section 12.

**What would count as progress:**

- Truncation and looping drop sharply, well below the previous 40/49 and 41/49.
- At least some build-from-spec passes. The last two fine-tunes scored 0/26.
- pass@16 high enough that GRPO groups would actually contain winners.

[TK: v3 results. Overall /49, full /32, build-from-spec /26, truncated, looping, median length, pass@1, pass@16.]

**What comes after, in order:**

1. **RL (GRPO), only if best-of-16 shows signal.** We'll use the hardened reward, filter prompts whose gold answer exceeds the completion cap, and enforce a hard budget stop.
2. **A held-out test** on plugins neither the model nor the grader has seen, run through the same Dell loop with verdicts sealed in advance. We know 49 prompts is a noisy eval (the reviewers estimated a ±13-point confidence interval), and we'd like a bigger one. The constraint is how many unused, verified, permissively licensed plugins exist.
3. **A real person building a real plugin with Usuba**, on their own machine, end to end. That's the only test that matters for the launch. [TK: who, and which plugin?]

**What we learned (so far):** We're further from done than the overnight log suggested, and much closer to *knowing* where we stand. Every piece of infrastructure we built in the last two days (provenance records, the Dell-calibrated grader, sealed blind rounds, the loop detector, pass@k gating) will outlast this particular retrain, whether it works or not.

**Suggested figures:**
- Answer-length histogram: v3 training targets (capped at 8,192 tokens) vs. the earlier clean set (long tail to 25.6k).
- A "what we're watching" scorecard with the prior baseline filled in and the v3 column left as [TK].
- Roadmap strip: SFT v3 → (gate: pass@16) → GRPO → blind held-out test on the Dell → real user build → usuba.dev.

---

## 15. Cost discipline: pay for runs only after hand-checking the outputs (the whole project)

This isn't a separate milestone so much as the habit that ran through all of the above. It deserves its own section, because it's the part most people skip.

**What we've spent, as far as we can document it:**

| item | cost | source |
|---|---|---|
| First smoke-run GPU (Vast A100 SXM4) | $1.07/hour, about 2:51-4:26 AM | progress log |
| 14B smoke run (Vast A100 SXM4, Utah) | about $0.79 at $0.935/hour | progress log (credit $92.21 → $91.43) |
| Frontier panel via OpenRouter | about $33.50 from per-call logs | `panel_costs.txt`, rerun logs |
| Outside reviews (GLM 5.3, DeepSeek V4 Pro) | $0.12 | review synthesis |
| Clean fine-tunes, 14B warm-ups, decoding sweep, best-of-16, v3 retrain | [TK] | [TK: pull from Vast billing] |
| **Total to date** | [TK] | |

**The habits that kept those numbers small:**

- **No GPU until the data is right.** The dataset was built and validated with zero GPU spend. The dataset doc says it in so many words: "using a rented GPU later and only after approval."
- **Destroy instances as soon as you're done, and check for strays.** At one point we found an old instance from an earlier attempt still running and killed it. Both overnight GPU sessions end in the log with the instance destroyed; the second one also confirms "instance list = 0."
- **Hold the expensive model until you've checked spend.** Opus waited in the panel queue until we'd confirmed the budget. When credit ran out mid-panel, we reran only the failed rows.
- **Read the outputs before you trust the score.** The 4:26 AM "SUCCESS" never turned into a bigger run, because opening the plugins showed JavaScript pretending to be QML and one that would have overwritten a Hyprland config. Every plugin headed to the Dell gets read first.
- **Gate the big spend behind a cheap experiment.** The decoding sweep (a few dollars) ruled out decoding settings. Best-of-16 (one sampling run) ruled out RL for now. The GRPO plan comes with a budget ($150-250), a hard stop ($300), and kill criteria (no improvement over the SFT checkpoint by step 100, reward collapse, or exploding length).

**What we learned:** The cheapest experiment is the one you don't run because a hand-check already answered the question. For a small team, "pay only for runs once outputs have been checked by a human" is a quality strategy as much as a cost strategy. Most of our most important findings cost almost nothing.

**Suggested figures:**
- Cumulative spend over the two days, annotated with each milestone. [TK: needs the Vast billing export.]
- A two-column comparison: "money we spent" vs. "money we didn't spend because a cheap check said no" (RL plan budget vs. best-of-16 cost; sweep vs. retrain).

---

## What's next, and what this post will become

This is the honest middle of the story, not the end. Usuba isn't ready. Our fine-tunes don't yet beat GPT-5.6 or Opus 5.5 on writing working Omarchy plugins, and on the hardest task they haven't scored a single pass. But we now have the things that make a real result possible: a training set where every row has a paper trail, a grader that matches real hardware with zero false passes in a blind test, and a clear prerequisite for RL that we can measure.

When the v3 numbers come in, this post will get its next section, whatever they say.

[TK: closing paragraph once v3 results are in: release plan for usuba.dev, license for weights and data, NOTICE completeness, how people can try it.]

*— Harris Kenny, OutboundSync*
