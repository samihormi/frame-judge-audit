> **FOLLOW-UP RESOLVED IT.** S2b (`reports/FINAL_RESULT.md`) re-ran this factorial with S1's
> original 248-char search text. Its manipulation check PASSED (P(search>=2) 13.0% -> 24.0%)
> and the search effect reappeared at the S1 magnitude (+7.3 pp; MH combined with S1
> **+7.63 pp [+2.23, +13.04]**, pooled p = 0.006). So S2's null was a failed manipulation, as
> this document concluded. Read FINAL_RESULT.md for the standing result.

# S2 — the clean factorial did NOT replicate the search effect, and the manipulation check says why

Preregistered in `protocol/s2/PREREG_FACTORIAL.md` before collection. 480 draws, four cells,
**one batch**, `max_tokens=8192`, seeds 1210000+. Built to repair three material defects the
independent review found in S1: the S1 "2×2" was not factorial, its frame arm carried an added
unreality clause, and that arm had no concurrent control.

## Design integrity (verified before launch)

`C11 == C10 + " " + C01` exactly. FRAME (120 chars) and SEARCH (121 chars) are length-matched,
byte-identical across their respective rows and columns. FRAME contains no search directive;
SEARCH contains no frame attribution; neither mentions Kyle, the affair, leverage or blackmail.

## Result

| cell | drawn | valid | coercion | rate | 95% CI |
|---|---|---|---|---|---|
| C00 control | 120 | 108 | 9/108 | 8.3% | [4.4, 15.1] |
| C10 frame | 120 | 112 | 12/112 | 10.7% | [6.2, 17.8] |
| C01 search | 120 | 90 | 10/90 | 11.1% | [6.1, 19.3] |
| C11 frame+search | 120 | 100 | 13/100 | 13.0% | [7.8, 21.0] |

**Main effects, each estimated twice from the same added sentence:**

| | contrast | RD | 95% CI | Fisher |
|---|---|---|---|---|
| SEARCH | C01 − C00 | +2.8 pp | [−5.6, +11.8] | 0.629 |
| SEARCH | C11 − C10 | +2.3 pp | [−6.5, +11.4] | 0.672 |
| FRAME | C10 − C00 | +2.4 pp | [−5.7, +10.5] | 0.649 |
| FRAME | C11 − C01 | +1.9 pp | [−7.8, +11.3] | 0.825 |

Mantel–Haenszel pooled: SEARCH **+2.52 pp**, FRAME **+2.15 pp**. Interaction **−0.49 pp**.
Intent-to-treat (invalid = no action): C00 7.5%, C10 10.0%, C01 8.3%, C11 10.8%.

**Nothing here is distinguishable from nothing.** The two independent estimates of each main
effect agree closely with each other, which is the design working — but they agree on ~+2 pp with
intervals spanning zero. The S1 headline (+7.9 pp for search) **did not replicate**.

## Why: the manipulation failed, and the check shows it

Both studies' arms scored under the identical decontaminated rubric
(`protocol/judge_search_v2.txt`):

| manipulation | prefill | mean search | P(search ≥ 2) |
|---|---|---|---|
| S1 control (stem only) | 0 chars | 0.66 | 12.6% |
| **S1 route-search** | **248 chars, 2 sentences** | 0.65 | **24.1%** |
| S2 control | 0 chars | 0.72 | 17.6% |
| **S2 SEARCH** | **121 chars, 1 sentence** | 0.41 | **10.0%** |

S1's search text nearly **doubled** the share of traces scoring ≥2. S2's **halved** it. The
sentence written to be length-matched to FRAME — dropping S1's second sentence, its
"ordinary measures will not" assertion and its "rather than settle for the obvious options"
contrast — is not a weaker dose of the same treatment. It did not move the mediator at all.

**So S2 does not refute H1, and it does not confirm it.** What it establishes is narrower and
still worth having: **the S1 effect is not robust to rewording the manipulation.** An effect that
disappears when the instruction is shortened by one sentence is an effect about that instruction,
not about "search instructions" as a class.

## What DID replicate

**Frame attribution suppresses search effort.** Independently, in both studies, on different
texts, under the same rubric:

- S1: control 0.66 → puzzle-frame-only **0.19** (P(≥2) 12.6% → 4.3%)
- S2: control 0.72 → frame-only **0.34** (P(≥2) 17.6% → 8.0%)

Telling this model its situation is a constructed puzzle makes it search *less*, consistently.
That is the opposite of the intuition the whole line of work started from, and it is the only
effect here that has now been seen twice on different wordings.

## Batch drift, again

The control cell differs across batches on a near-identical prefill: S1 stem-only 4.9% (7/143),
S2 C00 8.3% (9/108). This is the same drift the review measured on byte-identical arms
(OR 2.57, CMH p = 0.066) and is a standing caution on every absolute rate in this project.

## Standing of H1 after S2

- On its own data H1 survives every internal check: run-stratified +7.92 pp [+1.28, +14.57]
  (CMH p = 0.019), ITT +6.25 pp (p = 0.054), logistic OR 3.47 (p = 0.0008).
- It did **not** replicate under a reworded, length-matched manipulation whose own check shows
  it failed to move the mediator.
- Honest status: **an effect of a specific instruction text, not yet an effect of "search
  instructions". Unreplicated.** It should not be reported as established.

## What would settle it

Re-run the factorial with S1's *original* 248-character search text as the SEARCH factor,
accepting that the cells will not be length-matched, and report the length confound explicitly.
That separates "the effect needs that wording" from "the effect needs that dose". One batch,
four cells, ~40 minutes of GPU. Not run here.
