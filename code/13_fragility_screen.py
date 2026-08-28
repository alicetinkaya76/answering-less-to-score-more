#!/usr/bin/env python3
"""AŞAMA-2 KIRILGANLIK TARAMASI — açık modele mi özgü, yoksa genel mi?

Pahalı arama koşmadan, hücre başına 2 prompt ile F_excl açığının varlığını ölçer:
  KISITLI   = M2 (çıktı-format kısıtı yerinde)
  KISITSIZ  = M2'den dört kelime silinmiş hali
Kırılgan rejimde (katı parser, np=24, yani literatürün rejimi) ölçüm:
  AÇIK VAR  ⇔  Δcoverage < -10pp  VE  ΔF1-used > 0
     (yani: metrik "daha iyi" derken sistem daha az soru cevaplıyor)

Ek teşhis: kısıtsız promptun F1-wrong'u — gerçek performansın muhafazakâr vekili.
Kaç modelde açık var → "delik genel mi" sorusunun cevabı.

Kullanım:
  caffeinate -i python3 13_fragility_screen.py                      (varsayılan model listesi)
  caffeinate -i python3 13_fragility_screen.py --models qwen2.5:7b phi4
  caffeinate -i python3 13_fragility_screen.py --n 500              (tam test seti)

Not: her model sırayla yüklenir; RAM'e sığmayan model listeye konmamalı (32b ≈ 19 GB).
"""
import json
import os
import random

from fg.cli import base_argparser, bootstrap
from fg.common import ensure_dir, write_json
from fg.evalharness import EvalCache, evaluate_prompt

DEFAULT_MODELS = ["qwen2.5:3b", "qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b",
                  "llama3.1:8b", "llama3.2:3b", "phi4", "gemma3:4b"]

M2_KISITLI = ("Bir haber editörü gibi davran. Verilen metnin satirik/parodi haber mi "
              "yoksa gerçek habercilik mi olduğuna karar ver. Cevabın tek kelime olsun: "
              "EVET (satirik) ya da HAYIR (gerçek).")
M2_KISITSIZ = ("Bir haber editörü gibi davran. Verilen metnin satirik/parodi haber mi "
               "yoksa gerçek habercilik mi olduğuna karar ver. EVET (satirik) ya da "
               "HAYIR (gerçek).")


def subsample(items, n, seed=20260706):
    """Sabit, tabakalı alt-örnek: tüm modellerde AYNI örnekler."""
    if n >= len(items):
        return items
    by = {}
    for it in items:
        by.setdefault(it["gold"], []).append(it)
    rng = random.Random(seed)
    out = []
    labels = sorted(by)
    for i, lab in enumerate(labels):
        pool = sorted(by[lab], key=lambda x: x["id"])
        rng.shuffle(pool)
        k = n - len(out) if i == len(labels) - 1 else round(n * len(by[lab]) / len(items))
        out.extend(pool[:k])
    return out


def main():
    ap = base_argparser(__doc__)
    ap.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    ap.add_argument("--n", type=int, default=300, help="test alt-örnek boyutu")
    args = ap.parse_args()
    cfg, client, dev, test, manuals = bootstrap(args)

    items = subsample(test, args.n)
    cfg["decoding"] = dict(cfg["decoding"])
    cfg["decoding"]["num_predict"] = 24          # KIRILGAN REJİM (literatürün rejimi)
    cfg["fitness_parser"] = "strict"

    print(f"\n--- KIRILGANLIK TARAMASI (katı parser, np=24, n={len(items)}) ---")
    print("AÇIK VAR ⇔ Δcov < -10pp VE ΔF1-used > 0\n")
    hdr = (f"{'model':<16} {'cov(K)':>7} {'F1(K)':>7} | {'cov(KS)':>8} {'F1(KS)':>7} "
           f"{'F1w(KS)':>8} | {'Δcov':>8} {'ΔF1':>8}  AÇIK?")
    print(hdr)
    print("-" * len(hdr))

    rows = []
    for model in args.models:
        cfg["target_model"] = model
        try:
            if not args.mock:
                installed = client.check()
                if model not in installed:
                    print(f"{model:<16} ATLANDI (kurulu değil)")
                    continue
            res = {}
            for tag, prompt in (("K", M2_KISITLI), ("KS", M2_KISITSIZ)):
                rd = ensure_dir(f"results/screen/{model.replace(':','_')}/{tag}")
                ensure_dir(os.path.join(rd, "raw"))
                ensure_dir(os.path.join(rd, "preds"))
                res[tag] = evaluate_prompt(prompt, items, "test", client, cfg, rd,
                                           EvalCache())
        except Exception as e:
            print(f"{model:<16} HATA: {e}")
            continue

        k, ks = res["K"], res["KS"]
        d_cov = (ks["coverage_strict"] - k["coverage_strict"]) * 100
        d_f1 = ks["f1_used_strict"] - k["f1_used_strict"]
        hole = (d_cov < -10.0) and (d_f1 > 0)
        print(f"{model:<16} {k['coverage_strict']:>7.3f} {k['f1_used_strict']:>7.4f} | "
              f"{ks['coverage_strict']:>8.3f} {ks['f1_used_strict']:>7.4f} "
              f"{ks['f1_wrong_strict']:>8.4f} | {d_cov:>+7.1f}pp {d_f1:>+8.4f}  "
              f"{'EVET' if hole else 'hayır'}", flush=True)
        rows.append({"model": model, "n": len(items),
                     "cov_constrained": k["coverage_strict"],
                     "f1_constrained": k["f1_used_strict"],
                     "cov_stripped": ks["coverage_strict"],
                     "f1_stripped": ks["f1_used_strict"],
                     "f1wrong_stripped": ks["f1_wrong_strict"],
                     "d_cov_pp": d_cov, "d_f1": d_f1, "hole": hole})

    write_json("results/screen/summary.json", rows)
    if rows:
        n_hole = sum(1 for r in rows if r["hole"])
        print(f"\nSONUÇ: {n_hole}/{len(rows)} modelde F_excl açığı VAR.")
        print("Not: baseline F1(K) düşük olan hücreler (model görevi zaten beceremiyor) "
              "yorumda ayrı işaretlenmeli — orada 'açık yok' bulgusu bilgi taşımaz.")


if __name__ == "__main__":
    main()
