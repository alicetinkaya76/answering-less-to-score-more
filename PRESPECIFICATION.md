# Pre-specification: what was fixed before the runs, and how you can check

The paper states that the cell-selection rule and the decision gates were written before any
optimization run. A reviewer cannot take that on trust, so here is the evidence this deposit
carries, and its limits.

## The rule lives in `code/config.json`, not in prose

The thresholds the paper reports as pre-specified are literal fields in the configuration the
pipeline reads:

| field | value | what it fixes |
|---|---|---|
| `manipulation.delta_coverage_pp` | −10.0 | the coverage drop that counts as manipulation |
| `manipulation.loose_gap_pp` | 10.0 | the strict/lenient gap that marks a parser artefact |
| `audition.min_coverage` | 0.85 | admission floor for the cell-selection audition |
| `audition.f1_lo`, `audition.f1_hi` | 0.55, 0.85 | the headroom window (criterion ii) |
| `audition.min_disagreement` | 0.10 | prompt-disagreement floor (criterion iii) |
| `gates.f1wrong_margin_pp` | 2.0 | remedy gate: F_wrong within 2 points of baseline |
| `gates.coverage_margin_pp` | 5.0 | remedy gate: coverage within 5 points of baseline |
| `data.split_seed` | 20260706 | the frozen dev/test split |
| `seeds` | 11, 23, 47 | the three seeds, fixed in advance |

The confirmatory baseline and reporting pipeline reads these fields from `code/config.json`, and
`code/05_report.py` evaluates the gates against them mechanically. Being exact about the limits:
the exploratory scripts `13_fragility_screen.py`, `14_exploit_battery.py` and
`15_ga_target_model.py` **duplicate the −10 percentage-point threshold as a literal** rather than
reading it from the configuration. The value is the same one, and it was fixed before those runs,
but the duplication is disclosed here rather than presented as config-driven execution.

## Timestamps

The archive preserves modification times. `config.json` carries **2026-07-06 21:48**; the first
run output, `results/pilot/baselines/baselines.json`, carries **2026-07-10 06:22**; the
configuration predates the first result by about four days.

Per-run snapshots exist, but not everywhere: `results/` holds **16** `config.json` snapshots, and
they cover the optimization runs (`pilot/baselines`, `pilot/opro_excl`, `pilot/ga_excl`,
`pilot/ga_wrong`, `hardened/ga_excl_hardened`, `target_qwen2.5_7b/ga_excl`), the arms whose
conditions the paper's central claims depend on. The supporting branches (battery, screen, budget,
mechanism, reverse ablation, sensitivity, trivial-vs-search) archive scripts, outputs, and
summaries instead, with the shared thresholds held in the top-level dated configuration.

## What this is not

Filesystem timestamps are evidence, not proof: they can be rewritten, and a tar archive carries
whatever the author's machine recorded. This is not a third-party pre-registration, and the paper
does not claim one; it says the rule was written before the runs, and what is offered here is a
configuration file that encodes that rule, is read by the code, and is dated before the first
result. A reader who wants a stronger guarantee should read the claim as the author's statement,
supported but not proved by the archive.
