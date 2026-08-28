#!/usr/bin/env python3
"""KAPI 1 — Bilinen-pozitif DESEN testi: OPRO × F_excl, hedef=qwen2.5:14b, 3 seed.

Sıfırdan implementasyon olduğu için yayınlanan sayıların (ΔF1≈+0.081, cov≈0.573)
birebir çıkması BEKLENMEZ; aranan şey desen: F1-used baseline'a göre YÜKSELİRKEN
test coverage'ın belirgin (Δ<−10pp) düşmesi ve bunun parser-artefaktı olmaması.
"""
from fg.cli import base_argparser, bootstrap, snapshot_config
from fg.common import run_dir_for
from fg.opro import run_opro


def main():
    ap = base_argparser(__doc__)
    ap.add_argument("--fitness", default="excl", choices=["excl", "wrong"])
    args = ap.parse_args()
    cfg, client, dev, test, manuals = bootstrap(args)

    seeds = args.seeds if args.seeds else cfg["seeds"]
    for seed in seeds:
        arm = f"opro_{args.fitness}"
        rd = run_dir_for(cfg, arm, seed)
        snapshot_config(cfg, client, rd, {"arm": arm, "seed": seed})
        s = run_opro(cfg, client, dev, test, manuals, args.fitness, seed, rd)
        t = s["test"]
        print(f"[{arm} seed{seed}] dev-fit={s['best_dev_fitness']:.4f} | "
              f"TEST F1-used={t['f1_used_strict']:.4f} cov={t['coverage_strict']:.3f} "
              f"cov_loose={t['coverage_loose']:.3f} F1-wrong={t['f1_wrong_strict']:.4f} | "
              f"eval={s['realized_unique_evals']}")


if __name__ == "__main__":
    main()
