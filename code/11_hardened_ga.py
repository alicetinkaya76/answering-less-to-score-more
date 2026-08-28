#!/usr/bin/env python3
"""SERTLEŞTİRİLMİŞ HAT TESTİ (whack-a-mole) — hattı düzeltmek deliği kapatır mı?

Bulgumuz: cömert bütçe (np=256) + toleranslı (gevşek) parser rejiminde coverage ~0.99'a
çıkıyor; dışlanacak pay kalmadığı için F_excl ≈ F_wrong olur. Yani MÜKEMMEL bir ölçüm
hattı, F_excl'in açığını kapatır.

Soru: hat sertleştirildiğinde optimize edici (a) dürüst iyileştirmeye mi yönelir,
yoksa (b) YENİ bir kaçış kanalı mı bulur (ör. hiçbir etiket içermeyen çıktı, açık ret,
tek-sınıf dejenerasyonu)?

  (a) ise → hat-sertleştirme yeterli bir çaredir (F_wrong'a ek/alternatif).
  (b) ise → whack-a-mole doğrulanır: kanalları tek tek kapatmak beyhude; TEK dayanıklı
      çare TEŞVİĞİ kaldırmaktır, yani F_wrong. Makalenin tezi tamamlanır.

Bu koşu: GA × F_excl, fitness GEVŞEK parser'dan, num_predict=256, 1 seed (pilot-of-pilot).
Kıyas: aynı GA katı/np=24 rejiminde seed11'de cov=0.424, F1-used=0.9242 üretmişti;
gerçek (dürüst) performansı ise 0.7550 (baseline 0.7930'un ALTINDA).

Bakılacaklar (koşu bitince otomatik yazdırılır):
  - best-of-run'ın TEST coverage'ı (katı ve gevşek) ve gerçek F1'i
  - dürüst mü (gevşek F1 > 0.7930, cov ~0.99) yoksa yeni kanal mı (cov düşük)

Kullanım:
  caffeinate -i python3 11_hardened_ga.py --seeds 11        (~3-5 saat)
"""
import json
import os

from fg.cli import base_argparser, bootstrap, snapshot_config
from fg.common import run_dir_for
from fg.ga import run_ga

BASE_HONEST = 0.7930  # M2, coverage 1.000, her bütçede sabit


def main():
    ap = base_argparser(__doc__)
    ap.add_argument("--np", type=int, default=256)
    ap.add_argument("--gens", type=int, default=None)
    args = ap.parse_args()
    cfg, client, dev, test, manuals = bootstrap(args)

    # SERTLEŞTİRİLMİŞ HAT
    cfg["decoding"] = dict(cfg["decoding"])
    cfg["decoding"]["num_predict"] = args.np
    cfg["fitness_parser"] = "loose"
    cfg["results_dir"] = "results/hardened"
    if args.gens:
        cfg["ga"]["gens"] = args.gens

    seeds = args.seeds if args.seeds else [11]
    print(f"\n--- SERTLEŞTİRİLMİŞ HAT: fitness=GEVŞEK parser, num_predict={args.np} ---")
    print(f"    (dürüst baseline: F1={BASE_HONEST:.4f} @ coverage 1.000)\n")

    for seed in seeds:
        arm = "ga_excl_hardened"
        rd = run_dir_for(cfg, arm, seed)
        snapshot_config(cfg, client, rd, {"arm": arm, "seed": seed,
                                          "fitness_parser": "loose",
                                          "num_predict": args.np})
        s = run_ga(cfg, client, dev, test, manuals, "excl", seed, rd)
        t = s["test"]
        cov_s, cov_l = t["coverage_strict"], t["coverage_loose"]
        f1_l = t["f1_used_loose"]
        print(f"\n[{arm} seed{seed}] best-of-run:")
        print(f"  TEST coverage: katı={cov_s:.3f}  gevşek={cov_l:.3f}")
        print(f"  TEST F1-used (gevşek = GERÇEK performans): {f1_l:.4f} "
              f"({f1_l - BASE_HONEST:+.4f} baseline'a göre)")
        print(f"  TEST F1-wrong: {t['f1_wrong_strict']:.4f}")
        if cov_l >= 0.95 and f1_l > BASE_HONEST:
            verdict = ("(a) DÜRÜST İYİLEŞTİRME — hat-sertleştirme deliği kapatmış "
                       "görünüyor; optimize edici gerçek kazanç bulmuş.")
        elif cov_l < 0.95:
            verdict = ("(b) YENİ KAÇIŞ KANALI — gevşek parser bile kurtaramıyor; "
                       "whack-a-mole doğrulandı, tek çare F_wrong.")
        else:
            verdict = ("(c) NÖTR — hat sertleştirilince kazanç kayboldu; F_excl'in "
                       "raporladığı iyileştirmeler ölçüm kırılganlığından ibaretti.")
        print(f"  → {verdict}")
        print(f"\n  Kazanan prompt:\n  {s['best_prompt'].strip()[:400]}")


if __name__ == "__main__":
    main()
