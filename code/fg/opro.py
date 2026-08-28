"""OPRO (Large Language Models as Optimizers) — standalone, minimal, sadık iskelet.

Amaç: bilinen-pozitif DESENİ (F_excl altında F1-used artarken coverage düşüşü) bu
kurulumda yeniden üretmek. Sıfırdan implementasyon olduğu için sayı-düzeyinde birebir
reprodüksiyon (ΔF1≈+0.081, cov≈0.573) BEKLENMEZ; desen + mertebe raporlanır (README,
"Kapı 0/1"). Bütçe: steps × candidates_per_step; varsayılan 6×8=48 aday, GA'nın
gerçekleşen ~38–47 eval bandına bilinçli olarak yakın (compute-uyumlu).
"""

import os
import random

from .common import append_jsonl, sha_of, write_json
from .evalharness import EvalCache, evaluate_prompt, fitness_value
from .operators import _task_desc, extract_instruction, validity


def _meta_prompt(trajectory, exemplars, task, top_k=12):
    traj = sorted(trajectory, key=lambda t: t[0])[-top_k:]  # artan: en iyi en sonda
    lines = [
        f"Şu görev için bir dil modeline verilecek TALİMAT arıyoruz: {task}.",
        "Aşağıda daha önce denenmiş talimatlar ve puanları var (puan yüksek = iyi):", "",
    ]
    for score, _, text in traj:
        lines.append(f"PUAN: {score:.4f}\nTALİMAT: {text.strip()}\n")
    lines.append("Görevden örnekler:")
    for it in exemplars:
        lines.append(f"Metin: \"{it['text']}\"\nDoğru cevap: {it['gold']}")
    lines += [
        "",
        "Yukarıdakilerin HEPSİNDEN farklı ve daha yüksek puan alacak YENİ bir Türkçe "
        "talimat yaz. Talimat kısa ve insan-okunur olsun; modelden YALNIZCA EVET veya "
        "HAYIR üretmesini istesin.",
        "Yalnızca yeni talimatı <TALIMAT> ve </TALIMAT> etiketleri arasında ver.",
    ]
    return "\n".join(lines)


def run_opro(cfg, client, dev, test, manuals, fitness_name, seed, run_dir):
    o = cfg["opro"]
    steps = int(o.get("steps", 6))
    per_step = int(o.get("candidates_per_step", 8))
    n_exemplars = int(o.get("exemplars", 3))

    rng = random.Random(seed)
    cache = EvalCache()
    gen_log = os.path.join(run_dir, "gen_log.jsonl")
    exemplars = rng.sample(dev, min(n_exemplars, len(dev)))

    trajectory = []  # (dev_fitness, sha, text)
    best = None

    def eval_and_log(text, step, rank):
        nonlocal best
        res = evaluate_prompt(text, dev, "dev", client, cfg, run_dir, cache)
        fit = fitness_value(fitness_name, res, cfg.get("fitness_parser", "strict"))
        trajectory.append((fit, res["sha"], text))
        append_jsonl(gen_log, {"seed": seed, "gen": step, "rank": rank,
                               "sha": res["sha"], "fitness": fit,
                               "fitness_name": fitness_name,
                               "f1_used": res["f1_used_strict"],
                               "coverage": res["coverage_strict"],
                               "coverage_loose": res["coverage_loose"],
                               "f1_wrong": res["f1_wrong_strict"],
                               "f1_adj": res["f1_adj_strict"],
                               "is_elite": False, "prompt": text})
        if best is None or fit > best[0]:
            best = (fit, res)

    # yörünge, manuel promptlarla tohumlanır (gen=-1 olarak loglanır -> gen 0'da)
    for i, m in enumerate(manuals):
        eval_and_log(m.strip(), 0, i)

    opts_base = dict(cfg.get("optimizer_decoding", {"temperature": 0.9, "num_predict": 400}))
    model = cfg.get("optimizer_model", cfg["target_model"])
    keep = cfg.get("keep_alive", "30m")
    seen = {sha for _, sha, _ in trajectory}

    for step in range(1, steps + 1):
        meta = _meta_prompt(trajectory, exemplars, _task_desc(cfg))
        produced = 0
        attempt = 0
        while produced < per_step and attempt < per_step * 3:
            attempt += 1
            opts = dict(opts_base)
            opts["seed"] = seed * 100000 + step * 1000 + attempt
            reply = client.generate(meta, model=model, options=opts, keep_alive=keep)
            instr = extract_instruction(reply)
            ok, _ = validity(instr, cfg)
            if not ok or sha_of(instr) in seen:
                continue
            seen.add(sha_of(instr))
            eval_and_log(instr, step, produced)
            produced += 1
        print(f"[OPRO seed{seed}] adim {step}/{steps} bitti: uretilen={produced} "
              f"| yorunge-en-iyi={max(t[0] for t in trajectory):.4f} "
              f"| benzersiz-eval={cache.realized}", flush=True)

    test_res = evaluate_prompt(best[1]["prompt"], test, "test", client, cfg,
                               run_dir, cache)
    summary = {
        "arm": f"opro_{fitness_name}", "seed": seed, "fitness_name": fitness_name,
        "best_dev_fitness": best[0], "best_sha": best[1]["sha"],
        "best_prompt": best[1]["prompt"],
        "dev": best[1], "test": test_res,
        "realized_unique_evals": cache.realized,
    }
    write_json(os.path.join(run_dir, "best_of_run.json"), summary)
    return summary
