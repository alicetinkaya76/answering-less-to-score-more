"""Uçtan uca KURU KOŞU: sentetik veri + MockClient.

Bu, GERÇEK deney değildir; harness'ın kod-düzeyi doğrulamasıdır:
veri->split->baseline->OPRO->GA(excl/wrong)->RS->rapor hattı Ollama olmadan çalışmalı,
metrikler [0,1] içinde olmalı, dosyalar oluşmalı, rejim sınıflandırıcısı koşmalı.
"""

import json
import os
import shutil
import tempfile
import unittest

from fg.cli import load_manual_prompts
from fg.common import load_config
from fg.data import load_dataset, make_or_load_splits
from fg.evalharness import EvalCache, evaluate_prompt
from fg.ga import run_ga, run_random_search
from fg.mockllm import MockClient, latent_label
from fg.opro import run_opro
from fg.report import build_report


WORDS = ["merhaba", "bugün", "hava", "çok", "kötü", "harika", "insanlar", "yine",
         "trafik", "maç", "siyaset", "yemek", "kitap", "film", "yorum", "saçma",
         "berbat", "güzel", "aptalca", "sevimli"]


def synth_tsv(path, n=60):
    import random
    rng = random.Random(3)
    with open(path, "w", encoding="utf-8") as f:
        f.write("id\ttext\tlabel\n")
        for i in range(n):
            text = " ".join(rng.choice(WORDS) for _ in range(rng.randint(4, 9))) + f" #{i}"
            gold = latent_label(text)  # mock hedef-modelle tutarlı latent kural
            raw = "SATIRIK" if gold == "EVET" else "GERCEK"
            f.write(f"t{i}\t{text}\t{raw}\n")


class TestSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="fg_smoke_")
        cls.old_cwd = os.getcwd()
        # proje dosyalarını (config, prompts) referans al, çalışma dizinini tmp yap
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(cls.tmp)
        os.makedirs("data", exist_ok=True)
        synth_tsv("data/satire_tr.tsv", n=60)
        with open(os.path.join(root, "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["data"]["dev_size"] = 24
        cfg["data"]["test_size"] = 24
        cfg["seeds"] = [5]
        cfg["ga"].update({"pop": 4, "gens": 3})
        cfg["opro"].update({"steps": 2, "candidates_per_step": 3})
        cfg["rs"]["target_evals"] = 8
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
        shutil.copy(os.path.join(root, "prompts_manual.json"), "prompts_manual.json")
        cls.cfg = cfg
        cls.client = MockClient(seed=1)

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.old_cwd)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _rd(self, arm, seed):
        d = os.path.join(self.cfg["results_dir"], arm, f"seed{seed}")
        os.makedirs(os.path.join(d, "raw"), exist_ok=True)
        os.makedirs(os.path.join(d, "preds"), exist_ok=True)
        return d

    def test_full_pipeline(self):
        cfg, client = self.cfg, self.client
        items = load_dataset(cfg["data"])
        dev, test = make_or_load_splits(items, cfg["data"])
        self.assertEqual(len(dev), 24)
        self.assertEqual(len(test), 24)
        manuals = load_manual_prompts(cfg)

        # baseline'lar + baselines.json
        bdir = self._rd("baselines", 0).rsplit(os.sep, 1)[0]
        os.makedirs(os.path.join(bdir, "raw"), exist_ok=True)
        os.makedirs(os.path.join(bdir, "preds"), exist_ok=True)
        cache = EvalCache()
        rows = []
        for i, m in enumerate(manuals, 1):
            d = evaluate_prompt(m, dev, "dev", client, cfg, bdir, cache)
            t = evaluate_prompt(m, test, "test", client, cfg, bdir, cache)
            for res in (d, t):
                for k in ("coverage_strict", "coverage_loose", "f1_used_strict",
                          "f1_wrong_strict"):
                    self.assertGreaterEqual(res[k], 0.0)
                    self.assertLessEqual(res[k], 1.0)
            rows.append({"name": f"M{i}", "sha": d["sha"], "prompt": m,
                         "dev": d, "test": t})
        # duplicate-cache: aynı prompt ikinci kez eval EDİLMEZ
        before = cache.realized
        evaluate_prompt(manuals[0], dev, "dev", client, cfg, bdir, cache)
        self.assertEqual(cache.realized, before)

        best = max(rows, key=lambda r: r["dev"]["f1_used_strict"])
        with open(os.path.join(bdir, "baselines.json"), "w", encoding="utf-8") as f:
            json.dump({"baseline": best, "all": rows}, f, ensure_ascii=False)

        # OPRO / GA(excl) / GA(wrong) / RS
        s1 = run_opro(cfg, client, dev, test, manuals, "excl", 5,
                      self._rd("opro_excl", 5))
        s2 = run_ga(cfg, client, dev, test, manuals, "excl", 5,
                    self._rd("ga_excl", 5))
        s3 = run_ga(cfg, client, dev, test, manuals, "wrong", 5,
                    self._rd("ga_wrong", 5))
        s4 = run_random_search(cfg, client, dev, test, manuals, "excl", 5,
                               self._rd("rs_excl", 5), target_evals=8)
        for s in (s1, s2, s3, s4):
            self.assertIn("test", s)
            self.assertGreater(s["realized_unique_evals"], 0)

        # ham çıktı + per-item arşivi oluşmuş mu
        raws = []
        for root, _, files in os.walk(cfg["results_dir"]):
            raws += [f for f in files if f.endswith(".txt")]
        self.assertGreater(len(raws), 50)

        # rapor
        gates, table = build_report(cfg, os.path.join(bdir, "baselines.json"))
        self.assertTrue(os.path.exists(os.path.join(cfg["results_dir"], "REPORT.md")))
        self.assertEqual(set(gates.keys()),
                         {"gate1_harness_pattern", "gate2_phenomenon",
                          "gate3_intervention"})
        regimes = {r["cls"]["regime"] for r in table}
        self.assertTrue(regimes <= {"clean_win", "clean_loss", "coverage_manipulated",
                                    "parser_artefact", "null"})


if __name__ == "__main__":
    unittest.main()
