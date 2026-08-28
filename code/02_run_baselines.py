#!/usr/bin/env python3
"""KAPI 0 — Harness kalibrasyonu: M1–M8'i dev VE test'te değerlendir.

- Manuel-baseline = dev-en-iyisi (F_excl'e göre); tüm Δ'lar buna göre hesaplanır.
- config.published_baseline verilirse (yayınlanan test F1/coverage), sapma yazdırılır:
  aynı model + aynı sabit indeksler + greedy decoding ile bu sayıların toleransta
  oturması, ölçüm hattını ESKİ KODA İHTİYAÇ DUYMADAN doğrular.
"""
import os

from fg.cli import base_argparser, bootstrap, snapshot_config
from fg.common import ensure_dir, write_json
from fg.evalharness import EvalCache, evaluate_prompt


def main():
    ap = base_argparser(__doc__)
    args = ap.parse_args()
    cfg, client, dev, test, manuals = bootstrap(args)

    run_dir = ensure_dir(os.path.join(cfg["results_dir"], "baselines"))
    ensure_dir(os.path.join(run_dir, "raw"))
    ensure_dir(os.path.join(run_dir, "preds"))
    snapshot_config(cfg, client, run_dir, {"arm": "baselines"})
    cache = EvalCache()

    rows = []
    for i, m in enumerate(manuals, start=1):
        d = evaluate_prompt(m, dev, "dev", client, cfg, run_dir, cache)
        t = evaluate_prompt(m, test, "test", client, cfg, run_dir, cache)
        rows.append({"name": f"M{i}", "sha": d["sha"], "prompt": m,
                     "dev": d, "test": t})
        print(f"M{i} [{d['sha']}]  dev F1-used={d['f1_used_strict']:.4f} "
              f"cov={d['coverage_strict']:.3f} | test F1-used={t['f1_used_strict']:.4f} "
              f"cov={t['coverage_strict']:.3f} F1-wrong={t['f1_wrong_strict']:.4f}")

    best = max(rows, key=lambda r: r["dev"]["f1_used_strict"])
    print(f"\nManuel-baseline (dev-en-iyisi): {best['name']} [{best['sha']}]")

    # --- prompt-uyuşmazlığı (zor-kuyruk vekili): dev'de M-promptların katı tahminleri
    # oybirliği DEĞİLSE örnek 'kararsız' sayılır (abstain'ler de uyuşmazlıktır).
    import json as _json
    per_item = {}
    for r in rows:
        pp = os.path.join(run_dir, "preds", f"dev_{r['dev']['sha']}.jsonl")
        with open(pp, encoding="utf-8") as f:
            for line in f:
                d = _json.loads(line)
                per_item.setdefault(d["id"], []).append(d["strict"])
    n_items = len(per_item)
    unstable = sum(1 for v in per_item.values() if len(set(v)) > 1)
    disagreement = unstable / n_items if n_items else 0.0
    print(f"Prompt-uyuşmazlığı (dev): {unstable}/{n_items} = {disagreement:.3f}")

    # --- Önceden-kayıtlı GO/ADJUST kararı (config.audition): hücre tatlı bölgede mi?
    aud = cfg.get("audition", {})
    bt = best["test"]
    checks = {
        f"coverage ≥ {aud.get('min_coverage', 0.85)}":
            bt["coverage_strict"] >= float(aud.get("min_coverage", 0.85)),
        f"F1-used ∈ [{aud.get('f1_lo', 0.55)}, {aud.get('f1_hi', 0.85)}]":
            float(aud.get("f1_lo", 0.55)) <= bt["f1_used_strict"]
            <= float(aud.get("f1_hi", 0.85)),
        f"uyuşmazlık ≥ {aud.get('min_disagreement', 0.10)}":
            disagreement >= float(aud.get("min_disagreement", 0.10)),
    }
    verdict = "GO" if all(checks.values()) else "ADJUST"
    print(f"\nSEÇMECE KARARI: {verdict}")
    for k, v in checks.items():
        print(f"  [{'✓' if v else '✗'}] {k}")
    if verdict == "ADJUST":
        print("  → Hücre tatlı bölge dışında. README'deki yedek zincirini uygula "
              "(FCTR-küçük hücre) ya da kırpma/görev tanımını ayarlayıp 02'yi tekrar koş. "
              "Pahalı optimizer koşularına (03/04) GEÇME.")

    pub = cfg.get("published_baseline")
    if pub:
        dt = best["test"]["f1_used_strict"] - float(pub.get("f1_used", 0))
        dc = best["test"]["coverage_strict"] - float(pub.get("coverage", 0))
        print(f"KALİBRASYON — yayınlanan baseline'a sapma: ΔF1-used={dt:+.4f}, "
              f"Δcoverage={dc:+.4f}  (|Δ| küçükse harness doğrulandı)")
    else:
        print("Not: config.published_baseline boş — kalibrasyon yön-düzeyinde kalır. "
              "Yayınlanan baseline sayılarını girersen KAPI 0 sayı-düzeyine yükselir.")

    write_json(os.path.join(run_dir, "baselines.json"),
               {"baseline": best, "all": rows,
                "disagreement": disagreement, "audition_verdict": verdict,
                "realized_unique_evals": cache.realized})
    print(f"Yazıldı: {os.path.join(run_dir, 'baselines.json')}")


if __name__ == "__main__":
    main()
