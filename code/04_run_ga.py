#!/usr/bin/env python3
"""KAPI 2/3 — EvoPrompt-tarzı talimat-GA.

Örnekler:
  python3 04_run_ga.py --fitness excl              # Görev 3 (fenomen)
  python3 04_run_ga.py --fitness wrong             # Görev 4 (müdahale)
  python3 04_run_ga.py --fitness excl --gens 10 --seeds 11 23 47 59 71 83   # PIVOT-doğrulama
  python3 04_run_ga.py --mode rs --fitness excl    # PIVOT tanı kolu (seçilimsiz RS)
"""
from fg.cli import base_argparser, bootstrap, snapshot_config
from fg.common import run_dir_for
from fg.ga import run_ga, run_random_search


def main():
    ap = base_argparser(__doc__)
    ap.add_argument("--fitness", default="excl", choices=["excl", "wrong"])
    ap.add_argument("--mode", default="ga", choices=["ga", "rs"])
    ap.add_argument("--gens", type=int, default=None)
    ap.add_argument("--pop", type=int, default=None)
    ap.add_argument("--target-evals", type=int, default=None,
                    help="rs modunda hedeflenen benzersiz eval sayısı "
                         "(varsayılan: config.rs.target_evals; GA'nın gerçekleşenine eşitle)")
    args = ap.parse_args()
    cfg, client, dev, test, manuals = bootstrap(args)
    if args.gens:
        cfg["ga"]["gens"] = args.gens
    if args.pop:
        cfg["ga"]["pop"] = args.pop

    seeds = args.seeds if args.seeds else cfg["seeds"]
    for seed in seeds:
        if args.mode == "ga":
            arm = f"ga_{args.fitness}"
            rd = run_dir_for(cfg, arm, seed)
            snapshot_config(cfg, client, rd, {"arm": arm, "seed": seed})
            s = run_ga(cfg, client, dev, test, manuals, args.fitness, seed, rd)
        else:
            arm = f"rs_{args.fitness}"
            rd = run_dir_for(cfg, arm, seed)
            tgt = args.target_evals or int(cfg.get("rs", {}).get("target_evals", 44))
            snapshot_config(cfg, client, rd, {"arm": arm, "seed": seed,
                                              "rs_target_evals": tgt})
            s = run_random_search(cfg, client, dev, test, manuals, args.fitness,
                                  seed, rd, target_evals=tgt)
        t = s["test"]
        print(f"[{s['arm']} seed{seed}] dev-fit={s['best_dev_fitness']:.4f} | "
              f"TEST F1-used={t['f1_used_strict']:.4f} cov={t['coverage_strict']:.3f} "
              f"cov_loose={t['coverage_loose']:.3f} F1-wrong={t['f1_wrong_strict']:.4f} | "
              f"eval={s['realized_unique_evals']}")


if __name__ == "__main__":
    main()
