#!/usr/bin/env python3
"""num_predict duyarlılık eki: 6 kazanan + baseline'ı test'te farklı decode bütçesiyle yeniden değerlendirir."""
import copy
import json
import os

from fg.cli import base_argparser, bootstrap
from fg.common import ensure_dir, write_json
from fg.evalharness import EvalCache, evaluate_prompt

RUNS = [("opro_excl", 11), ("opro_excl", 23), ("opro_excl", 47),
        ("ga_excl", 11), ("ga_excl", 23), ("ga_excl", 47)]


def main():
    ap = base_argparser(__doc__)
    ap.add_argument("--num-predict", type=int, default=64)
    args = ap.parse_args()
    cfg, client, dev, test, manuals = bootstrap(args)
    cfg = copy.deepcopy(cfg)
    cfg["decoding"]["num_predict"] = args.num_predict

    base = json.load(open("results/pilot/baselines/baselines.json",
                          encoding="utf-8"))["baseline"]
    targets = [("baseline_M2", 0, base["prompt"])]
    for arm, seed in RUNS:
        s = json.load(open(f"results/pilot/{arm}/seed{seed}/best_of_run.json",
                           encoding="utf-8"))
        targets.append((arm, seed, s["best_prompt"]))

    rows = []
    for arm, seed, prompt in targets:
        rd = ensure_dir(f"results/sensitivity_np{args.num_predict}/{arm}_seed{seed}")
        ensure_dir(os.path.join(rd, "raw"))
        ensure_dir(os.path.join(rd, "preds"))
        res = evaluate_prompt(prompt, test, "test", client, cfg, rd, EvalCache())
        print(f"[{arm} seed{seed}] np={args.num_predict}: "
              f"cov={res['coverage_strict']:.3f} covL={res['coverage_loose']:.3f} "
              f"F1-used={res['f1_used_strict']:.4f} F1-wrong={res['f1_wrong_strict']:.4f}")
        rows.append({"arm": arm, "seed": seed, "num_predict": args.num_predict,
                     "cov": res["coverage_strict"], "cov_loose": res["coverage_loose"],
                     "f1_used": res["f1_used_strict"], "f1_wrong": res["f1_wrong_strict"]})
    write_json(f"results/sensitivity_np{args.num_predict}/summary.json", rows)


if __name__ == "__main__":
    main()
