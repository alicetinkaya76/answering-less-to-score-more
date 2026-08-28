"""Değerlendirme hattı (harness) + metrikler + fitness.

KESİN FORMÜLLER (handoff v2, Bölüm 3):
- F_excl : macro-F1, YALNIZ katı-parse edilebilen tahminler üzerinden. coverage=0 => 0.0.
- F_wrong: macro-F1; abstain/parse-edilemeyen HER örnek altın sınıfı için yanlış sayılır:
           altın sınıfa bir FN yazılır, HİÇBİR sınıfa FP yazılmaz. coverage=0 => 0.0.
- F_adj  : F1_used * coverage (yalnız rapor metriği).

Harness garantileri:
- HAM çıktılar her zaman diske yazılır (parser-robustness bunun üzerinden çalışır).
- Per-item tahmin arşivi (id, gold, strict_pred, loose_pred) jsonl olarak saklanır.
- Duplicate-genom önbelleği: aynı prompt (sha) aynı split'te İKİNCİ KEZ değerlendirilmez;
  gerçekleşen-eval sayacı yalnız önbellek kaçırınca artar.
"""

import os

from .common import append_jsonl, ensure_dir, sha_of
from .parse import parse_both


# ---------------- metrikler ----------------

def _macro_f1(counts, labels):
    f1s = []
    for lab in labels:
        tp, fp, fn = counts[lab]["tp"], counts[lab]["fp"], counts[lab]["fn"]
        denom = 2 * tp + fp + fn
        f1s.append((2 * tp / denom) if denom else 0.0)
    return sum(f1s) / len(f1s) if f1s else 0.0


def metrics_from_preds(golds, preds, labels):
    """golds: [EVET/HAYIR], preds: [EVET/HAYIR/None]. Tüm rapor metriklerini döndürür."""
    n = len(golds)
    used = [(g, p) for g, p in zip(golds, preds) if p is not None]
    coverage = len(used) / n if n else 0.0

    # F1-used: yalnız parse edilenler evreninde
    c_used = {lab: {"tp": 0, "fp": 0, "fn": 0} for lab in labels}
    for g, p in used:
        if p == g:
            c_used[g]["tp"] += 1
        else:
            c_used[p]["fp"] += 1
            c_used[g]["fn"] += 1
    f1_used = _macro_f1(c_used, labels) if used else 0.0

    # F1-wrong: abstain -> altın sınıfa FN, FP yok
    c_wrong = {lab: {"tp": 0, "fp": 0, "fn": 0} for lab in labels}
    for g, p in zip(golds, preds):
        if p is None:
            c_wrong[g]["fn"] += 1
        elif p == g:
            c_wrong[g]["tp"] += 1
        else:
            c_wrong[p]["fp"] += 1
            c_wrong[g]["fn"] += 1
    f1_wrong = _macro_f1(c_wrong, labels) if n else 0.0
    if coverage == 0.0:
        f1_used, f1_wrong = 0.0, 0.0  # dejenere prompt tanımlı biçimde en dipte

    return {"n": n, "coverage": coverage, "f1_used": f1_used,
            "f1_wrong": f1_wrong, "f1_adj": f1_used * coverage}


# ---------------- fitness ----------------

FITNESS_NAMES = ("excl", "wrong")


def fitness_value(name, res, parser="strict"):
    """parser='strict' (varsayılan) veya 'loose' (SERTLEŞTİRİLMİŞ hat rejimi)."""
    suf = "_loose" if parser == "loose" else "_strict"
    if name == "excl":
        return res["f1_used" + suf]
    if name == "wrong":
        return res["f1_wrong" + suf]
    raise ValueError(f"Bilinmeyen fitness: {name!r} (geçerli: {FITNESS_NAMES})")


# ---------------- harness ----------------

class EvalCache:
    """(split_adı, prompt_sha) -> sonuç. Gerçekleşen benzersiz eval sayacını tutar."""

    def __init__(self):
        self._store = {}
        self.realized = 0

    def get(self, split_name, sha):
        return self._store.get((split_name, sha))

    def put(self, split_name, sha, res):
        self._store[(split_name, sha)] = res
        self.realized += 1


def build_item_prompt(instruction, item_text, template):
    return template.format(instruction=instruction.strip(), text=item_text)


def evaluate_prompt(instruction, items, split_name, client, cfg, run_dir, cache,
                    lexicon=None):
    """Bir talimatı bir split üzerinde değerlendirir; tüm metrik sözlüğünü döndürür."""
    sha = sha_of(instruction)
    hit = cache.get(split_name, sha)
    if hit is not None:
        return hit

    template = cfg.get("item_template", "{instruction}\n\nTweet: \"{text}\"\nCevap:")
    dec = dict(cfg.get("decoding", {"temperature": 0.0, "num_predict": 24}))
    dec.setdefault("seed", 7)  # temp=0 + sabit seed: aynı girdi -> aynı çıktı
    model = cfg["target_model"]
    keep = cfg.get("keep_alive", "30m")

    raw_dir = ensure_dir(os.path.join(run_dir, "raw", f"{split_name}_{sha}"))
    preds_path = os.path.join(run_dir, "preds", f"{split_name}_{sha}.jsonl")

    def _one(it):
        out = client.generate(build_item_prompt(instruction, it["text"], template),
                              model=model, options=dec, keep_alive=keep)
        with open(os.path.join(raw_dir, f"{it['id']}.txt"), "w", encoding="utf-8") as f:
            f.write(out)
        s, l = parse_both(out, lexicon)
        return it["id"], it["gold"], s, l

    workers = max(1, int(cfg.get("parallel_requests", 1)))
    results = []
    if workers == 1:
        for idx, it in enumerate(items, 1):
            results.append(_one(it))
            if idx % 50 == 0:
                print(f"    ... {idx}/{len(items)}", flush=True)
    else:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for idx, r in enumerate(ex.map(_one, items), 1):  # girdi sırası korunur
                results.append(r)
                if idx % 50 == 0:
                    print(f"    ... {idx}/{len(items)}", flush=True)

    golds, strict_preds, loose_preds = [], [], []
    for iid, gold, s, l in results:
        golds.append(gold)
        strict_preds.append(s)
        loose_preds.append(l)
        append_jsonl(preds_path, {"id": iid, "gold": gold, "strict": s, "loose": l})

    labels = sorted(cfg.get("labels", {"positive": "EVET", "negative": "HAYIR"}).values())
    m_s = metrics_from_preds(golds, strict_preds, labels)
    m_l = metrics_from_preds(golds, loose_preds, labels)

    res = {
        "sha": sha, "prompt": instruction, "split": split_name, "n": m_s["n"],
        "coverage_strict": m_s["coverage"], "coverage_loose": m_l["coverage"],
        "f1_used_strict": m_s["f1_used"], "f1_used_loose": m_l["f1_used"],
        "f1_wrong_strict": m_s["f1_wrong"], "f1_wrong_loose": m_l["f1_wrong"],
        "f1_adj_strict": m_s["f1_adj"],
    }
    cache.put(split_name, sha, res)
    print(f"  [{split_name} eval #{cache.realized}] {sha} cov={res['coverage_strict']:.3f} "
          f"f1_used={res['f1_used_strict']:.4f} f1_wrong={res['f1_wrong_strict']:.4f}",
          flush=True)
    return res
