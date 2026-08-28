# data/

The corpus text is **not** in this directory, by design — see `../DATA.md` for the
provenance chain and the reasoning. What is here lets you rebuild it and prove the
rebuild is identical.

| file | what it is |
|---|---|
| `splits/dev_indices.txt` | the 175 frozen dev item ids |
| `splits/test_indices.txt` | the 500 frozen test item ids |
| `MANIFEST_satire_tr.tsv` | one row per corpus item: `id`, `label`, `n_chars`, `sha256_text` (4,370 rows) |
| `MANIFEST_satire_probe_debiased.tsv` | the same for the 200-item style-debiased hard-slice probe |
| `CHECKSUMS.txt` | sha256 of the two whole corpus files as this study produced them |

## Rebuilding and verifying

```bash
cd ../code
python3 00_prepare_data.py          # writes data/satire_tr.tsv, data/satire_probe_debiased.tsv
shasum -a 256 data/satire_tr.tsv    # must match CHECKSUMS.txt
```

Item by item, if a whole-file hash mismatches and you want to find out where:

```python
import csv, hashlib
man = {r["id"]: r for r in csv.DictReader(open("MANIFEST_satire_tr.tsv"), delimiter="\t")}
for r in csv.DictReader(open("../code/data/satire_tr.tsv"), delimiter="\t"):
    want = man[r["id"]]["sha256_text"]
    got = hashlib.sha256(r["text"].encode("utf-8")).hexdigest()
    if want != got:
        print("differs:", r["id"])
```

The derivation is deterministic at `SEED = 20260706`, so a divergence means the upstream
source changed, not that the sampling drifted.
