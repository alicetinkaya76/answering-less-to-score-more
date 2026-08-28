# Reproduction record — 2026-08-27

The recorded verification in `VERIFICATION.md` / `verification.json` was produced in an earlier
sandbox session. This is a separate re-run of the same script against the author's local run
archive, on the author's own machine, as part of preparing the public artifact.

## Environment

| | |
|---|---|
| Host | macOS (Darwin 25.5.0), Apple Silicon |
| Python | 3.11.9, standard library only |
| Archive | `~/Desktop/fg_pilot/results` (650 MB; 12 experiment groups) |
| Script | `analysis/analysis.py`, unchanged except for path parametrization (see below) |

## Command

```bash
python3 analysis/analysis.py ~/Desktop/fg_pilot/results <out-dir>
```

`BASE` and `OUT` were hard-coded to the sandbox paths `/home/claude/fg_pilot/results` and
`/home/claude/derived`, so the script could not run anywhere else. They now come from `argv`
or from `FG_RESULTS` / `FG_OUT`, defaulting to the original values. **No check, tolerance, or
metric definition was altered** — only where the script reads from and writes to.

## Result

```
105 checks   101 pass   4 fail
```

Identical to the recorded run, including the same four failures:

| section | check | expected | got |
|---|---|---|---|
| landscape | honest improvements excl | 3 | 2 |
| landscape | honest improvements wrong | 6 | 1 |
| class | hard core size | 59 | 75 |
| class | hard core satirical | 58 | 74 |

None of the four was a regression: in each case `expected` was an older reading and `got` was
what the archive supports. All four have since been resolved — see the next section.

## Resolution — the verifier now passes 105/105

Diagnosing the four failures showed that in every case the *check* was stale, never the archive
and never the manuscript. Each was corrected in `analysis.py`, with the previous value and the
reason recorded in a comment beside it.

**Hard core (2 checks).** §4 defines the hard core as the test items that all eight manual
prompts *answer* and all eight answer *wrongly*, and says so in those words. The check body
computed the looser "an unanswered item counts as wrong" variant. Implementing the definition
the paper states reproduces the paper's numbers exactly:

| definition | items | satirical |
|---|---|---|
| all eight answer **and** all eight answer wrongly — **what §4 states** | **59** | **58** |
| unanswered counted as wrong — what the check computed | 75 | 74 |

`VERIFICATION.md` finding 3 had already settled this in the paper's favour on 2026-07-15; only
the check body was never updated. **The paper's 59 / 58 was correct all along.**

**Honest-improvement counts (2 checks).** Their `expected` values, 3 and 6, came from the
archived interim report and were shown unreproducible by `VERIFICATION.md` finding 1. The
manuscript had already dropped them: §6 reports "two such candidates existed across all six
runs, both proposed by OPRO", and the "6" under F_wrong turned out to count log lines rather
than prompts — seed 47's single winner logged as elite in six successive generations, so the
unique count is 1. The expected values are now 2 and 1, matching the manuscript and the archive.

Re-running after the corrections:

```
105 checks   105 pass   0 fail
```

The 2026-07-15 output is preserved unchanged as `verification_2026-07-15.json`; `verification.json`
is now the current run. `figure_data.json` is byte-identical to the pre-correction run — none of
these checks feeds the figures.

Nothing in the manuscript's "Corrections made during analysis" ledger changed. The ledger and
`VERIFICATION.md` remain the record of what was corrected and when; the verifier is now an
instrument that agrees with the paper rather than a partial record of the paper's history.

## Numerical agreement

`verification.json` and `figure_data.json` reproduce the recorded outputs field for field, with
three exceptions — the OPRO fitness-landscape bin means:

| field | recorded | re-run | abs. difference |
|---|---|---|---|
| `fig1.opro_bins.hi` | 0.6869075338108728 | 0.686907533810873 | 2.2e-16 |
| `fig1.opro_bins.mid` | 0.7992552499083795 | 0.7992552499083793 | 2.2e-16 |
| `fig1.opro_bins.lo` | 0.880571615094505 | 0.8805716150945049 | 1.1e-16 |

One or two units in the last place of a double — floating-point summation order across platforms.
All three round to the reported three-decimal values (0.687 / 0.799 / 0.881) unchanged. Every
other field, including all headline scores, matched exactly.

## The check count: 70 → 105

The manuscript described the verifier as "an independent verification script (**70 checks**,
including bit-for-bit reproduction of all headline scores)", and referred to it twice more as
"the 70-check verification script" and "its 70-check report". The script runs **105**.
`VERIFICATION.md`'s headline said 70 as well.

70 − 4 = 66 exactly as 105 − 4 = 101, so the count of definitional findings was stable and only
the total drifted: the script grew after the 2026-07-15 audit and the sentence was never updated.
The direction was an *understatement*, not an overclaim — but the archive is now public, and a
reviewer who runs the released script counts 105.

Corrected to **105** in all three places, in both `manuscript/paper_v11.md` and `paper/body.tex`.
This is a change to a number in the manuscript, so to be explicit about the basis: 105 is the
number of `check()` calls the released script makes and the number of entries in the
`verification.json` it writes, verified twice on separate runs. No result, table cell, figure
value, or limitation was touched. To revert, `git revert` the commit that made this change.

### Scope of the claim — narrowed 2026-08-27

§3 also said "**Every number in this paper** was re-derived ... by an **independent** verification
script ... all statistics in the text follow definitions that this script reproduces exactly."
A pre-submission review challenged both the scope and the word "independent", and both challenges
hold:

- **Scope.** The 105 checks carry no `battery` or `screen` section. Table 5 (the escape-vector
  battery) and the seven-model fragility screen are therefore *not* re-derived by the script, so
  "every number" was false. Confirmed by grouping `verification.json` by section: `main` 30,
  `mechanism` 12, `budget` 11, `manual` 8, `reverse` 8, `rescore` 6, `landscape` 6, `central` 5,
  `hardened` 4, `class` 4, `7b` 3, `traj` 3, `early` 2, `anatomy` 2, `fwrong` 1 — no battery, no screen.
- **"Independent."** The script is separate from the analysis pipeline, but it was written and run
  by the author on the author's machine. A reader can fairly read "independent" as third-party
  verification, which has not happened.

The sentence now reads: "The headline results were re-derived from the archived per-item
predictions by a **separate** verification script (105 checks, including bit-for-bit reproduction
of every headline score) ... the statistics it covers follow definitions it reproduces exactly, and
the archive exposes the per-item predictions behind the remainder." "Independent" was likewise
softened to "separate" in the cover letter and in this file.

## Figures

`figures-src/make_figures.py` read `/home/claude/derived/figure_data.json` and wrote to
`/mnt/user-data/outputs/figures`, both hard-coded. It now takes the data file and output
directory from `argv` or `FG_FIGURE_DATA` / `FG_FIG_OUT`, defaulting to the `figure_data.json`
checked in beside it. Plot code is untouched. (This script needs matplotlib — 3.10.8 here; the
analysis pipeline itself remains standard-library only.)

Regenerating all five figures from the archive-derived `figure_data.json` and comparing against
the copies in `paper/figures/`:

| figure | PDF text layer | PNG dimensions | pixel difference |
|---|---|---|---|
| fig1 coverage/fitness landscape | identical | identical | mean 0.0001/255, confined to one band |
| fig2 generation dynamics | identical | identical | none |
| fig3 substance vs artefact | identical | identical | none |
| fig4 battery heatmap | identical | identical | none |
| fig5 honest accounting | identical | identical | none |

Every label and printed value matches. Four of the five are pixel-identical; fig1's band is where
the OPRO bin means are drawn as horizontal rules, so the 1–2 ulp difference in those means shifts
the rules by a fraction of a pixel. No figure value changed.
