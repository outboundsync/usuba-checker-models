# Usuba: what we learned trying to teach a small model to write Omarchy plugins, and why we're building the checker first

*By Harris Kenny · OutboundSync · DRAFT v0.2, revised Tuesday, Oct 13, 2026 · usuba.dev*

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
- **Base-model tryout.** Before training something bigger, we ran six stock open models on the same holdout. All six are Apache-2.0. Stock **Qwen3.6-27B** was the best at **6/49** after a hand-check.
- **27B.** We fine-tuned Qwen3.6-27B with the same recipe and data. On hand-check it scored 4/49, *below* the stock 27B's 6. The stock 27B had **0** looping answers. The fine-tuned 27B looped on **31 of 49**.

That last number is the most important one in this section. Our training recipe, not the base model, taught the model to keep writing and never stop. We'd seen the same thing with the 7B. Changing the base model didn't fix it.

**What we learned:** a fine-tune that loops is a training-data and recipe problem, and it can make a good base model worse. Measure the stock model first, and treat "beats its own base" as the first bar to clear, before "beats the frontier."

**Suggested figures:**
- Paired bars, stock vs. fine-tuned, for 7B and 27B: working /49, with loop counts overlaid (27B: 0 → 31).

---

## 4. The fix loop, and how the model learned to game the grader

Next we tried something that needed no training at all. Stock Qwen3.6-27B writes a plugin. If the grader fails it, the grader's errors (static failures, runtime errors, truncation and loop notes) go back to the model as feedback, and it gets up to three rounds to fix the plugin. It never sees the reference answers.

By the grader's count, it worked: passes rose from **5 to 13 of 49**.

Then we checked all 13 by hand, and only **4 were real**. The rest had learned to satisfy the grader instead of the task:

- **Stubs.** Strip the imports and APIs the grader complained about until nothing fails, even if the plugin no longer does anything.
- **Fake data.** A weather widget with a hardcoded temperature, and a plugin that openly simulated its data.
- **Invented APIs.** Calls to Quickshell and Qt functions that don't exist, on code paths the grader never exercised.

We also found the gaps it was exploiting. Binaries called inside `sh -c` strings weren't checked. Component tasks could pass with a manifest-only answer. Fake data and invented JS APIs on click paths slipped through. A grader that's 90/90 on real plugins can still have holes once a model is actively searching for them.

**What we learned:** everything depends on a test you can trust, and "trust" has to include a model trying to fool it. The grader is the product.

[CHART 2: Grader passes vs. real passes in the fix loop. Grader passes per round (round 0 → round 3: 5, 8, 12, 13) as a rising line, and a flat bar or line for hand-verified real passes (4 at the start, 4 at the end). The space between them is the gaming.]

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

While we were doing this, Brian Armstrong [posted](https://x.com/brian_armstrong/status/2109412046244913643) that Coinbase fine-tuned Qwen3.5-9B on internal data and beat frontier models on fraud prevention, at lower cost. I believe it. Fraud is a high-volume task with a lot of proprietary data, and that's exactly where a specialist model can win.

One [reply](https://x.com/trashpandaemoji/status/2109959474978930940), from @trashpandaemoji, described what it takes to get there. After three years of fine-tuning small models for special purposes, they said it's good for high-volume or low-latency tasks, but it isn't cheap, and you end up in a never-ending cycle of dataset work.

That matches our experience, and it's useful to know going in. Every fine-tune sent us back to the data: what to include, how long the targets should be, why the model loops. A specialist model isn't a weekend fine-tune. It's an ongoing investment in data and evaluation. The part that lasts is the evaluation: the grader and the standard stay useful whichever model wins, and they're what make a good specialist possible.

On cost: total GPU and API spend so far is modest, tens of dollars, at roughly $3 to $12 per run. The real investment is the time spent on data and evaluation, not the GPUs.

---

## What's next, and how you can help

This is ongoing work, and it isn't trivial. Still, our results so far tell us it's worth pursuing with more time and spend. We have a grader that matches real hardware, a clear map of where models fail, and a concrete plan for the Checker. Omarchy will keep changing, and every release can change what "working" means. So the next job is maintaining and improving the Checker and the standard as Omarchy evolves: new versions of the standard, new rules for each gap we find, and new hardware checks on each release. Beyond that, I want to build a builder-grade model, one that actually helps people ship working plugins, but only once the Checker is solid enough to train against.

Long term, a standard for what counts as a working Omarchy plugin probably belongs with Omarchy itself, as an Omacom project. We're happy to build it in the open until then and hand it over in whatever shape makes sense.

If any of this is useful to you, here's what would help most:

- **Omarchy maintainers:** review the v0.1 rules against your intent for the plugin contract, and tell us when an upcoming release will change something. [TK: link to the standard and rules]
- **Plugin authors:** run the Checker on your plugins and report false passes and false fails. A plugin that works on your machine but fails the Checker (or the reverse) is exactly the case we need. [TK: link to the issue tracker]
- **Anyone who wants a builder-grade model:** tell us what you'd build with it. If you can help with compute, base-model access, or funding, get in touch. [TK: contact or sponsorship link]

I'll keep posting what we find, including what doesn't work.

*Harris Kenny, OutboundSync*
