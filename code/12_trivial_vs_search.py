#!/usr/bin/env python3
"""TRİVİAL DÜZENLEME vs PAHALI ARAMA — aramanın kendi ölçütünde (dev fitness) kıyas.

Sertleştirilmiş hatta (gevşek parser, np=256) GA 37 değerlendirme harcadı ve
dev-fitness 0.8514 olan bir prompt seçti; test'teki gerçek F1'i 0.8212.
M2'den dört kelime silmek ise test'te 0.8240 veriyor — yani GA'nın bulduğunun aynısı.

Bu betik, kısıtsız manuel promptların DEV fitness'ını aynı protokolde ölçer.
  M2_KISITSIZ dev-fitness ≥ 0.8514 ise → arama, ARAMA UZAYININ TEPESİNDE ZATEN DURAN
  bir noktayı 37 değerlendirmede "keşfetti"; katkısı sıfırdır. Punchline sağlamlaşır.
  Belirgin altındaysa → aramanın gerçek (küçük de olsa) bir katkısı var; öyle raporlanır.

Kullanım: caffeinate -i python3 12_trivial_vs_search.py     (~20-30 dk)
"""
import json
import os

from fg.cli import base_argparser, bootstrap
from fg.common import ensure_dir, write_json
from fg.evalharness import EvalCache, evaluate_prompt

M1_KISITSIZ = ("Aşağıdaki haber metnini oku. Bu metin Zaytung tarzı satirik (uydurma/"
               "mizahi) bir haberse EVET, gerçek bir haber ajansı haberiyse HAYIR yaz.")
M2_KISITSIZ = ("Bir haber editörü gibi davran. Verilen metnin satirik/parodi haber mi "
               "yoksa gerçek habercilik mi olduğuna karar ver. EVET (satirik) ya da "
               "HAYIR (gerçek).")
M8_KISITSIZ = ("Metnin türüne karar ver. Hiciv, ironi veya kurgu yoluyla güncel olaylarla "
               "dalga geçen satirik bir haberse EVET; sahici bir haber ajansının olay "
               "aktarımıysa HAYIR yaz.")

GA_DEV_FITNESS = 0.8514   # sertleştirilmiş GA'nın kazananı (bf4a1731c5ce)
M2_DEV_FITNESS = 0.8108   # baseline M2 (coverage 1.000)


def main():
    ap = base_argparser(__doc__)
    ap.add_argument("--np", type=int, default=256)
    args = ap.parse_args()
    cfg, client, dev, test, manuals = bootstrap(args)

    cfg["decoding"] = dict(cfg["decoding"])
    cfg["decoding"]["num_predict"] = args.np

    print(f"\n--- TRİVİAL vs ARAMA (gevşek fitness, np={args.np}, DEV n={len(dev)}) ---")
    print(f"    GA'nın 37 değerlendirmeyle bulduğu dev-fitness: {GA_DEV_FITNESS:.4f}")
    print(f"    Baseline M2 dev-fitness:                        {M2_DEV_FITNESS:.4f}\n")

    rows = []
    for name, prompt in [("M2_KISITSIZ", M2_KISITSIZ), ("M8_KISITSIZ", M8_KISITSIZ),
                         ("M1_KISITSIZ", M1_KISITSIZ)]:
        rd = ensure_dir(f"results/trivial_vs_search/{name}")
        ensure_dir(os.path.join(rd, "raw"))
        ensure_dir(os.path.join(rd, "preds"))
        res = evaluate_prompt(prompt, dev, "dev", client, cfg, rd, EvalCache())
        fit = res["f1_used_loose"]           # sertleştirilmiş hattın fitness'ı
        d_ga = fit - GA_DEV_FITNESS
        print(f"{name:<14} dev-fitness(gevşek F1)={fit:.4f}  "
              f"covL={res['coverage_loose']:.3f} covS={res['coverage_strict']:.3f}  "
              f"| GA'ya fark: {d_ga:+.4f}", flush=True)
        rows.append({"name": name, "dev_fitness_loose": fit,
                     "cov_loose": res["coverage_loose"],
                     "cov_strict": res["coverage_strict"],
                     "vs_ga": d_ga, "prompt": prompt})

    write_json("results/trivial_vs_search/summary.json", rows)
    best = max(rows, key=lambda r: r["dev_fitness_loose"])
    print(f"\nEn iyi trivial düzenleme: {best['name']} → {best['dev_fitness_loose']:.4f}")
    if best["dev_fitness_loose"] >= GA_DEV_FITNESS - 0.005:
        print("YORUM: Trivial düzenleme, 37 değerlendirmelik aramanın bulduğu noktaya "
              "EŞİT ya da ÜSTÜN. Aramanın katkısı ≈ 0. Punchline sağlam.")
    else:
        print("YORUM: Arama, trivial düzenlemenin ötesinde ölçülebilir bir kazanç buldu; "
              "makalede bu kadarıyla ve dürüstçe raporlanmalı.")


if __name__ == "__main__":
    main()
