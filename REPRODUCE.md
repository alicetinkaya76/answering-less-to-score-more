# Reproducing the paper

There are two paths, and they cost very different amounts. Path A re-derives the main tables
and the textual statistics covered by 105 explicit checks from the archived predictions in
minutes; Table 5 and the seven-model screen have separate reconstruction paths from
`results/battery/` and `results/screen/`. Path B re-runs the experiments that produced the
archived predictions, and takes nights.

---

## Path A: verify the paper's numbers (minutes, no model, no network)

The archive already contains every per-item prediction, so nothing needs to be inferred
again. You need Python 3.10+ and nothing else; the verifier is standard library only.

```bash
python3 analysis/analysis.py results/ derived/
```

This writes `derived/verification.json` and `derived/figure_data.json` and prints one line
per check. Expect:

```
CHECKS: 105 total, 105 PASS, 0 FAIL
```

That is the script's literal last line. Every check passes. If any fails, the archive you are running against is not the one this
deposit shipped; compare `SHA256SUMS.txt` before looking anywhere else.

### A note on the recorded history

`analysis/verification_2026-07-15.json` preserves an earlier run in which four checks failed,
and `analysis/VERIFICATION.md` (in Turkish) is the audit that investigated them. In all four
cases the *check* was stale, not the archive and not the paper:

- **Hard core (2 checks).** §4 of the paper defines the hard core as the test items that all
  eight manual prompts *answer* and all eight answer *wrongly*: 59 items, 58 of them satirical.
  The check body computed the looser "an unanswered item counts as wrong" variant, which gives
  75 and 74. Implementing the paper's stated definition reproduces 59 / 58 exactly. The paper's
  numbers were correct throughout.
- **Honest-improvement counts (2 checks).** Their expected values, 3 and 6, came from an
  archived interim report and were shown unreproducible. The manuscript had already dropped
  them: §6 reports two near-full-coverage candidates beating the baseline, both from OPRO, and
  the "6" under F_wrong counted log lines rather than prompts: one winner logged as elite in
  six successive generations, so the unique count is 1.

Both fixes are annotated inline in `analysis/analysis.py` with the previous value and the
reason. The manuscript's own "Corrections made during analysis" ledger is unaffected: it
records what was corrected during the analysis, and none of those corrections changed.

### Regenerate the figures

```bash
python3 figures-src/make_figures.py derived/figure_data.json derived/figures/
```

Needs matplotlib (3.10.8 used here); the analysis pipeline itself does not. All five
figures reproduce with identical labels, values, and dimensions.

---

## Path B: re-run the experiments (nights, needs a local Ollama)

### Environment

| | |
|---|---|
| Python | ≥ 3.10, standard library only; no pip install required |
| Inference | [Ollama](https://ollama.com) running locally at `http://localhost:11434` |
| Target / optimizer model | `qwen2.5:14b`, digest `7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6` |
| Resistant-target model | `qwen2.5:7b` |
| Fragility screen / battery | seven and four further local models; see the per-run `config.json` snapshots |
| Cost | zero; no API is called at any point |

Each optimization run directory carries a `config.json` snapshot recording the model digests,
decoding parameters, seeds, and the same-model condition flag, so the exact conditions of those
results can be read off the archive rather than inferred from prose. The supporting analyses
keep their scripts, outputs, and summary files instead; shared thresholds and gates live in the
top-level dated configuration. `PRESPECIFICATION.md` gives the exact coverage.

### Rebuild the corpus first

The corpus is not shipped (see `DATA.md`). Rebuild it from the public upstream source:

```bash
cd code
python3 00_prepare_data.py            # downloads SatireTR, derives data/satire_tr.tsv
python3 01_make_splits.py             # freezes dev/test indices
```

Then confirm you rebuilt the identical corpus:

```bash
shasum -a 256 data/satire_tr.tsv      # compare against data/CHECKSUMS.txt
```

For item-level confirmation, hash each item's text and compare against
`data/MANIFEST_satire_tr.tsv`. The derivation is deterministic (`SEED = 20260706`), so a
matching hash means a matching corpus.

### Run the pipeline

```bash
python3 -m unittest tests.test_parser tests.test_smoke   # pipeline check, no Ollama needed
python3 02_run_baselines.py                              # manual baselines M1-M8 + cell selection
python3 03_run_opro.py                                   # OPRO x F_excl
python3 04_run_ga.py --fitness excl                      # GA x F_excl
python3 04_run_ga.py --fitness wrong                     # GA x F_wrong (the remedy)
python3 05_report.py                                     # decision report
python3 06_probe_hard_slice.py --arm ga_excl --seed 11   # hard-slice probe
```

Stages `07`–`15` are the supporting experiments: decoding-budget sensitivity, mechanism
and reverse ablation, the budget test, the trivial-vs-search comparison, the fragility
screen, the exploit battery, and the resistant-target search. Each is an independent
script, so the work can be split across sessions. All runners accept `--mock` for a dry
run without Ollama and `--seeds ...` to override the seed list.

Budget, measured on an M4 Max with 4-bit `qwen2.5:14b`: roughly 86,000 target inferences
for the core arms, about 60–75 hours single-stream, or 2–3 nights with
`OLLAMA_NUM_PARALLEL=4` and `parallel_requests: 4`.

### A caveat on exact reproduction

Decoding is configured deterministically (`temperature 0.0`, fixed seed), but identical
sampling across Ollama versions, quantizations, and hardware is not guaranteed. Path A is
the reproduction path with a guarantee attached; Path B reproduces the *procedure*.

---

## Known documentation drift in the archived code

> **Read this before re-running stage 00.** `code/00_prepare_data.py` and
> `code/README_pipeline.md` both *describe* the item text as "the first ~400 characters of
> the body". The code **truncates at 200** (`TRUNC = 200`), and 200 is what the paper
> reports and what every archived result reflects. The prose is stale; the code is correct.

The archived scripts are left exactly as they were run, so the discrepancy is documented here
rather than edited away. Nothing in the pipeline reads 400 from anywhere; `TRUNC` is a single
module-level constant with no override path, so there is no way to silently reproduce at the
wrong width. To confirm before you spend a night of inference:

```bash
python3 -c "import re; print(re.search(r'^TRUNC = (\d+)', open('code/00_prepare_data.py').read(), re.M).group(1))"
# expects: 200
```

(`code/baselines_trunc400.json` is a leftover from an earlier 400-character exploration and is
not used by any reported result.)
