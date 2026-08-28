#!/usr/bin/env python3
"""ZOR-DİLİM PROBU — stil-arındırılmış 200 satirik makale üzerinde best-of-run analizi.

Mantık: coverage-manipülasyonu gerçekse, abstain'ler kolay örneklere değil ZOR
örneklere yığılmalıdır. Bu script, seçilen kolun best-of-run promptunu
data/satire_probe_debiased.tsv (hepsi SATIRIK) üzerinde değerlendirir ve
probe-coverage'ı ana test-coverage ile yan yana koyar:

  probe_coverage << test_coverage  →  abstention zor dilimde yoğunlaşıyor
                                      (manipülasyon mekanizması doğrulanır)

Kullanım:
  python3 06_probe_hard_slice.py --arm ga_excl --seed 11
  python3 06_probe_hard_slice.py --arm ga_excl --seed 11 --mock
"""
import json
import os

from fg.cli import base_argparser, bootstrap
from fg.common import ensure_dir
from fg.data import load_dataset
from fg.evalharness import EvalCache, evaluate_prompt


def main():
    ap = base_argparser(__doc__)
    ap.add_argument("--arm", required=True, help="ör: ga_excl, opro_excl, ga_wrong")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--probe", default="data/satire_probe_debiased.tsv")
    args = ap.parse_args()
    cfg, client, dev, test, manuals = bootstrap(args)

    bor = os.path.join(cfg["results_dir"], args.arm, f"seed{args.seed}",
                       "best_of_run.json")
    if not os.path.exists(bor):
        raise SystemExit(f"best_of_run yok: {bor} — önce ilgili kolu koş.")
    with open(bor, encoding="utf-8") as f:
        s = json.load(f)

    pcfg = dict(cfg["data"])
    pcfg["path"] = args.probe
    probe_items = load_dataset(pcfg)

    run_dir = os.path.join(cfg["results_dir"], args.arm, f"seed{args.seed}")
    ensure_dir(os.path.join(run_dir, "raw"))
    ensure_dir(os.path.join(run_dir, "preds"))
    cache = EvalCache()
    res = evaluate_prompt(s["best_prompt"], probe_items, "probe", client, cfg,
                          run_dir, cache)

    t = s["test"]
    print(f"[{args.arm} seed{args.seed}] best-of-run [{s['best_sha']}]")
    print(f"  TEST : coverage={t['coverage_strict']:.3f}  F1-used={t['f1_used_strict']:.4f}")
    print(f"  PROBE: coverage={res['coverage_strict']:.3f}  "
          f"(cevaplananlarda doğruluk ~ F1-used={res['f1_used_strict']:.4f}; "
          f"dilim tek-sınıf olduğundan asıl gösterge COVERAGE farkıdır)")
    gap = (t["coverage_strict"] - res["coverage_strict"]) * 100
    print(f"  Δcoverage (test − probe) = {gap:+.1f}pp  "
          f"→ {'zor dilimde yoğunlaşan abstention' if gap > 5 else 'belirgin yoğunlaşma yok'}")
    out = {"arm": args.arm, "seed": args.seed, "best_sha": s["best_sha"],
           "test": t, "probe": res, "gap_pp": gap}
    with open(os.path.join(run_dir, "probe_hard_slice.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
