# TakeMeter — planning.md

> Complete this document before writing any implementation code.
> Your label taxonomy and data plan are what you'll use to direct AI tools (Claude, etc.) to assist with annotation and failure analysis — the more specific they are, the more useful that assistance will be.
> Update this file before starting any stretch features.

---

## Community

**Chosen community:** r/formula1

r/formula1 is one of the largest sports communities on Reddit (~7M members), with active daily discussion threads, post-race analysis, driver debates, and live race commentary. It is a strong fit for this task because the community explicitly values the distinction between substantive argument and noise — longtime members routinely call out posts that assert without evidence, and race weekends produce a dense, varied stream of text across the full spectrum from raw emotional reaction to detailed tactical breakdown. The discourse quality distinctions that matter to this community are real and observable, not invented for the task.

---

## Label Taxonomy

### Label 1: `analysis`

**Definition:** The post constructs a structured argument using specific, verifiable F1 evidence — lap time data, sector splits, tire degradation rates, championship points math, historical driver/team comparisons with named statistics, or technical mechanical reasoning. The evidence is load-bearing: remove it, and the argument collapses.

**Example 1 (real comment, r/formula1):**
> "Was it really a bad strategy though? It looked like a good move to me until the VSC. Didn't he come out in front of Alonso as well? I've watched Williams give Albon this one stop strategy so many times and it usually doesn't produce great results. The one time he actually benefits from a safety car while going longer on tires and suddenly it's a good strategy? Sometimes the end result is due to strategy and sometimes it's luck."

*Why analysis:* Cites specific tactical elements (VSC timing, one-stop strategy pattern, relative track position vs. Alonso) and distinguishes between outcome and decision quality — a genuine analytical structure.

**Example 2 (real comment, r/formula1):**
> "They don't have the same equipment though. Yuki had already lost the new spec wing because they took it off his car to put on Max's on Saturday. He then has an entirely old spec on Sunday. That's not to say he'd be near Max, but let's get the facts straight."

*Why analysis:* Corrects a comparison by citing a specific, verifiable equipment difference (spec wing allocation) that changes the interpretation of the performance gap.

---

### Label 2: `hot_take`

**Definition:** A bold, confident opinion or claim about a driver, team, regulation, or era stated without meaningful supporting evidence. The post may include a statistic or two, but the evidence is decorative — used to sound credible — rather than as part of a genuine argument. The framing is assertive rather than reasoned.

**Example 1:**
> "Hamilton was only good because of the Mercedes. Ferrari is exposing exactly how average he always was. Seven titles mean nothing if the car is doing the work."

*Why hot_take:* Makes a sweeping historical claim with no data. The assertion is the entire post — there is no evidence to remove.

**Example 2:**
> "The hybrid era ruined F1. Racing was genuinely better when drivers had to fight the car, not manage a battery. Liberty Media turned this into a Netflix show, not a sport."

*Why hot_take:* States strong opinions about a regulation era and media ownership without any comparative race data, viewership figures, or on-track metrics. Confident framing with no supporting structure.

---

### Label 3: `reaction`

**Definition:** An immediate emotional or expressive response to a specific, identifiable F1 event — a crash, overtake, penalty decision, qualifying lap, race result, or team announcement. The post expresses a feeling in the moment rather than arguing a position. Reactions are event-triggered; they would not exist without a specific triggering moment.

**Example 1:**
> "LANDO JUST TOOK P1 WITH TWO LAPS TO GO I CANNOT BREATHE. PAPAYA ABOVE ALL."

*Why reaction:* Triggered by a specific on-track event. Expresses emotional intensity. No claim or argument is made.

**Example 2:**
> "That steward call on Leclerc is genuinely baffling. I've been watching F1 for 15 years and I still don't understand how they reach these decisions."

*Why reaction:* Expresses frustration about a specific in-race decision. The sentiment is the point — there's no argument about what the correct penalty should have been or why the stewards were wrong on the merits.

---

### Hardest Anticipated Edge Case: The Stat-Decorated Hot Take

**Example:**
> "Hamilton's average qualifying gap to Leclerc this season is +0.4 seconds. No seven-time champion performs at that level. He's clearly finished."

**Why it's hard:** This post includes a specific statistic, which superficially resembles `analysis`. But the stat is one-dimensional, stripped of context (which circuits? what conditions? how does it compare to Leclerc's prior teammates?), and exists to decorate an assertion rather than to reason through one.

**Decision rule:** Ask: *would this evidence survive cross-examination?* If the data is presented without context, uses a single metric to support a sweeping conclusion, or would evaporate if challenged with "but what about X?" — it's `hot_take`. If the post would hold up when you ask "is this cherry-picked?" and the reasoning structure remains after you remove the emotional framing, it's `analysis`. The one-stat post above fails cross-examination: a fair analysis would compare to Leclerc's gap against his own prior teammates, control for circuit type, and acknowledge sample size.

**Secondary edge case: Reaction that contains an argument.** A post like *"That penalty was wrong — the stewards have given identical moves a pass three times this season already."* starts as a reaction but makes a pattern-based claim. Decision rule: if the argumentative content would stand on its own without the triggering event, label it `hot_take`. If you remove the argument and only the emotional response remains, label it `reaction`. The example above is `hot_take` — the "three times this season" claim is a pattern assertion that exists independent of the immediate event.

---

## Data Collection Plan

**Source:** r/formula1 comments collected via the PullPush API (`api.pullpush.io`), which archives Reddit data and allows filtering by subreddit, date range, and score.

**What to collect:** Comments (not post titles) from three thread types to ensure label diversity:
- **Post-race "Day After Debrief" threads** — highest density of `analysis` and `hot_take`
- **Live race discussion megathreads** — highest density of `reaction`
- **Standalone opinion/debate posts** — mix of `hot_take` and `analysis`

**Filters:** Minimum comment length of 80 characters (eliminates "lol" and single-sentence non-starters that can't be labeled reliably). No score floor — low-score comments are valid examples of poor-quality takes.

**Target:** 240 labeled examples (buffer above the 200 minimum to allow for drop-off during cleaning). Target split: ~80 per label to maintain balance. No label should exceed 70% of the dataset.

**Train / validation / test split:** 70% / 15% / 15% (roughly 168 / 36 / 36 examples).

**Labeling process:** Label each comment independently before looking at score or replies. Record the label, a confidence flag (sure / unsure), and a short note for any unsure cases. Unsure cases will be revisited after labeling the full batch, using the decision rules above.

**Label distribution target:** ~33% per label. If any label falls below 20% after initial collection, collect additional examples from thread types that produce that label.

---

## Evaluation Metrics

**Primary metric: Macro F1**

Macro F1 averages F1 score equally across all three classes, regardless of class size. This is the right choice here because:
1. The classes should be roughly balanced (target ~33% each), so macro and weighted F1 will be similar — but macro is more honest if balance drifts.
2. A model that learns to predict `hot_take` 80% of the time and ignores `reaction` would score high on accuracy but low on macro F1. Macro F1 penalizes that behavior.

**Secondary metrics:** Per-class precision, recall, and F1 for all three labels. Precision and recall reveal different failure modes: low precision means the model over-predicts a label; low recall means it misses examples of a label.

**Also reported:** Confusion matrix showing where the model confuses label pairs — specifically, I expect the `analysis` / `hot_take` boundary to produce the most confusion.

**Baseline:** Zero-shot Groq (llama-3.3-70b-versatile) with a prompt that provides label definitions and asks for one of the three labels. Same test set, same metrics.

---

## Definition of "Good Enough"

The fine-tuned model must achieve:
- **Macro F1 ≥ 0.70** on the held-out test set
- **No individual class F1 below 0.55** (a model that collapses one class entirely is not useful)
- **Outperform the zero-shot baseline on macro F1** (if fine-tuning doesn't beat zero-shot, the labeled dataset is not providing signal)

A macro F1 of 0.70 on a three-class subjective task with ~36 test examples is a meaningful threshold — it reflects genuine learning without demanding near-perfect accuracy on a task where even humans would disagree on 10–15% of cases.

---

## AI Tool Plan

**Milestone 1 — Label stress-testing:**
I will give Claude the three label definitions and the decision rules, then present 10–15 real r/formula1 comments and ask it to classify each and explain its reasoning. Where Claude's classification disagrees with mine, I will investigate whether the label boundary needs sharpening or whether the example is a genuine edge case. This is label stress-testing, not annotation — the goal is to find holes in the definitions before committing to labeling 200 examples.
