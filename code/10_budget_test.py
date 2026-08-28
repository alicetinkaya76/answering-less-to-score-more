#!/usr/bin/env python3
"""BÜTÇE TESTİ — "num_predict=24 fazla dardı" itirazını kapatır.

Aynı promptlar, 10× cömert bütçe (np=256). "EVET" tek token; 256 token, herhangi bir
makul ön-açıklamadan sonra bile etiketi yazmaya fazlasıyla yeter.

Koşulan promptlar (az ve öz — pahalı koşu):
  M2_HAM        : kontrol (kısıt yerinde) — beklenti: coverage ~1.000
  M2_KISITSIZ   : minimal düzenleme (dört kelime silinmiş) — asıl bilimsel nesne
  M8_KISITSIZ   : minimal düzenleme, ikinci tekrar
  opro_excl/47  : evrimleşmiş, en uç koşu (np=24'te cov=0.266)
  ga_excl/11    : evrimleşmiş, en yüksek F1-used (0.9242 @ cov=0.424)

YORUM:
  coverage ~1.00'a dönerse → fenomen "kısıt silme + SONLU bütçe" bileşimidir. Hâlâ
    gerçek bir Goodhart başarısızlığıdır (her konuşlandırmada bütçe sonludur) ama
    makalede num_predict KONTROLLÜ FAKTÖR olarak öne çıkarılmalıdır.
  coverage düşük kalırsa → model cömert bütçede bile karar vermiyordur; itiraz düşer
    ve bulgu sertleşir.

np=24 referansları (TEST):
  M2_HAM cov=1.000 F1u=0.7930 | M2_KISITSIZ cov=0.710 F1u=0.8736
  M8_KISITSIZ cov=0.734 F1u=0.8698 | opro47 cov=0.266 F1u=0.9079 | ga11 cov=0.424 F1u=0.9242

Kullanım: caffeinate -i python3 10_budget_test.py            (np=256, ~1.5-2.5 saat)
          caffeinate -i python3 10_budget_test.py --np 512   (daha da cömert)
"""
import json
import os

from fg.cli import base_argparser, bootstrap
from fg.common import ensure_dir, write_json
from fg.evalharness import EvalCache, evaluate_prompt

M2_KISITSIZ = ("Bir haber editörü gibi davran. Verilen metnin satirik/parodi haber mi "
               "yoksa gerçek habercilik mi olduğuna karar ver. EVET (satirik) ya da "
               "HAYIR (gerçek).")
M8_KISITSIZ = ("Metnin türüne karar ver. Hiciv, ironi veya kurgu yoluyla güncel olaylarla "
               "dalga geçen satirik bir haberse EVET; sahici bir haber ajansının olay "
               "aktarımıysa HAYIR yaz.")

REF24 = {"M2_HAM": (1.000, 0.7930), "M2_KISITSIZ": (0.710, 0.8736),
         "M8_KISITSIZ": (0.734, 0.8698), "opro_excl_seed47": (0.266, 0.9079),
         "ga_excl_seed11": (0.424, 0.9242)}


def main():
    ap = base_argparser(__doc__)
    ap.add_argument("--np", type=int, default=256, help="num_predict (varsayılan 256)")
    args = ap.parse_args()
    cfg, client, dev, test, manuals = bootstrap(args)

    with open("results/pilot/baselines/baselines.json", encoding="utf-8") as f:
        m2 = json.load(f)["baseline"]["prompt"].strip()
    prompts = [("M2_HAM", m2), ("M2_KISITSIZ", M2_KISITSIZ), ("M8_KISITSIZ", M8_KISITSIZ)]
    for arm, seed in [("opro_excl", 47), ("ga_excl", 11)]:
        with open(f"results/pilot/{arm}/seed{seed}/best_of_run.json", encoding="utf-8") as f:
            prompts.append((f"{arm}_seed{seed}", json.load(f)["best_prompt"].strip()))

    cfg["decoding"] = dict(cfg["decoding"])
    cfg["decoding"]["num_predict"] = args.np

    print(f"\n--- BÜTÇE TESTİ: num_predict={args.np} ---")
    print(f"{'prompt':<20} {'cov':>6} {'cov@24':>7} {'Δcov':>8} {'F1-used':>8} {'F1-wrong':>9}\n")
    rows = []
    for name, prompt in prompts:
        rd = ensure_dir(f"results/budget_np{args.np}/{name}")
        ensure_dir(os.path.join(rd, "raw"))
        ensure_dir(os.path.join(rd, "preds"))
        res = evaluate_prompt(prompt, test, "test", client, cfg, rd, EvalCache())
        r24 = REF24.get(name, (float("nan"), float("nan")))
        print(f"{name:<20} {res['coverage_strict']:>6.3f} {r24[0]:>7.3f} "
              f"{(res['coverage_strict']-r24[0])*100:>+7.1f}pp "
              f"{res['f1_used_strict']:>8.4f} {res['f1_wrong_strict']:>9.4f}", flush=True)
        rows.append({"name": name, "num_predict": args.np,
                     "cov": res["coverage_strict"], "cov_loose": res["coverage_loose"],
                     "f1_used": res["f1_used_strict"],
                     "f1_wrong": res["f1_wrong_strict"],
                     "cov_np24": r24[0], "f1_used_np24": r24[1], "prompt": prompt})
    write_json(f"results/budget_np{args.np}/summary.json", rows)
    print("\nKontrol (M2_HAM) coverage ~1.000 kalmalı. Kısıtsız/evrimleşmiş promptlarda "
          "coverage hâlâ düşükse → bütçe itirazı düşer.")


if __name__ == "__main__":
    main()
