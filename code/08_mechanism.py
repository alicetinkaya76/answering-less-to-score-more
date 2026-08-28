#!/usr/bin/env python3
"""MEKANİZMA TESTİ — iki deney, tek betik.

(A) NEDENSEL ABLASYON  [--mode ablation]
    Manipüle best-of-run promptlarının SONUNA silinmiş format kısıtını geri koy,
    aynı bütçede (np=24) yeniden değerlendir.
    Öngörü: coverage ~1.00'a döner, F1-used ~baseline'a çöker.
    Doğrularsa: istismarın nedeni KISITIN SİLİNMESİDİR (semantik değil) — nedensel kanıt.

(B) BÜTÇE DOYGUNLUĞU  [--mode saturation]
    Aynı promptları DOKUNMADAN, cömert bütçeyle (np=128) değerlendir. Kontrol olarak
    baseline M2 de koşulur.
    Öngörü: coverage kısmen toparlanır ama 1.00'ın çok altında kalır.
    Doğrularsa: "bütçen dardı" itirazı düşer — model gerçekten karar vermiyor.

Kullanım:
  python3 08_mechanism.py --mode ablation      (~1 saat)
  python3 08_mechanism.py --mode saturation    (~2-4 saat; uzun çıktı üretir)
  python3 08_mechanism.py --mode both
"""
import json
import os

from fg.cli import base_argparser, bootstrap
from fg.common import ensure_dir, write_json
from fg.evalharness import EvalCache, evaluate_prompt

RUNS = [("opro_excl", 11), ("opro_excl", 23), ("opro_excl", 47),
        ("ga_excl", 11), ("ga_excl", 23), ("ga_excl", 47)]

CONSTRAINT = " Yalnızca EVET veya HAYIR yaz, başka hiçbir şey yazma."
BASELINE_SHA = "8182b54e3e74"


def load_prompt(arm, seed):
    p = f"results/pilot/{arm}/seed{seed}/best_of_run.json"
    with open(p, encoding="utf-8") as f:
        return json.load(f)["best_prompt"].strip()


def load_baseline_prompt():
    with open("results/pilot/baselines/baselines.json", encoding="utf-8") as f:
        return json.load(f)["baseline"]["prompt"].strip()


def run_condition(cfg, client, test, tag, items_prompt, num_predict):
    cfg = json.loads(json.dumps(cfg))  # derin kopya
    cfg["decoding"] = dict(cfg["decoding"])
    cfg["decoding"]["num_predict"] = num_predict
    rows = []
    for name, prompt in items_prompt:
        rd = ensure_dir(f"results/mechanism/{tag}/{name}")
        ensure_dir(os.path.join(rd, "raw"))
        ensure_dir(os.path.join(rd, "preds"))
        res = evaluate_prompt(prompt, test, "test", client, cfg, rd, EvalCache())
        print(f"[{tag}] {name:<20} cov={res['coverage_strict']:.3f} "
              f"covL={res['coverage_loose']:.3f} "
              f"F1-used={res['f1_used_strict']:.4f} "
              f"F1-wrong={res['f1_wrong_strict']:.4f}", flush=True)
        rows.append({"cond": tag, "name": name, "num_predict": num_predict,
                     "cov": res["coverage_strict"], "cov_loose": res["coverage_loose"],
                     "f1_used": res["f1_used_strict"],
                     "f1_wrong": res["f1_wrong_strict"], "prompt": prompt})
    write_json(f"results/mechanism/{tag}/summary.json", rows)
    return rows


def main():
    ap = base_argparser(__doc__)
    ap.add_argument("--mode", default="ablation",
                    choices=["ablation", "saturation", "both"])
    ap.add_argument("--sat-num-predict", type=int, default=128)
    args = ap.parse_args()
    cfg, client, dev, test, manuals = bootstrap(args)

    if args.mode in ("ablation", "both"):
        pairs = []
        for arm, seed in RUNS:
            p = load_prompt(arm, seed)
            pairs.append((f"{arm}_seed{seed}_KISITLI", p + CONSTRAINT))
        print("\n--- (A) NEDENSEL ABLASYON: format kısıtı geri kondu, np=24 ---")
        print(f"    (baseline referans: cov=1.000 F1-used=0.7930)\n")
        run_condition(cfg, client, test, "ablation_np24", pairs, 24)

    if args.mode in ("saturation", "both"):
        pairs = [("baseline_M2_HAM", load_baseline_prompt())]
        for arm, seed in RUNS:
            pairs.append((f"{arm}_seed{seed}_HAM", load_prompt(arm, seed)))
        np_ = args.sat_num_predict
        print(f"\n--- (B) BÜTÇE DOYGUNLUĞU: promptlar ham, np={np_} ---\n")
        run_condition(cfg, client, test, f"saturation_np{np_}", pairs, np_)


if __name__ == "__main__":
    main()
