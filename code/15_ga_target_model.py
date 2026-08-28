#!/usr/bin/env python3
"""HEDEF-MODEL GENELLEMESİ — arama, elle bulunamayan tatlı noktayı bulur mu?

Batarya (14) gösterdi:
  - Kaçış KANALI her modelde açık (V3 → coverage 0.00–0.11).
  - Ama elle atılan vektörler 7b/32b'de ya HİÇ susturmuyor (V1: cov 1.000)
    ya da HERKESİ susturuyor (V3: cov ~0.00, F1 → 0). İkisi de istismar değil.
  - İstismar TATLI NOKTA gerektirir: kısmi + zorlukla-korele susma.

Optimize edicinin işi tam olarak bu ara noktayı aramaktır. Bu betik, F_excl'i
kırılgan rejimde (katı parser, np=24 — literatürün rejimi) yeni bir HEDEF modele
karşı koşar. Optimize edici (prompt yazan) model ayrı tutulabilir: gerçekçi senaryo
"güçlü modelle optimize et, ucuz modele konuşlandır"dır.

  MANİPÜLASYON ⇔ best-of-run TEST: F1-used ↑ (baseline'a göre) VE Δcoverage < -10pp

Sonuç ne olursa olsun bilgi verir:
  BULURSA  → kırılganlık genel; elle atılan probe'lar yetersizmiş. En güçlü iddia.
  BULAMAZSA → kırılganlık modelin erişilebilir kaçış moduna bağlı; F_wrong lehine
             daha keskin argüman ("hangi modelin sömürülebilir olduğunu bilemezsin").

Kullanım:
  caffeinate -i python3 15_ga_target_model.py --target qwen2.5:7b --seeds 11
  caffeinate -i python3 15_ga_target_model.py --target qwen2.5:7b --seeds 11 23 47
"""
import json
import os

from fg.cli import base_argparser, bootstrap, snapshot_config
from fg.common import ensure_dir, write_json
from fg.evalharness import EvalCache, evaluate_prompt
from fg.ga import run_ga


def main():
    ap = base_argparser(__doc__)
    ap.add_argument("--target", required=True, help="hedef (sınıflandıran) model")
    ap.add_argument("--optimizer", default="qwen2.5:14b",
                    help="prompt yazan model (varsayılan 14b: güçlü optimize edici)")
    args = ap.parse_args()
    cfg, client, dev, test, manuals = bootstrap(args)

    cfg["target_model"] = args.target
    cfg["optimizer_model"] = args.optimizer
    cfg["decoding"] = dict(cfg["decoding"])
    cfg["decoding"]["num_predict"] = 24        # kırılgan rejim
    cfg["fitness_parser"] = "strict"
    slug = args.target.replace(":", "_")
    cfg["results_dir"] = f"results/target_{slug}"

    print(f"\n--- HEDEF-MODEL GENELLEMESİ ---")
    print(f"    hedef={args.target} | optimize edici={args.optimizer} | "
          f"katı parser, np=24\n")

    # bu hedef modelin KENDİ baseline'ı (M2) — tüm Δ'lar buna göre
    bdir = ensure_dir(os.path.join(cfg["results_dir"], "baseline"))
    ensure_dir(os.path.join(bdir, "raw"))
    ensure_dir(os.path.join(bdir, "preds"))
    m2 = manuals[1]  # M2 = sıralı anahtarların ikincisi
    cache = EvalCache()
    b_dev = evaluate_prompt(m2, dev, "dev", client, cfg, bdir, cache)
    b_test = evaluate_prompt(m2, test, "test", client, cfg, bdir, cache)
    print(f"[baseline M2 @ {args.target}] dev F1={b_dev['f1_used_strict']:.4f} "
          f"cov={b_dev['coverage_strict']:.3f} | TEST F1={b_test['f1_used_strict']:.4f} "
          f"cov={b_test['coverage_strict']:.3f} F1-wrong={b_test['f1_wrong_strict']:.4f}\n")
    write_json(os.path.join(bdir, "baseline.json"), {"dev": b_dev, "test": b_test})

    seeds = args.seeds if args.seeds else [11]
    results = []
    for seed in seeds:
        arm = "ga_excl"
        rd = ensure_dir(os.path.join(cfg["results_dir"], arm, f"seed{seed}"))
        ensure_dir(os.path.join(rd, "raw"))
        ensure_dir(os.path.join(rd, "preds"))
        snapshot_config(cfg, client, rd, {"arm": arm, "seed": seed,
                                          "target": args.target,
                                          "optimizer": args.optimizer})
        s = run_ga(cfg, client, dev, test, manuals, "excl", seed, rd)
        t = s["test"]
        d_f1 = t["f1_used_strict"] - b_test["f1_used_strict"]
        d_cov = (t["coverage_strict"] - b_test["coverage_strict"]) * 100
        manip = (d_f1 > 0.005) and (d_cov < -10.0)
        print(f"\n[{args.target} GA×F_excl seed{seed}]")
        print(f"  TEST F1-used={t['f1_used_strict']:.4f} ({d_f1:+.4f})  "
              f"cov={t['coverage_strict']:.3f} ({d_cov:+.1f}pp)  "
              f"covL={t['coverage_loose']:.3f}  F1-wrong={t['f1_wrong_strict']:.4f}")
        print(f"  → {'MANİPÜLASYON BULDU' if manip else 'manipülasyon YOK'}")
        print(f"  Kazanan prompt: {s['best_prompt'].strip()[:220]}")
        results.append({"seed": seed, "manipulation": manip, "d_f1": d_f1,
                        "d_cov_pp": d_cov, "test": t, "prompt": s["best_prompt"]})

    n = sum(1 for r in results if r["manipulation"])
    print(f"\nSONUÇ ({args.target}): {n}/{len(results)} seed'de manipülasyon.")
    if n:
        print("→ Kırılganlık GENEL: elle atılan probe'lar yetersizdi, ARAMA tatlı noktayı buldu.")
    else:
        print("→ Bu hedefte arama istismar bulamadı: kırılganlık, modelin erişilebilir "
              "kaçış moduna bağlı. F_wrong argümanı keskinleşir.")
    write_json(os.path.join(cfg["results_dir"], "summary.json"),
               {"target": args.target, "optimizer": args.optimizer,
                "baseline_test": b_test, "runs": results})


if __name__ == "__main__":
    main()
