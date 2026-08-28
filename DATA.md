# Data: provenance, licensing, and what is not here

The manuscript promises that this repository "documents the provenance and redistribution
basis for the Zaytung- and Anadolu-Agency-derived texts separately from the software
license". This file is that documentation.

## The chain

1. **Upstream corpus.** SatireTR — the Turkish Satirical News Dataset — pairs satirical
   articles from *Zaytung* with non-satirical agency news from *Anadolu Ajansı*, and adds
   200 style-debiased satirical articles generated with an LLM.
   - Repository: <https://github.com/auotomaton/satireTR>
   - Released by its authors under the **MIT License** (verified 2026-08-27).
   - Cite as: Aslı Umay Öztürk, Recep Fırat Çekinel, and Pınar Karagöz. *Make Satire
     Boring Again: Reducing Stylistic Bias of Satirical Corpus by Utilizing Generative
     LLMs.* Proceedings of the 18th Workshop on Building and Using Comparable Corpora
     (BUCC), 2025, pages 19–35. arXiv:2412.09247.

2. **This study's derived corpus.** `code/00_prepare_data.py` downloads the three upstream
   CSVs and derives `data/satire_tr.tsv` — 4,370 balanced items, each the **headless
   opening of an article body truncated at 200 characters** on a word boundary, with
   duplicates and items under 80 characters dropped, sampled deterministically at
   `SEED = 20260706`. The style-debiased probe becomes
   `data/satire_probe_debiased.tsv` (200 items).

3. **The evaluation splits.** `code/01_make_splits.py` freezes dev (175) and test (500)
   from that corpus. Both index files ship here, in `data/splits/`.

## What is deliberately absent

`data/satire_tr.tsv` and `data/satire_probe_debiased.tsv` are **not** included. The
newspaper texts they derive from are third-party journalism, and this deposit does not
assert any right over them. Instead you get everything needed to rebuild them bit-for-bit
and to prove that you did:

- `data/splits/dev_indices.txt`, `data/splits/test_indices.txt` — the frozen item ids.
- `data/MANIFEST_satire_tr.tsv`, `data/MANIFEST_satire_probe_debiased.tsv` — one row per
  item: `id`, `label`, `n_chars`, `sha256_text`. Rebuild the corpus, hash each item's
  text, and compare item by item.
- `data/CHECKSUMS.txt` — sha256 of the two whole files.

A note on what the MIT license does and does not settle. The upstream repository is released
by its authors under an MIT license, and that license governs the repository's own contents as
they released them. It does not, by itself, establish redistribution rights in the underlying
Zaytung and Anadolu Ajansı journalism from which those contents derive. This deposit therefore
does not redistribute the source text and makes no claim about the rights in it. The manifests
exist so that withholding the text costs a reproducer nothing.

## Verbatim echo in the raw model outputs — disclosed

`results/**/raw/` holds the raw text each target model returned, one file per item. These
are model generations, not corpus files. But the exploit under study works by deleting an
output-format constraint, and an unconstrained model sometimes restates its input before
(or instead of) answering. A full scan of all 146,550 raw output files, comparing each
against its own input item, found:

| verbatim overlap with own input | files | share |
|---|---|---|
| ≥ 40 characters | 1,725 | 1.18% |
| ≥ 80 characters | 249 | 0.17% |
| ≥ 160 characters (effectively the whole 200-character item) | 37 | 0.025% |
| no overlap ≥ 40 characters | 144,825 | 98.82% |

98.8% of raw outputs contain no verbatim span of their input at all. The affected files
are left **unredacted**: they are primary evidence for the paper's central claim about
what the optimized prompts actually elicit, and editing them would destroy the audit trail
that the paper asks readers to trust. The overlap is disclosed here rather than removed.

**Access and takedown.** The raw outputs are distributed openly, without access control, as
part of this deposit. They are archived as evidence of model behaviour, not as a corpus, and
no rights in any echoed source text are claimed. If you hold rights in material an archived
output reproduces, write to ali.cetinkaya@selcuk.edu.tr: affected files will be withdrawn from
the distributed copy and the withdrawal recorded in the deposit's version history, so that what
was removed and when remains auditable even though the file itself is gone.

## Licensing summary

| component | terms |
|---|---|
| `code/`, `analysis/`, `figures-src/`, `verify_manifest.py` | MIT — see `LICENSE`, whose header states this scope |
| `results/`, `data/` manifests and indices, `figures/` | CC BY 4.0 for the author's derived data and figures — except that no rights are claimed in any third-party text incidentally reproduced inside raw model outputs, which remains subject to its original holders' rights and to the access-and-takedown procedure above |
| the underlying Zaytung / Anadolu Ajansı article texts | not redistributed and no rights claimed; the upstream compilation's MIT license covers that repository's contents, not the journalism they derive from |
