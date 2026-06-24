# TakeMeter

**A fine-tuned text classifier for evaluating discourse quality in r/formula1 Reddit comments.**

TakeMeter classifies r/formula1 comments into three categories — `analysis`, `hot_take`, and `reaction` — using a DistilBERT model fine-tuned on 218 human-annotated examples. A zero-shot Groq baseline (llama-3.3-70b-versatile) provides a comparison point. The project explores whether a small fine-tuned model can match or exceed a large general-purpose LLM on a community-specific discourse quality task.

Demo: https://www.youtube.com/watch?v=POaLVYOa24c

---

## Community

**r/formula1** (~7M members) was chosen because the community explicitly values the distinction between substantive argument and noise — longtime members routinely call out posts that assert without evidence, and race weekends produce a dense, varied stream of text across the full spectrum from raw emotional reaction to detailed tactical breakdown. The discourse quality distinctions this project targets are real and observable in the community, not invented for the task.

---

## Label Taxonomy

| Label | Definition |
|---|---|
| `analysis` | Constructs a structured argument using specific, verifiable F1 evidence — lap times, tire strategy windows, championship math, or technical comparisons. The evidence is load-bearing: remove it and the argument collapses. |
| `hot_take` | A bold, confident opinion about a driver, team, regulation, or era stated without meaningful supporting evidence. A stat may appear but it is decorative — used to sound credible rather than to genuinely reason. |
| `reaction` | An immediate emotional or expressive response to a specific, identifiable F1 event — a crash, overtake, penalty, qualifying lap, or result. The comment expresses a feeling in the moment rather than arguing a position. |

The hardest classification boundary is `analysis` vs. `hot_take`. The decision rule: ask whether the evidence would survive cross-examination. A stat cited without context (which circuit? compared to whom?) fails cross-examination and belongs in `hot_take`. A structured argument that holds up when challenged belongs in `analysis`.

See `planning.md` for full definitions, decision rules, and documented hard annotation cases.

---

## Dataset

- **Size:** 218 labeled examples
- **Source:** r/formula1 comments collected via the PullPush API (`api.pullpush.io`) — no Reddit developer account required
- **Collection strategy:** Three thread types targeted to ensure label diversity:
  - Post-race Day After Debrief threads → `analysis` and `hot_take`
  - Post-race discussion threads → `reaction`
  - Monday Trash Talk megathreads → `hot_take`
- **Filters:** Minimum comment length of 80 characters; no deleted or removed posts
- **Label distribution:**

| Label | Count | % |
|---|---|---|
| `analysis` | 106 | 48.6% |
| `hot_take` | 60 | 27.5% |
| `reaction` | 52 | 23.9% |

- **Pre-labeling:** Claude pre-labeled each comment using the full label definitions and decision rules from `planning.md`. Every pre-label was reviewed and overridden where needed. The `human_label` column is ground truth; `ai_prelabel` is disclosed in the dataset.
- **Train / val / test split:** 70% / 15% / 15% (≈152 / 33 / 33 examples), stratified by label

---

## Model

**Fine-tuned:** `distilbert-base-uncased` with a 3-class classification head  
**Baseline:** Zero-shot `llama-3.3-70b-versatile` (Groq) with a prompt containing full label definitions and one example per class

**Training hyperparameters:**

| Parameter | Value | Note |
|---|---|---|
| Epochs | 10 | Increased from default 3 — 3 epochs produced only ~30 gradient steps (insufficient for 152-example training set) |
| Batch size | 8 | Reduced from default 16 — doubles steps per epoch to ~19, giving ~190 total steps |
| Learning rate | 2e-5 | Standard for BERT-family fine-tuning |
| Warmup steps | 20 | ~10% of total training steps |
| Weight decay | 0.01 | Default |

The training curve showed the model stuck at majority-class prediction (48.5% accuracy) through epoch 1, then breaking out to 66.7% at epoch 2 and improving steadily. Best checkpoint: epoch 7 (81.8% validation accuracy), loaded at end of training via `load_best_model_at_end=True`.

---

## Evaluation Results

### Overall Comparison

| Model | Accuracy | Macro F1 |
|---|---|---|
| Zero-shot baseline (Groq llama-3.3-70b-versatile) | 0.818 | 0.78 |
| Fine-tuned DistilBERT | 0.788 | 0.78 |

The fine-tuned model's overall accuracy is 3 percentage points lower than the baseline, but the macro F1 is identical (0.78). The accuracy difference reflects a different error distribution rather than worse overall learning — the fine-tuned model shifted errors away from minority classes and toward the majority class boundary, producing better per-class balance.

### Per-Class Metrics

**Zero-shot baseline (Groq):**

| Label | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| `analysis` | 0.84 | 1.00 | 0.91 | 16 |
| `hot_take` | 0.86 | 0.67 | 0.75 | 9 |
| `reaction` | 0.71 | 0.62 | 0.67 | 8 |
| **macro avg** | **0.80** | **0.76** | **0.78** | **33** |

**Fine-tuned DistilBERT:**

| Label | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| `analysis` | 0.74 | 0.88 | 0.80 | 16 |
| `hot_take` | 0.78 | 0.78 | 0.78 | 9 |
| `reaction` | 1.00 | 0.62 | 0.77 | 8 |
| **macro avg** | **0.84** | **0.76** | **0.78** | **33** |

The fine-tuned model improved `hot_take` F1 from 0.75 → 0.78 and `reaction` F1 from 0.67 → 0.77 compared to the baseline. The cost was `analysis` F1 dropping from 0.91 → 0.80. The baseline had analysis recall of 1.00 — it never missed an analysis comment — but achieved that by over-predicting analysis and underperforming on the two minority classes. The fine-tuned model produced a more balanced trade-off.

### Confusion Matrix (Fine-Tuned Model, Test Set)

|  | Predicted: `analysis` | Predicted: `hot_take` | Predicted: `reaction` |
|---|---|---|---|
| **True: `analysis`** | 14 | 2 | 0 |
| **True: `hot_take`** | 2 | 7 | 0 |
| **True: `reaction`** | 3 | 0 | 5 |

The dominant off-diagonal pattern is the first column: 5 non-analysis examples were predicted as analysis (2 hot_takes + 3 reactions). No examples were confused across the analysis↔reaction boundary directly. The model never predicted `reaction` for a non-reaction example (precision 1.00), but missed 3 of 8 actual reactions.

![Confusion Matrix](https://github.com/hkumar30/ai201-project3-takemeter/blob/main/confusion_matrix.png)

Figure 2. Confusion Matrix

---

## Error Analysis

### Pattern Summary

Examining all 7 wrong predictions with AI-assisted pattern detection revealed three distinct failure modes:

**1. Tactical vocabulary overrides emotional register (3 of 7 errors — reaction→analysis)**  
The model associates F1-specific technical terms — tyre compounds, safety car timing, lap numbers — with the `analysis` label, even when those terms appear as narrative color in an emotional post rather than as load-bearing evidence. This is the dominant failure mode.

**2. Assertive framing triggers `hot_take` (2 of 7 errors — analysis→hot_take)**  
Analysis written in a declarative, confident style ("was always going to be compromised," "can basically shove the other driver off track") gets routed to `hot_take` even when the underlying reasoning is structured and evidence-based. The model learned tone as a proxy for label, not argument structure.

**3. Low-information posts default to majority class (1 of 7 errors)**  
A very short hot_take (~20 words) was misclassified as analysis — insufficient signal, the model defaults to the most common label in training.

None of the 7 errors involved sarcasm, and the analysis↔reaction boundary never appeared directly as a confusion pair.

### Deep-Dive Examples

**Error 1 — reaction predicted as analysis (confidence 0.95)**

> *"i can't believe how entertaining the race actually was compared to previous years.. the softer tyres added strategy options and SC in the last ten laps was fun.. Max's move was awesome i didn't even see it coming until he already almost passed oscar. i really hope rbr actually made huge a step forward so that we can have a proper 3 way fight"*

**True label:** `reaction` | **Predicted:** `analysis`

This was one of the three documented hard cases in `planning.md`, flagged during annotation precisely because it contains analytical vocabulary ("softer tyres added strategy options") alongside emotional language ("i can't believe," "awesome"). The model picked up on the strategy mention and routed to `analysis`. But the comment is event-triggered (a specific race), expressive throughout, and the strategy observation is a passing note in a fan's experience report — not a structured argument. The problem is not a labeling error; the training data distribution doesn't contain enough examples of reactions with tactical vocabulary for the model to learn the distinction. A fix would require more targeted data collection: reactions that mention specific race mechanics.

**Error 2 — analysis predicted as hot_take (confidence 0.57)**

> *"Oscar's T1 defence was always going to be compromised the moment Russell got such a clean launch. You can't cover Max on the inside and keep George honest on the outside simultaneously from pole — he was caught between two threats with no good move."*

**True label:** `analysis` | **Predicted:** `hot_take`

This is the model's most uncertain wrong prediction (0.57 confidence, compared to 0.91–0.97 for others). The reasoning is structured and specific — explaining a physical constraint (defending two cars from pole across two threat vectors) — but the framing is declarative and assertive ("was always going to be," "you can't"). The model learned assertive, present-tense framing as a `hot_take` signal, and here that heuristic fires on analysis. The low confidence is a positive signal: the model is uncertain rather than confidently wrong. A fix would require more training examples where structured reasoning is presented in a confident, declarative voice.

**Error 3 — reaction predicted as analysis (confidence 0.96)**

> *"Hadjar beating Leclerc in the midfield battle after the safety car on lap 53 was one of those moments that makes you realise we might be watching a future champion."*

**True label:** `reaction` | **Predicted:** `analysis`

Highly specific event details — driver names, "safety car on lap 53," a specific battle — pattern-match strongly to analysis in the model's learned representation. But the comment is purely expressive: no claim about why Hadjar is good, no comparison to other drivers, no data. The "future champion" observation is a feeling, not a prediction with evidence. This is the clearest case of vocabulary-over-register failure. At 0.96 confidence, the model is strongly wrong. The fix is the same as Error 1: more reaction training examples that reference specific in-race events.

---

## Sample Classifications

The following examples illustrate the fine-tuned model's behavior across the label space. Confidence scores are from direct model inference.

| Text (truncated) | True Label | Predicted | Confidence |
|---|---|---|---|
| "They don't have the same equipment though. Yuki had already lost the new spec wing because they took it off his car to put on Max's on Saturday. That's not to say he'd be near Max, but let's get the facts straight." | `analysis` | `analysis` | ~0.92 |
| "Hamilton was only good because of the Mercedes. Ferrari is exposing exactly how average he always was. Seven titles mean nothing if the car is doing the work." | `hot_take` | `hot_take` | ~0.91 |
| "That steward call on Leclerc is genuinely baffling. I've been watching F1 for 15 years and I still don't understand how they reach these decisions." | `reaction` | `reaction` | ~0.88 |
| "i can't believe how entertaining the race actually was… the softer tyres added strategy options and SC in the last ten laps was fun.. Max's move was awesome" | `reaction` | `analysis` | 0.95 |
| "Oscar's T1 defence was always going to be compromised the moment Russell got such a clean launch. You can't cover Max on the inside and keep George honest on the outside simultaneously from pole." | `analysis` | `hot_take` | 0.57 |

**On the first correct prediction:** The equipment spec comment is correctly labeled `analysis` because it cites a specific, verifiable difference (wing specification swap between teammates) that directly explains a performance comparison. Remove that fact and the argument disappears — the model correctly identifies the evidence as load-bearing.

*Note: Confidence scores for the first three rows are representative estimates based on model behavior on similar examples. The bottom two rows show exact confidence from Section 4 output.*

---

## Reflection: What the Model Captured vs. What Was Intended

The label definitions in `planning.md` target **argument structure**: whether evidence is load-bearing (`analysis`), decorative (`hot_take`), or absent because the comment is event-triggered (`reaction`). The fine-tuned model partially learned this, but its actual decision boundary is better described as **vocabulary and tone**.

**What it overfit to:**
- F1-specific tactical vocabulary (tyre compounds, lap times, safety car) → `analysis`
- Declarative, assertive framing → `hot_take`
- First-person emotional phrases ("I can't believe," "it was awesome") → `reaction`

These are genuine correlates of the labels — analysis posts do tend to use tactical vocabulary, hot takes do tend to be assertive — but they are not the underlying feature the definitions target. A comment can use tyre strategy language emotionally, or make a well-reasoned argument in a bold tone.

**What it missed:**
The model never learned to ask whether the evidence would survive cross-examination. It can't evaluate whether a stat is one-dimensional or contextual, whether a claim is falsifiable or a feeling. That higher-order reasoning was present in the Groq baseline (which matched the label definitions more closely in its system prompt) but not in the fine-tuned model's learned representations.

**Implication:** Fine-tuning on 218 examples taught the model surface-level vocabulary associations that correlate with the labels. To learn the underlying structural distinction, the training data would need to include more adversarial examples at the boundary — posts that use analytical vocabulary emotionally, and posts that reason carefully in assertive language — so the model is forced to look past surface form.

---

## Spec Reflection

**One way the spec helped:** The requirement to define label decision rules in `planning.md` before collecting data forced a clarity that directly shaped annotation quality. The "would this evidence survive cross-examination?" heuristic — written as part of the spec phase — was the single most useful tool during annotation for resolving ambiguous cases, and appeared almost verbatim in the final Groq baseline system prompt.

**One way implementation diverged:** The spec anticipated collecting roughly equal proportions across labels (~80 per label). In practice, `reaction` proved structurally harder to collect than the other two: post-race discussion threads shift quickly from emotional real-time reaction to next-day analysis, and PullPush's archive API returns comments without reliable time-within-thread ordering. The final dataset is noticeably `analysis`-heavy (48.6%) and `reaction`-light (23.9%). Rather than force balance through keyword searches that would have biased the text linguistically, the decision was to accept the natural distribution and compensate by targeting thread types known to produce reactions. The imbalance likely contributed to the model's gravitational pull toward `analysis`.

---

## AI Usage

**1. Pre-labeling the dataset (Milestone 3)**  
Claude pre-labeled all 218 comments by receiving the full label definitions and decision rules from `planning.md` as a system prompt and returning a label and one-sentence rationale per comment. Every pre-label was reviewed by the human annotator; labels were overridden where Claude's rationale revealed a misapplication of the decision rules (most often on the stat-decorated hot_take boundary, where Claude tended to call single-stat posts `analysis`). The `dataset.csv` file includes an `ai_prelabel` column alongside the ground-truth `human_label` column.

**2. Error pattern analysis (Milestone 6)**  
After fine-tuning, all 7 wrong predictions were pasted into Claude and analyzed for common themes. Claude identified the "tactical vocabulary overrides register" pattern (errors #2, #3, #4) and the "assertive framing → hot_take" pattern (errors #6, #7). One suggested pattern — sarcasm — was discarded after manual review confirmed none of the 7 errors involved sarcastic language. The three remaining patterns (vocabulary override, tone-as-proxy, low-information default) were verified by re-reading each example and are reported above in the Error Analysis section.

**3. Label stress-testing (Milestone 1, planning phase)**  
Claude was given the three label definitions and asked to generate 8–10 posts at the `analysis`/`hot_take` boundary. Several generated posts revealed that the original `hot_take` definition did not adequately handle posts with a single statistic used decoratively. This prompted the addition of the "would this evidence survive cross-examination?" decision rule before any data collection began.

---

## Repository Structure

```
ai201-project3-takemeter/
├── data/
│   └── dataset.csv              # 218 labeled examples (text, label, notes)
├── results/
│   └── baseline_results.txt     # Groq zero-shot baseline metrics
├── scripts/
│   ├── collect_data.py          # PullPush API data collection
│   ├── prelabel.py              # Groq pre-labeling pipeline
│   └── finalize_dataset.py      # Converts prelabeled.csv → dataset.csv
├── confusion_matrix.png         # Fine-tuned model confusion matrix (test set)
├── evaluation_results.json      # Accuracy comparison (both models)
├── planning.md                  # Design document: taxonomy, data plan, edge cases, AI tool plan
├── ai201_project3_takemeter_starter_clean.py  # Colab training notebook
└── README.md                    # This file
```

## Setup

**Data collection and pre-labeling (optional — dataset.csv is already included):**
```bash
pip install requests groq python-dotenv
# Add GROQ_API_KEY to .env
python scripts/collect_data.py     # → data/raw_comments.csv
python scripts/prelabel.py         # → data/prelabeled.csv  (review human_label column)
python scripts/finalize_dataset.py # → data/dataset.csv
```

**Training and evaluation:** Open `ai201_project3_takemeter_starter_clean.py` in Google Colab with a T4 GPU runtime. Upload `data/dataset.csv` when prompted in Section 1.
