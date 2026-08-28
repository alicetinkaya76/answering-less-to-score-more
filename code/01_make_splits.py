#!/usr/bin/env python3
"""Sabit dev/test indekslerini üret (yoksa) veya yükle (varsa) ve dağılımı yazdır.

Önceki makalenin indeksleri varsa: config.json > data.dev_index_file / test_index_file
alanlarına yollarını yaz — bu script onları doğrular (karşılaştırılabilirlik korunur).
"""
from fg.cli import base_argparser
from fg.common import load_config
from fg.data import load_dataset, make_or_load_splits, split_stats


def main():
    ap = base_argparser(__doc__)
    args = ap.parse_args()
    cfg = load_config(args.config)
    items = load_dataset(cfg["data"])
    dev, test = make_or_load_splits(items, cfg["data"])
    print(split_stats("TOPLAM", items))
    print(split_stats("DEV   ", dev))
    print(split_stats("TEST  ", test))
    print("İndeks dosyaları: data/splits/ (veya config'te verilen yollar) — artık SABİT.")


if __name__ == "__main__":
    main()
