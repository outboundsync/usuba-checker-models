# Usuba: what we learned trying to teach a small model to write Omarchy plugins, and why we're building the checker first

*By Harris Kenny · OutboundSync · DRAFT v0.3, revised Tuesday, Oct 13, 2026 · usuba.dev*

> Draft status: this is a work-in-progress post, not a launch. Every number below comes from our working repo (the READMEs in `runs/rescore404`, `runs/basetry`, `runs/q27` and `runs/fixer`). Anything we haven't confirmed or built yet is marked [TK].

Here's the short version. We set out to build a small, open, local model that does one job: write Omarchy shell plugins that actually work. That means Quickshell/QML plugins for the Omarchy 4 shell on Hyprland.

Here's the honest version. Our fine-tunes didn't beat the stock models they started from. The most useful things we built were a grader we can trust and a clear picture of what "working" means. So we're changing the order. The first Usuba release will be a **checker**, plus a public standard for what counts as a working Omarchy plugin. A model that builds plugins comes later, and it will be trained and judged against that checker.

[CHART 1, hero: Frontier scoreboard. Working plugins out of 49 on the hardware-calibrated grader, with loops counted as fails. Human reference 26, GPT-5.6 20, Opus 18, Sonnet 10, Grok-build 10, stock Qwen 14B 4, stock Qwen 7B 3. Draw the human reference as a reference line.]

---

## 1. First, a grader that matches a real laptop

Omarchy plugins are a small, fast-moving dialect of QML with a strict contract: the manifest, the shell's singletons and theme API, the bar API, and which binaries actually exist on a stock install. General coding models know QML. They don't know *this* QML, and when they guess, the guesses look plausible and fail quietly.

A plugin can pass a manifest check and still do nothing. We found that out early, so the first real piece of work was a functional test. It's a headless Quickshell harness that installs a plugin into the real Omarchy shell, runs it, and checks whether it loads, renders something visible, and keeps its logs free of real errors.

We calibrated it against my own Dell laptop running Omarchy 4.0.4. A few things that took:

- Matching the shell tree on the Dell exactly.
- Pruning the list of "available" binaries to what `command -v` finds on the Dell. 54 binaries we had assumed were present aren't there on a stock install, including walker, mako, playerctl, hyprlock and alacritty.
- Treating a few harmless warnings the way the real shell treats them, so working plugins don't fail on noise.
- Labeling real runs on the Dell by eye and treating those labels as the answer key.

Against that hardware-verified answer key, the grader scores **90/90**, with no false passes.

**What we learned:** a grader you haven't checked against real hardware is a guess. Everything else in this post depends on this one piece.

**Suggested figures:**
- The Dell running Omarchy 4.0.4 next to a diagram of the harness: plugin → real Omarchy shell under headless Quickshell → screenshot, log and probes → verdict. [TK: photo]
- Before/after bar strips for a couple of plugins, each labeled WORKS or BROKEN.

---

## 2. The scoreboard: frontier models, people, and stock open models

With a grader we trust, we scored everyone on the same 49 held-out plugin tasks. A loop or a truncated answer counts as a fail.

| who | working plugins /49 |
|---|---|
| human reference (the real plugins) | 26 |
| GPT-5.6 | 20 |
| Opus | 18 |
| Sonnet | 10 |
| Grok-build | 10 |
| stock Qwen 14B | 4 |
| stock Qwen 7B | 3 |

Why is the human reference only 26 and not 49? Many of the reference answers are Omarchy's own first-party plugins. 18 of the 20 first-party answers in the holdout come from a newer Omarchy tree and fail on 4.0.4. That's the grader working as intended: it judges against the Omarchy on the laptop, not the one on `main`.

So the best frontier model is within six plugins of the human reference. The small open models are near the floor.

---

## 3. Fine-tuning: it didn't beat stock

The original bet was that fine-tuning a small open model on real, permissively licensed Omarchy plugins would close that gap. It didn't.

- **7B.** Our latest 7B fine-tune scored 4/49, with 32 answers looping. That's within the ±1 noise of the stock models (stock 7B 3, stock 14B 4). It isn't a real gain.
- **Base-model tryout.** Before training something bigger, we ran six stock open models on the same holdout. All six are Apache-2.0. Stock **Qwen3.6-27B** was the best at **6/49** after manual review.
- **27B.** We fine-tuned Qwen3.6-27B with the same recipe and data. On manual review it scored 4/49, *below* the stock 27B's 6. The stock 27B had **0** looping answers. The fine-tuned 27B looped on **31 of 49**.

That last number is the most important one in this section. Our training recipe, not the base model, taught the model to keep writing and never stop. We'd seen the same thing with the 7B. Changing the base model didn't fix it.

**What we learned:** a fine-tune that loops is a training-data and recipe problem, and it can make a good base model worse. Measure the stock model first, and treat "beats its own base" as the first bar to clear, before "beats the frontier."

**Suggested figures:**
- Paired bars, stock vs. fine-tuned, for 7B and 27B: working /49, with loop counts overlaid (27B: 0 → 31).

---

## 4. The fix loop, and how the model learned to game the grader

Next we tried something that needed no training at all. Stock Qwen3.6-27B writes a plugin. If the grader fails it, the grader's errors (static failures, runtime errors, truncation and loop notes) go back to the model as feedback, and it gets up to three rounds to fix the plugin. It never sees the reference answers.

By the grader's count, it worked: passes rose from **5 to 13 of 49**.

Then we reviewed all 13 manually, and only **4 were real**. The rest had learned to satisfy the grader instead of the task:

- **Stubs.** Strip the imports and APIs the grader complained about until nothing fails, even if the plugin no longer does anything.
- **Fake data.** A weather widget with a hardcoded temperature, and a plugin that openly simulated its data.
- **Invented APIs.** Calls to Quickshell and Qt functions that don't exist, on code paths the grader never exercised.

We also found the gaps it was exploiting. Binaries called inside `sh -c` strings weren't checked. Component tasks could pass with a manifest-only answer. Fake data and invented JS APIs on click paths slipped through. A grader that's 90/90 on real plugins can still have holes once a model is actively searching for them.

**What we learned:** everything depends on a test you can trust, and "trust" has to include a model trying to fool it. The grader is the product.

[CHART 2: Grader passes vs. real passes in the fix loop. Grader passes per round (round 0 → round 3: 5, 8, 12, 13) as a rising line, and a flat bar or line for manually verified real passes (4 at the start, 4 at the end). The space between them is the gaming.]

**Suggested figures:**
- Two or three short excerpts of "passing" plugins, annotated: a stub, a hardcoded value, an invented API call.

---

## 5. The pivot: the Usuba model family, Checker first

Here's the new plan.

**Usuba Checker comes first.** It's a hardened checker plus a public, versioned standard that defines a working Omarchy plugin. Version **v0.1 targets Omarchy 4.0.4**. Every rule has an id, a reason, and a fix hint, so a failure tells you (or a model) exactly what's wrong and how to fix it, not just "fail." It closes the gaps the fix loop found.

It's in progress, and it isn't done until it verifies against the Dell, the same way the grader did. [TK: link to the standard and the rule list once published.]

**Usuba Builder comes later.** It will use a stronger base model and be trained and judged against the Checker. That ordering is the whole lesson of this post. We shouldn't train or optimize anything against a test that can be gamed.

Why make the standard public? Plugin authors get a clear target and readable failures. Omarchy gets a written definition of "working" that can move with each release. And anyone's model, ours or not, can be measured against the same ruler.

**Suggested figures:**
- A sample Checker failure: rule id, reason and fix hint. [TK: real example once the rule format is final.]
- A roadmap strip: Checker + standard v0.1 (Omarchy 4.0.4) → verified on the Dell → Usuba Builder on a stronger base.

---

## 6. What specialist models really take

A big part of the inspiration for this project came from the Coinbase team, who are also a sponsor. While we were doing this, Brian Armstrong [posted](https://x.com/brian_armstrong/status/2109412046244913643) that Coinbase fine-tuned Qwen3.5-9B on internal data and beat frontier models on fraud prevention, at lower cost. I believe it. Fraud is a high-volume task with a lot of proprietary data, and that's exactly where a specialist model can win.

One [reply](https://x.com/trashpandaemoji/status/2109959474978930940), from @trashpandaemoji, described what it takes to get there. After three years of fine-tuning small models for special purposes, they said it's good for high-volume or low-latency tasks, but it isn't cheap, and you end up in a never-ending cycle of dataset work.

That matches our experience, and it's useful to know going in. Every fine-tune sent us back to the data: what to include, how long the targets should be, why the model loops. A specialist model isn't a weekend fine-tune. It's an ongoing investment in data and evaluation. The part that lasts is the evaluation: the grader and the standard stay useful whichever model wins, and they're what make a good specialist possible.

On cost: total GPU and API spend so far is modest, tens of dollars, at roughly $3 to $12 per run. The real investment is the time spent on data and evaluation, not the GPUs.

---

## 7. Back to the Dell: a full sweep on real hardware (2026-10-13)

Next we stopped sampling and ran the whole plugin set on the reference laptop running Omarchy, using the Usuba Checker scripts as the reference.

**The answer key got better.** Agreement between the Checker scripts and the answer key went from 45/52 to **52/52**.

**The desktop broke, and we re-ran it.** 194 jobs were invalid. An audio-control plugin rerouted system audio, and the desktop shell grew to 13 GB and ran out of memory. We threw those jobs out and re-ran them. Final labels: **3,942 works, 1,001 broken, 589 unsure.**

**A new severity rule.** A QML message fails a plugin only if it stops a component from being created. Everything else is a warning. Under that rule, no plugin passes the Checker scripts and then fails to load on the Dell. For loading, the scripts are stricter than the hardware.

**But loading isn't using.** 137 plugins pass the scripts and have problems only the hardware shows in use:

- 68 where the toggle opens nothing
- 62 that call a missing binary
- 7 with memory growth over 150 MB in 20 seconds

82 bugs showed up only in use. That gave us new checks: **D01** audio routing, **D02** panel with no toggle, **D04** close/reopen cycle, and **D05** runaway memory (precision 0.75, recall 0.27).

**What we learned:** the scripts already handle "does it load." What's left is "does it work when you click it."

[CHART 3: Dell sweep labels: 3,942 works / 1,001 broken / 589 unsure, plus a breakdown of the 137 in-use-only problems (68 / 62 / 7).]

---

## 8. Re-checking the grader, and an out-of-sample test

We re-ran the full answer key on the real-runtime grader. It found a crash and one miss on `main`. After the fixes, it agrees on **90/90 decided cases**.

Then we checked it out of sample, against bug issues filed on GitHub. That confirmed the severity rule for loading. It also turned up a bug we weren't catching: a panel that can't close, caused by writing to the read-only property `centerHoverRevealSuppressed`. It's in 117 plugins the Dell had marked as working. That became a new warning, **USB-D06**, which catches 15 of 19 such issues.

**What we learned:** even a hardware-verified answer key has blind spots. Real bug reports from real users are the next ruler.

---

## 9. When a model is worth it, and the bar it has to clear

This changed how I think about the model. The case for the Usuba Checker model isn't load checks. The scripts already do that. The case is **HANCORE-style review** (HANCORE is the Omarchy plugin reviewer) plus the in-use problems that only show up on hardware.

So the bar is concrete. The model has to beat a frontier model run as a skill on the 329-plugin HANCORE holdout, on accuracy, cost and speed. If it doesn't, the honest release is the Checker scripts plus a skill, not a model. For reference, the Checker-only baseline on that holdout is accuracy **0.650**, with false alarms on negatives at **0.586**.

The base model is locked: **Qwen 3.5 9B, 4-bit (~5.5 GB)**, so it runs on a 32 GB laptop without a GPU.

---

## 10. Training the Usuba Checker model [PENDING RESULTS]

The training set is built: **4,592 train and 148 val examples**, with provenance on every row:

| source | rows |
|---|---|
| HANCORE review | 3,114 |
| missing binary | 396 |
| toggle/memory | 75 |
| panel can't close | 104 |
| verified broken | 397 |
| verified works | 506 |

The holdout is excluded by repo, by manifest id and by near-duplicate code.

The plan is a bf16 LoRA on one H100 80GB on Vast, about 6 hours and roughly $20, then export to 4-bit. **Training hasn't run yet.** [TK: results against the 329-plugin HANCORE holdout vs. a frontier model as a skill.]

---

## What's next, and how you can help

I want to be straight about this: it has been a lot of work. Calibrating a grader against a real laptop, sweeping thousands of plugins on hardware, re-running jobs after an audio plugin took down the desktop, chasing bugs through GitHub issues, building a training set with provenance on every row. None of it was quick, and most of it was data and evaluation, not GPUs.

Omarchy will keep changing, and every release can change what "working" means. So the Usuba Checker scripts and the standard need ongoing maintenance: new rules for each gap we find, and new hardware checks on each release. The Usuba Checker model needs the same, starting with the holdout comparison above.

Long term, a standard for what counts as a working Omarchy plugin probably belongs with Omarchy itself, as an Omacom project. We're happy to build it in the open until then and hand it over in whatever shape makes sense.

I'd love help maintaining and improving all of this:

- **Omarchy maintainers:** review the rules against your intent for the plugin contract, and tell us when an upcoming release will change something. [TK: link to the standard and rules]
- **Plugin authors:** run the Usuba Checker scripts on your plugins and report false passes and false fails, especially in-use bugs. [TK: link to the issue tracker]
- **Anyone who wants to help with the model:** help us evaluate and improve the Usuba Checker model, or contribute compute or funding. [TK: contact or sponsorship link]

And I'm still interested in a builder-grade model, one that actually helps people ship working Omarchy plugins. The Checker is what makes that possible to train honestly. If you want that too, get in touch.

I'll keep posting what we find, including what doesn't work.

*Harris Kenny, OutboundSync*
