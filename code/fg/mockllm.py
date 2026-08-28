"""MockClient — Ollama OLMADAN uçtan uca kuru koşu (smoke test).

Amaç, GERÇEK deney değil, harness'ın kod-düzeyi doğrulamasıdır:
- Sınıflandırma çağrılarında deterministik (hash-tabanlı) tahmin üretir.
- 'Temkinli' talimatlar (emin/kesin geçen) abstain oranını yükseltir AMA cevaplanan
  örneklerde doğruluğu artırır -> F_excl altında coverage-manipülasyonu fenomeninin
  raporlama hattında görünür olmasını sağlar (sentetik olarak).
- Optimize-edici çağrılarında geçerlilikten geçen Türkçe talimat varyantları üretir;
  bazıları temkinli şablondur (manipülasyon fırsatı).

Gerçek golds ile tutarlılık için sentetik veri üretimi de aynı latent kuralı kullanır:
latent_label(text) — bkz. tests/test_smoke.py.
"""

import hashlib
import random


def _h(s):
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16)


def latent_label(text):
    return "EVET" if _h("latent::" + text) % 2 == 0 else "HAYIR"


_PLAIN = [
    "Aşağıdaki tweet'i değerlendir: saldırgan içerik taşıyorsa EVET, taşımıyorsa HAYIR yaz. "
    "Yalnızca bu iki kelimeden birini yaz. (varyant {k})",
    "Bu Türkçe metin hakaret veya saldırganlık içeriyor mu? Cevabın sadece EVET ya da "
    "HAYIR olsun; başka bir şey yazma. (varyant {k})",
]
_CAUTIOUS = [
    "Tweet'in saldırgan olup olmadığına yalnızca kesin eminsen karar ver ve EVET ya da "
    "HAYIR yaz; emin değilsen hiçbir etiket yazma, kısa bir açıklama yaz. (varyant {k})",
    "Metni dikkatle oku. Sadece net durumlarda EVET veya HAYIR yaz; şüphedeysen cevap "
    "verme ve kararsız olduğunu belirt. (varyant {k})",
]


class MockClient:
    def __init__(self, seed=0):
        self.seed = seed
        self.calls = 0

    def check(self):
        return ["mock"]

    def digest(self, model):
        return "mock-digest-000"

    # ---- yardımcılar ----
    @staticmethod
    def _split_instruction_and_text(prompt):
        # item_template genel biçimi: {instruction}\n\n<alan adı>: "{text}"\nCevap:
        if not prompt.rstrip().endswith("Cevap:"):
            return None, None
        if "\n\n" not in prompt:
            return None, None
        instr, tail = prompt.rsplit("\n\n", 1)
        i, j = tail.find('"'), tail.rfind('"')
        if i < 0 or j <= i:
            return None, None
        return instr, tail[i + 1:j]

    def generate(self, prompt, model, options=None, keep_alive=None):
        self.calls += 1
        opt_seed = (options or {}).get("seed", 0)

        instr, text = self._split_instruction_and_text(prompt)
        if instr is not None:
            # ---- hedef-model taklidi ----
            folded = instr.lower()
            cautious = ("emin" in folded) or ("kesin" in folded) or ("şüphe" in folded)
            r = _h(f"tgt::{instr}::{text}") % 1000 / 1000.0
            abst_p = 0.35 if cautious else 0.08
            if r < abst_p:
                return "Bu tweet hakkında kesin bir yargıya varamıyorum, bağlam yetersiz."
            gold = latent_label(text)
            acc = 0.93 if cautious else 0.82
            r2 = _h(f"acc::{instr}::{text}") % 1000 / 1000.0
            pred = gold if r2 < acc else ("HAYIR" if gold == "EVET" else "EVET")
            style = _h(f"sty::{text}") % 3
            if style == 0:
                return pred
            if style == 1:
                return f"{pred}."
            return f"Cevap: {pred}"

        # ---- optimize-edici taklidi (yeni talimat üretimi) ----
        rng = random.Random(f"{self.seed}:{opt_seed}:{_h(prompt) % 10**6}")
        pool = _CAUTIOUS if rng.random() < 0.45 else _PLAIN
        tmpl = rng.choice(pool)
        k = rng.randrange(10**6)
        return f"Elbette, işte yeni talimat:\n<TALIMAT>{tmpl.format(k=k)}</TALIMAT>"
