#!/usr/bin/env python3
"""TERS ABLASYON — istismar evrime özgü mü, yoksa tek satırlık bir düzenleme mi?

İleri ablasyon (08) gösterdi: evrimleşmiş prompta format kısıtını GERİ koyunca
coverage 1.00'a dönüyor. Bu betik tersini yapar: MANUEL promptlardan format kısıtını
SİLER ve aynı bütçede (np=24) değerlendirir.

Öngörü: coverage çöker, F_excl (F1-used) YÜKSELİR — yani "en iyi manuel promptumdan
dört kelime silince metrik onu daha iyi sanıyor". Doğrularsa kanıt zinciri kapanır:
format kısıtı, coverage'ın hem GEREK hem YETER koşuludur; istismar evrimin marifeti
değil, F_excl'in yapısal açığıdır — evrim sadece açığı bulur.

Kontroller (baselines.json'dan, np=24, TEST):
  M1 cov=0.774 F1u=0.7849 | M2 cov=1.000 F1u=0.7930
  M5 cov=1.000 F1u=0.6145 | M8 cov=1.000 F1u=0.7412

Kullanım: python3 09_reverse_ablation.py        (~40 dk)
"""
import json
import os

from fg.cli import base_argparser, bootstrap
from fg.common import ensure_dir, write_json
from fg.evalharness import EvalCache, evaluate_prompt

# Format kısıtı SİLİNMİŞ manuel promptlar (elle, minimal düzenleme; etiket uzayı korunur)
STRIPPED = {
    "M1_KISITSIZ": (
        "Aşağıdaki haber metnini oku. Bu metin Zaytung tarzı satirik (uydurma/mizahi) "
        "bir haberse EVET, gerçek bir haber ajansı haberiyse HAYIR yaz."
    ),
    "M2_KISITSIZ": (
        "Bir haber editörü gibi davran. Verilen metnin satirik/parodi haber mi yoksa "
        "gerçek habercilik mi olduğuna karar ver. EVET (satirik) ya da HAYIR (gerçek)."
    ),
    "M5_KISITSIZ": (
        "Soru: Bu haber satirik mi? Cevabını EVET veya HAYIR olarak ver."
    ),
    "M8_KISITSIZ": (
        "Metnin türüne karar ver. Hiciv, ironi veya kurgu yoluyla güncel olaylarla dalga "
        "geçen satirik bir haberse EVET; sahici bir haber ajansının olay aktarımıysa "
        "HAYIR yaz."
    ),
}

CONTROLS = {"M1": (0.774, 0.7849), "M2": (1.000, 0.7930),
            "M5": (1.000, 0.6145), "M8": (1.000, 0.7412)}


def main():
    ap = base_argparser(__doc__)
    args = ap.parse_args()
    cfg, client, dev, test, manuals = bootstrap(args)

    print("\n--- TERS ABLASYON: manuel promptlardan format kısıtı SİLİNDİ (np=24) ---\n")
    rows = []
    for name, prompt in STRIPPED.items():
        rd = ensure_dir(f"results/reverse_ablation/{name}")
        ensure_dir(os.path.join(rd, "raw"))
        ensure_dir(os.path.join(rd, "preds"))
        res = evaluate_prompt(prompt, test, "test", client, cfg, rd, EvalCache())
        base = CONTROLS[name.split("_")[0]]
        d_cov = (res["coverage_strict"] - base[0]) * 100
        d_f1 = res["f1_used_strict"] - base[1]
        print(f"[{name}] cov={res['coverage_strict']:.3f} ({d_cov:+.1f}pp) "
              f"covL={res['coverage_loose']:.3f} "
              f"F1-used={res['f1_used_strict']:.4f} ({d_f1:+.4f}) "
              f"F1-wrong={res['f1_wrong_strict']:.4f}", flush=True)
        rows.append({"name": name, "prompt": prompt,
                     "cov": res["coverage_strict"], "cov_loose": res["coverage_loose"],
                     "f1_used": res["f1_used_strict"],
                     "f1_wrong": res["f1_wrong_strict"],
                     "orig_cov": base[0], "orig_f1_used": base[1],
                     "d_cov_pp": d_cov, "d_f1_used": d_f1})
    write_json("results/reverse_ablation/summary.json", rows)
    print("\nYorum: Δcov belirgin NEGATİF ve ΔF1-used POZİTİF ise → istismar, "
          "evrime özgü değil; F_excl'in yapısal açığı. Kanıt zinciri kapanır.")


if __name__ == "__main__":
    main()
