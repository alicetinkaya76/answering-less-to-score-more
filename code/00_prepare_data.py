#!/usr/bin/env python3
"""Veri hazırlama — birincil: SatireTR (Zaytung vs AA), yedek: FCTR (ikili).

Kullanım:
  python3 00_prepare_data.py                      # satire: indir + dönüştür (varsayılan)
  python3 00_prepare_data.py --local-dir YOL      # indirmeden, yerel repo kopyasından
  python3 00_prepare_data.py --source fctr        # yedek: FCTR ikili (küçültülmüş hücre)

Çıktılar:
  data/satire_tr.tsv               (id, text, label∈{SATIRIK,GERCEK}; dengeli 2×2202'ye kadar)
  data/satire_probe_debiased.tsv   (200 stil-arındırılmış satirik — ZOR-DİLİM PROBU)
  data/fctr_tr.tsv                 (--source fctr: id, text, label∈{DOGRU,YANLIS}; dengeli)

Tasarım kararları (README'de gerekçeli):
- Metin = gövdenin ilk ~400 karakteri (kelime sınırında), BAŞLIKSIZ: Zaytung başlıkları
  en güçlü stil sızıntısıdır; gövde-odaklı kırpma görevi içerik-yargısına yaklaştırır.
- Dengeli örnekleme (split_seed ile deterministik): sınıf önseli örnekleme artefaktıdır.
"""

import argparse
import csv
import io
import os
import random
import sys
import urllib.request

csv.field_size_limit(10 ** 8)

RAW = "https://raw.githubusercontent.com/auotomaton/satireTR/main"
SAT_URL = f"{RAW}/TurkishSatiricalNewsDataset/satirical-zaytung.csv"
AA_URL = f"{RAW}/TurkishSatiricalNewsDataset/nonsatirical-aa.csv"
DEB_URL = f"{RAW}/DebiasingPipeline/satirical_initial_and_generated_200.csv"
FCTR_URL = "https://raw.githubusercontent.com/firatcekinel/FCTR/main/data/fctr.csv"

TRUNC = 200
MIN_LEN = 80
SEED = 20260706


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fg-pilot/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", errors="replace")


def _read_csv_text(text, delimiter=","):
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


def _load(path_or_url, local_dir, rel, delimiter=","):
    if local_dir:
        with open(os.path.join(local_dir, rel), encoding="utf-8", errors="replace") as f:
            return list(csv.DictReader(f, delimiter=delimiter))
    print(f"indiriliyor: {path_or_url}")
    return _read_csv_text(_fetch(path_or_url), delimiter=delimiter)


def _clean(text):
    return " ".join((text or "").split())


def _truncate(text, n=TRUNC):
    t = _clean(text)
    if len(t) <= n:
        return t
    cut = t[: n + 1]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > n * 0.6 else cut[:n]).rstrip() + "…"


def _write_tsv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["id", "text", "label"])
        for r in rows:
            w.writerow(r)
    print(f"yazıldı: {path}  ({len(rows)} satır)")


def prepare_satire(local_dir):
    sat = _load(SAT_URL, local_dir, "TurkishSatiricalNewsDataset/satirical-zaytung.csv")
    aa = _load(AA_URL, local_dir, "TurkishSatiricalNewsDataset/nonsatirical-aa.csv")
    deb = _load(DEB_URL, local_dir,
                "DebiasingPipeline/satirical_initial_and_generated_200.csv")

    rng = random.Random(SEED)
    seen = set()

    def uniq(t):
        k = t[:120]
        if k in seen or len(t) < MIN_LEN:
            return False
        seen.add(k)
        return True

    pos = []
    for i, r in enumerate(sat):
        t = _truncate(r.get("content"))
        if uniq(t):
            pos.append((f"s{i:04d}", t, "SATIRIK"))
    neg_pool = []
    for i, r in enumerate(aa):
        t = _truncate(r.get("body"))
        if uniq(t):
            neg_pool.append((f"a{i:04d}", t, "GERCEK"))
    rng.shuffle(neg_pool)
    neg = neg_pool[: len(pos)]

    rows = pos + neg
    rng.shuffle(rows)
    _write_tsv("data/satire_tr.tsv", rows)
    print(f"  sınıf dengesi: SATIRIK={len(pos)}, GERCEK={len(neg)} "
          f"(AA havuzu {len(neg_pool)}; eşitlenerek örneklendi, seed={SEED})")

    probe = []
    for i, r in enumerate(deb):
        t = _truncate(r.get("generated_content"))
        if len(t) >= MIN_LEN:
            probe.append((f"d{i:03d}", t, "SATIRIK"))
    _write_tsv("data/satire_probe_debiased.tsv", probe)
    print("  probe: stil-arındırılmış 200 satirik — best-of-run promptla ayrıca "
          "değerlendirilecek ZOR DİLİM (manipülasyon buraya yığılmalı).")


def prepare_fctr(local_dir):
    rows_in = (_load(FCTR_URL, None, None, delimiter="\t") if not local_dir else
               _load(None, local_dir, "fctr.csv", delimiter="\t"))
    pos, neg = [], []
    for i, r in enumerate(rows_in):
        lab = (r.get("label") or "").strip().lower()
        t = _truncate(r.get("claim"))
        if len(t) < 20:
            continue
        if lab in ("doğru", "çoğunlukla doğru"):
            pos.append((f"f{i:04d}", t, "DOGRU"))
        elif lab in ("yanlış", "çoğunlukla yanlış"):
            neg.append((f"f{i:04d}", t, "YANLIS"))
    rng = random.Random(SEED)
    rng.shuffle(neg)
    neg = neg[: len(pos)]
    rows = pos + neg
    rng.shuffle(rows)
    _write_tsv("data/fctr_tr.tsv", rows)
    print(f"  sınıf dengesi: DOGRU={len(pos)}, YANLIS={len(neg)} — KÜÇÜK hücre: "
          f"config'te dev_size=100, test_size=300 kullan (README'deki yedek planı).")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default="satire", choices=["satire", "fctr"])
    ap.add_argument("--local-dir", default=None,
                    help="İndirme yerine yerel repo kopyasının kökü")
    args = ap.parse_args()
    if args.source == "satire":
        prepare_satire(args.local_dir)
    else:
        prepare_fctr(args.local_dir)


if __name__ == "__main__":
    sys.exit(main())
