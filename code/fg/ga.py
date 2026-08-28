"""EvoPrompt-TARZI talimat-GA + compute-matched random-search (RS).

Sadakat notu (handoff v2): yayınlanan EvoPrompt-GA rulet-tekerleği ebeveyn seçimi +
tek şablonda cx->mut + birleşimden top-N kullanır; biz PeerJ tutarlılığı için
turnuva-3 + 2 elit + ayrı cx/mut olasılıkları kullanıyoruz. Raporda "EvoPrompt-tarzı
talimat-GA" olarak adlandırılır; elitizmin düşük-coverage bireyleri kilitleyebileceği
tartışma notu olarak kaydedilir.

Yürütme deseni: jenerasyon-başına toplu akış — önce TÜM çocuklar üretilir (optimize-edici
model), sonra TÜMÜ dev'de değerlendirilir (hedef model). Model-swap nesil sayısıyla sınırlı.
"""

import os
import random

from .common import append_jsonl, now_iso, sha_of, write_json
from .evalharness import EvalCache, evaluate_prompt, fitness_value
from .operators import llm_variation


def _init_population(manuals, pop_size, client, cfg, rng, log):
    pop = [m.strip() for m in manuals][:pop_size]
    fill_seed = rng.randrange(10**6)
    tries = 0
    while len(pop) < pop_size and tries < pop_size * 5:
        tries += 1
        parent = rng.choice(manuals)
        instr, r, reason = llm_variation("mut", [parent], client, cfg,
                                         seed=fill_seed + tries)
        if instr is not None and sha_of(instr) not in {sha_of(p) for p in pop}:
            pop.append(instr)
            log({"event": "init_fill", "retries": r})
        else:
            log({"event": "init_fill_fail", "reason": reason})
    while len(pop) < pop_size:  # son çare: mevcutları kopyala (eval cache maliyeti sıfırlar)
        pop.append(rng.choice(pop))
    return pop


def _tournament(scored, k, rng):
    cand = rng.sample(scored, min(k, len(scored)))
    return max(cand, key=lambda t: t[0])


def run_ga(cfg, client, dev, test, manuals, fitness_name, seed, run_dir):
    g = cfg["ga"]
    pop_size, gens = int(g["pop"]), int(g["gens"])
    tour, n_elite = int(g["tournament"]), int(g["elites"])
    cx_p, mut_p = float(g["cx_prob"]), float(g["mut_prob"])

    rng = random.Random(seed)
    cache = EvalCache()
    gen_log = os.path.join(run_dir, "gen_log.jsonl")
    ops_log = os.path.join(run_dir, "ops_log.jsonl")

    def oplog(row):
        row.update({"seed": seed, "ts": now_iso()})
        append_jsonl(ops_log, row)

    pop = _init_population(manuals, pop_size, client, cfg, rng, oplog)
    best = None  # (fit, res)

    for gen in range(gens):
        # --- toplu DEĞERLENDİRME fazı (hedef model) ---
        scored = []
        for text in pop:
            res = evaluate_prompt(text, dev, "dev", client, cfg, run_dir, cache)
            fit = fitness_value(fitness_name, res, cfg.get("fitness_parser", "strict"))
            scored.append((fit, res["sha"], text, res))
            if best is None or fit > best[0]:
                best = (fit, res)
        scored.sort(key=lambda t: (-t[0], t[1]))
        print(f"[GA {fitness_name} seed{seed}] jen {gen + 1}/{gens} degerlendirildi: "
              f"en-iyi fit={scored[0][0]:.4f} cov={scored[0][3]['coverage_strict']:.3f} "
              f"| benzersiz-eval={cache.realized}", flush=True)
        elite_shas = {s for _, s, _, _ in scored[:n_elite]}
        for rank, (fit, sha, text, res) in enumerate(scored):
            append_jsonl(gen_log, {
                "seed": seed, "gen": gen, "rank": rank, "sha": sha,
                "fitness": fit, "fitness_name": fitness_name,
                "f1_used": res["f1_used_strict"],
                "coverage": res["coverage_strict"],
                "coverage_loose": res["coverage_loose"],
                "f1_wrong": res["f1_wrong_strict"],
                "f1_adj": res["f1_adj_strict"],
                "is_elite": sha in elite_shas,
                "prompt": text,
            })
        if gen == gens - 1:
            break

        # --- toplu ÜRETİM fazı (optimize-edici model) ---
        elites = [t for _, _, t, _ in scored[:n_elite]]
        children = []
        while len(children) < pop_size - n_elite:
            p1 = _tournament(scored, tour, rng)[2]
            p2 = _tournament(scored, tour, rng)[2]
            child = p1
            op_used = "clone"
            if rng.random() < cx_p and sha_of(p1) != sha_of(p2):
                out, r, reason = llm_variation("cx", [p1, p2], client, cfg,
                                               seed=rng.randrange(10**6))
                oplog({"event": "cx", "gen": gen, "ok": out is not None,
                       "retries": r, "reason": reason})
                if out is not None:
                    child, op_used = out, "cx"
            if rng.random() < mut_p:
                out, r, reason = llm_variation("mut", [child], client, cfg,
                                               seed=rng.randrange(10**6))
                oplog({"event": "mut", "gen": gen, "ok": out is not None,
                       "retries": r, "reason": reason})
                if out is not None:
                    child, op_used = out, (op_used + "+mut").lstrip("clone+")
            children.append(child)
        pop = elites + children

    # --- best-of-run: dev fitness'a göre; rapor metrikleri TEST'te ---
    test_res = evaluate_prompt(best[1]["prompt"], test, "test", client, cfg,
                               run_dir, cache)
    summary = {
        "arm": f"ga_{fitness_name}", "seed": seed, "fitness_name": fitness_name,
        "best_dev_fitness": best[0], "best_sha": best[1]["sha"],
        "best_prompt": best[1]["prompt"],
        "dev": best[1], "test": test_res,
        "realized_unique_evals": cache.realized,
    }
    write_json(os.path.join(run_dir, "best_of_run.json"), summary)
    return summary


def run_random_search(cfg, client, dev, test, manuals, fitness_name, seed, run_dir,
                      target_evals):
    """Talimat-uzayı RS (handoff v2 tanımı): başlangıç havuzundan SEÇİLİMSİZ
    LLM-mutasyonlarıyla target_evals kadar benzersiz aday üret; hepsini dev'de
    değerlendir; SONDA fitness'a göre en iyiyi seç. Yalnız PIVOT-tanısı / Aşama 2."""
    rng = random.Random(seed)
    cache = EvalCache()
    gen_log = os.path.join(run_dir, "gen_log.jsonl")

    candidates = [m.strip() for m in manuals]
    seen = {sha_of(c) for c in candidates}
    tries = 0
    while len(candidates) < target_evals and tries < target_evals * 6:
        tries += 1
        parent = rng.choice(manuals)  # seçilim YOK: ebeveyn her zaman başlangıç havuzundan
        instr, _, _ = llm_variation("mut", [parent], client, cfg,
                                    seed=rng.randrange(10**6))
        if instr is not None and sha_of(instr) not in seen:
            seen.add(sha_of(instr))
            candidates.append(instr)

    best = None
    for i, text in enumerate(candidates):
        res = evaluate_prompt(text, dev, "dev", client, cfg, run_dir, cache)
        fit = fitness_value(fitness_name, res, cfg.get("fitness_parser", "strict"))
        append_jsonl(gen_log, {"seed": seed, "gen": 0, "rank": i, "sha": res["sha"],
                               "fitness": fit, "fitness_name": fitness_name,
                               "f1_used": res["f1_used_strict"],
                               "coverage": res["coverage_strict"],
                               "coverage_loose": res["coverage_loose"],
                               "f1_wrong": res["f1_wrong_strict"],
                               "f1_adj": res["f1_adj_strict"],
                               "is_elite": False, "prompt": text})
        if best is None or fit > best[0]:
            best = (fit, res)

    test_res = evaluate_prompt(best[1]["prompt"], test, "test", client, cfg,
                               run_dir, cache)
    summary = {
        "arm": f"rs_{fitness_name}", "seed": seed, "fitness_name": fitness_name,
        "best_dev_fitness": best[0], "best_sha": best[1]["sha"],
        "best_prompt": best[1]["prompt"],
        "dev": best[1], "test": test_res,
        "realized_unique_evals": cache.realized,
    }
    write_json(os.path.join(run_dir, "best_of_run.json"), summary)
    return summary
