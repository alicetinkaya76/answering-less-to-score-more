#!/usr/bin/env python3
"""Yedek zincire geçiş: config'i FCTR-küçük hücreye çevirir, split/sonuçları temizler.

Kullanım: python3 00_prepare_data.py --source fctr && python3 switch_to_fctr.py
Sonra:    python3 01_make_splits.py && python3 02_run_baselines.py
"""
import json
import shutil

cfg = json.load(open("config.json", encoding="utf-8"))
cfg["data"].update({
    "path": "data/fctr_tr.tsv",
    "label_map": {"DOGRU": "EVET", "YANLIS": "HAYIR"},
    "dev_size": 100, "test_size": 300,
    "dev_index_file": None, "test_index_file": None,
})
cfg["item_template"] = "{instruction}\n\nİddia: \"{text}\"\nCevap:"
cfg["task_description"] = ("Türkçe iddiaların (sosyal medyada yayılan haber ve iddia "
                           "metinleri) doğru mu yanlış mı olduğunu sınıflandırma; "
                           "EVET = iddia doğru, HAYIR = iddia yanlış")
cfg["manual_prompts_file"] = "prompts_manual_fctr.json"
json.dump(cfg, open("config.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
for p in ("data/splits", "results"):
    shutil.rmtree(p, ignore_errors=True)
print("config → FCTR-küçük hücre (dev 100 / test 300); split ve results temizlendi.")
print("Sıradaki: python3 01_make_splits.py && python3 02_run_baselines.py")
