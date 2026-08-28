"""Veri katmanı.

- OffensEval-TR (OLID formatı: id / tweet / subtask_a, OFF|NOT) veya benzer TSV/CSV yüklenir.
- Etiketler config'teki label_map ile EVET/HAYIR uzayına çevrilir.
- Sabit dev/test indeksleri: (a) config'te dosya verildiyse ORADAN okunur (önceki
  makalenin indeksleriyle karşılaştırılabilirlik için); (b) verilmediyse split_seed ile
  DETERMİNİSTİK ve TABAKALI üretilir, data/splits/ altına YAZILIR ve sonraki koşularda
  hep oradan okunur (bir kez üret, sonsuza dek sabit).
"""

import csv
import os
import random

from .common import ensure_dir


def _sniff_delimiter(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        head = f.readline()
    return "\t" if head.count("\t") >= head.count(",") else ","


def load_dataset(dcfg):
    path = dcfg["path"]
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Veri dosyası yok: {path} — OffensEval-TR dosyanı bu yola koy "
            f"(veya config.json > data.path'i güncelle)."
        )
    delim = dcfg.get("delimiter") or _sniff_delimiter(path)
    text_col, label_col = dcfg["text_col"], dcfg["label_col"]
    id_col = dcfg.get("id_col")
    lmap = {k.strip().upper(): v for k, v in dcfg["label_map"].items()}

    items = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        if text_col not in (reader.fieldnames or []):
            raise KeyError(
                f"'{text_col}' kolonu bulunamadı. Dosyadaki kolonlar: {reader.fieldnames}. "
                f"config.json > data.text_col / label_col / id_col alanlarını düzelt."
            )
        for i, row in enumerate(reader):
            raw_label = (row.get(label_col) or "").strip().upper()
            if raw_label not in lmap:
                continue  # etiketi haritalanamayan satır atlanır (ör. boş / NULL)
            iid = str(row.get(id_col)).strip() if id_col else str(i)
            items.append({"id": iid, "text": (row.get(text_col) or "").strip(),
                          "gold": lmap[raw_label]})
    if not items:
        raise ValueError("Hiç örnek yüklenemedi — kolon adlarını ve label_map'i kontrol et.")
    return items


def _read_index_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def _write_index_file(path, ids):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(ids) + "\n")


def _stratified_pick(items, n, rng):
    """Sınıf oranlarını koruyarak n örnek seç; (seçilen, kalan) döndür."""
    by = {}
    for it in items:
        by.setdefault(it["gold"], []).append(it)
    for v in by.values():
        rng.shuffle(v)
    total = len(items)
    picked, rest = [], []
    labels = sorted(by.keys())
    for j, lab in enumerate(labels):
        pool = by[lab]
        if j == len(labels) - 1:
            k = n - len(picked)  # kalan kota son sınıfa
        else:
            k = round(n * len(pool) / total)
        k = max(0, min(k, len(pool)))
        picked.extend(pool[:k])
        rest.extend(pool[k:])
    rng.shuffle(picked)
    rng.shuffle(rest)
    return picked, rest


def make_or_load_splits(items, dcfg, splits_dir="data/splits"):
    """(dev_items, test_items) döndürür. Öncelik: config'teki indeks dosyaları >
    daha önce üretilmiş data/splits dosyaları > yeni deterministik üretim."""
    ensure_dir(splits_dir)
    by_id = {it["id"]: it for it in items}

    dev_f = dcfg.get("dev_index_file") or os.path.join(splits_dir, "dev_indices.txt")
    test_f = dcfg.get("test_index_file") or os.path.join(splits_dir, "test_indices.txt")

    if os.path.exists(dev_f) and os.path.exists(test_f):
        dev_ids, test_ids = _read_index_file(dev_f), _read_index_file(test_f)
        missing = [i for i in dev_ids + test_ids if i not in by_id]
        if missing:
            raise KeyError(
                f"İndeks dosyalarındaki {len(missing)} id veri setinde yok "
                f"(ilk 5: {missing[:5]}). id_col ayarını / indeks dosyalarını kontrol et."
            )
        dev = [by_id[i] for i in dev_ids]
        test = [by_id[i] for i in test_ids]
    else:
        rng = random.Random(dcfg.get("split_seed", 20260706))
        test, rest = _stratified_pick(items, int(dcfg.get("test_size", 500)), rng)
        dev, _ = _stratified_pick(rest, int(dcfg.get("dev_size", 175)), rng)
        _write_index_file(dev_f, [it["id"] for it in dev])
        _write_index_file(test_f, [it["id"] for it in test])

    overlap = {it["id"] for it in dev} & {it["id"] for it in test}
    if overlap:
        raise ValueError(f"dev ve test kesişiyor ({len(overlap)} id) — indeks dosyaları hatalı.")
    return dev, test


def split_stats(name, items):
    from collections import Counter
    c = Counter(it["gold"] for it in items)
    dist = ", ".join(f"{k}={v}" for k, v in sorted(c.items()))
    return f"{name}: n={len(items)} [{dist}]"
