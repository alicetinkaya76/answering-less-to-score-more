# Answering Less to Score More: code and data artifact

Replication artifact for:

> Ali Çetinkaya. *Answering Less to Score More: A Measurement-Validity Audit of
> Abstain-Exclude Fitness in Prompt Optimization.* Submitted to **Computational
> Linguistics** (MIT Press / ACL), 2026.

The paper audits a measurement failure rather than proposing an algorithm: when a
prompt optimizer's fitness is a macro-F1 computed **only over parseable predictions**
(`F_excl`), the optimizer can raise the reported score by making hard items unparseable
instead of by classifying them. The remedy is to price unanswered items as errors
(`F_wrong`). The archive supports item-level reconstruction of the reported results: a
separate 105-check verifier re-derives the main tables and the textual statistics it covers,
while the battery, the model screen, and the remaining exploratory quantities are exposed
through their raw predictions, summaries, scripts, and provenance records.

## What is here

| path | contents |
|---|---|
| `code/` | the experiment pipeline as run: `00`–`15` stage scripts, the `fg/` package, unit and smoke tests, `config.json`, the manual prompt sets |
| `results/` | the complete run archive: 12 experiment groups, 146,550 raw model outputs, per-item strict and lenient predictions, per-candidate generation logs, best-of-run selections, per-run config snapshots with model digests |
| `data/` | frozen dev/test split indices, a per-item manifest, and checksums. **The corpus text itself is not redistributed here**; see `DATA.md` |
| `analysis/` | `analysis.py`, a separate 105-check verifier that re-derives the main tables and selected textual statistics from `results/`, plus its recorded and re-run outputs |
| `figures-src/` | `make_figures.py` and the `figure_data.json` it plots, itself produced by `analysis.py` |
| `figures/` | the five paper figures (PNG + PDF) and their captions |
| `PRESPECIFICATION.md` | what was fixed before the runs, where it lives in the config, and how to check it |
| `verify_manifest.py` | generates and verifies `SHA256SUMS.txt`; its docstring is the exact definition of the aggregate digest |

## Quick start

Verifying the paper's numbers takes minutes and needs no GPU, no network, and no
model; the archive already contains every prediction:

```bash
python3 analysis/analysis.py results/ derived/
```

Reproducing the *runs* that produced the archive is a different order of effort
(roughly 86,000 target inferences, ~2–3 nights on an M4 Max with a local Ollama).
`REPRODUCE.md` documents both paths.

## Licensing in one line

Code is MIT (`LICENSE`); the author's derived experimental data in `results/` is CC BY 4.0,
except that no rights are claimed in third-party text incidentally reproduced inside raw model
outputs; the underlying news texts are neither owned nor redistributed here. `DATA.md` gives
the full provenance chain.

## Citation

See `CITATION.cff`.
