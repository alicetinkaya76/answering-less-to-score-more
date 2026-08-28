# Figure captions (Draft v1 — English, PeerJ style)

All figures are generated directly from the archived per-candidate generation logs and per-item
predictions (`make_figures.py` + `analysis.py`); every plotted value was re-derived from the raw
archive and cross-checked against the numbers in the paper.

---

**Figure 4. The abstain-exclude fitness landscape rewards silence.**
Each point is one unique candidate prompt evaluated on the development set (n = 175) during
search, pooled over three seeds per optimizer (OPRO: 152 unique candidates; EvoPrompt-style GA:
98). x-axis: coverage under the strict parser; y-axis: the fitness the optimizer actually saw,
F_excl (macro-F1 over parsed items only). The black star is the hand-written baseline M2
(coverage 1.000, dev F_excl 0.811; dashed line). Horizontal segments give the mean OPRO fitness
per coverage bin (≥ 0.8: 0.687; 0.5–0.8: 0.799; < 0.5: 0.881): mean fitness rises monotonically
as coverage falls. The best full-coverage candidate the search ever saw improved on the baseline
by +0.008; the low-coverage region offered up to +0.12.

**Figure 1. What the fitness function permits, the population does.**
Coverage (strict parser, dev) of each generation's best prompt, three seeds per regime
(generation 0 = initial population, which contains the eight manual prompts). Under F_excl on the
strict pipeline (vermilion), coverage collapses — as early as generation 1 (seed 11:
1.00 → 0.41) and by generation 4 in every seed. Under F_wrong (green), which prices unanswered
items as errors, all three seeds hold coverage at exactly 1.000 for all five generations. Under
the hardened pipeline (pink; fitness = lenient parser at a 256-token budget), coverage dips are
proposed by the operators but no longer rewarded, and the population recovers.

**Figure 3. Search buys artefact, not substance.**
Reported gain over the M2 baseline (test, n = 500) decomposed into substance (solid: real gain
under the most generous accounting available — lenient parser, 256-token budget) and artefact
(hatched: reported − real). Left two bars: deleting the four-word format constraint from
hand-written prompts (zero search). Right two bars: the most-searched winners (38 and 57 dev
evaluations). As search increases, artefact grows (+0.050 → +0.176) while substance shrinks and
turns negative (+0.031 → −0.061): both champions are genuinely worse than the baseline they
started from.

**Figure 5. The escape channel is universal; the exploitable regime is not.**
Escape-vector battery on four competent models (test subsample n = 300, strict parser, 24-token
budget). Cell shading: coverage drop relative to each model's control prompt (V0 = M2, constraint
intact); annotations give absolute coverage and ΔF_excl vs. control. V3 (reasoning-inducing)
empties coverage on every model — the channel is open everywhere. V2 (explicit "abstain if
unsure") fails to move coverage on any model. Boxed cells mark the exploitable regime — partial
coverage combined with an F_excl gain — which occurs only on qwen2.5:14b (V1: constraint deleted;
V4/V5: evolved winners transferred). The same evolved prompts produce full coverage and an honest
+0.13 gain on llama3.1:8b: the fragility lives in the model × metric interaction, not in the
prompt string.

**Figure 2. Honest accounting of the six manipulated winners.**
For each winning prompt (test, n = 500): reported score (F_excl, strict parser, 24-token budget;
dark), the same prompt forced to answer via constraint restoration (blue), and the honest score
F_wrong under the original pipeline (green). Dashed line: M2 baseline (0.793 at coverage 1.000);
x labels give each winner's coverage. Yellow diamonds mark the deployment-generous "real" score
(lenient parser, 256-token budget), measured for the two most-searched winners (0.755, 0.732) —
both below baseline. F_wrong tracks the forced-answer counterfactual with a mean absolute gap of
0.077, erring conservative in four of six runs. *(Note: the original figure spec asked for the
lenient@256 score on all six winners; that measurement exists only for the two winners included
in the budget experiment — producing it for the remaining four would require new model inference.
F_wrong, available for all six, is shown as the honest accounting instead.)*
