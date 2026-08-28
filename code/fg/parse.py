"""Katı ve gevşek etiket ayrıştırıcılar.

Sözleşme (coverage-audit protokolüyle uyumlu):
- KATI parser fitness/coverage'ın resmi kaynağıdır: cevap İLK SATIRDA ve tekil olmalı.
- GEVŞEK parser yalnız teşhis içindir (parser-artefaktı vs gerçek manipülasyon ayrımı):
  tüm metni tarar, biçim gürültüsüne gömülü cevabı kurtarmaya çalışır.
- Her ikisi de belirsizlikte (iki etiket birden / hiç etiket yok) None (abstain) döndürür;
  gevşekte iki etiket birden görülürse İLK geçen kazanır (kurtarma amaçlı).

Türkçe normalizasyon: 'İ'->'i', 'I'->'ı' sonra lower() (casefold Türkçe'de I/İ'yi bozar).
"""

import re

DEFAULT_LEXICON = {
    "EVET": ["evet"],
    "HAYIR": ["hayır", "hayir"],
}

_PREFIXES = ("cevap", "yanıt", "yanit", "etiket", "sonuç", "sonuc", "karar", "answer", "label")


def tr_fold(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def _tokens(s):
    return re.findall(r"[0-9a-zçğıöşü]+", tr_fold(s))


def _label_of_token(tok, lexicon):
    for label, forms in lexicon.items():
        if tok in forms:
            return label
    return None


def strict_parse(text, lexicon=None):
    """İlk anlamlı satırda TEK etiket ara; iki etiket ya da hiç etiket -> None."""
    lexicon = lexicon or DEFAULT_LEXICON
    if not text:
        return None
    first = ""
    for ln in text.splitlines():
        if ln.strip():
            first = ln.strip()
            break
    if not first:
        return None
    toks = _tokens(first)
    # "cevap: evet" gibi öneklerin arkasına bakabilmek için önek sözcükleri düşülür
    toks = [t for t in toks if t not in _PREFIXES]
    found = []
    for t in toks:
        lab = _label_of_token(t, lexicon)
        if lab and lab not in found:
            found.append(lab)
    return found[0] if len(found) == 1 else None


def loose_parse(text, lexicon=None):
    """Tüm metni tara; ilk geçen etiketi döndür (kurtarma). Hiç yoksa None."""
    lexicon = lexicon or DEFAULT_LEXICON
    if not text:
        return None
    folded = tr_fold(text)
    best_pos, best_label = None, None
    for label, forms in lexicon.items():
        for form in forms:
            for m in re.finditer(r"(?<![0-9a-zçğıöşü])" + re.escape(form) + r"(?![0-9a-zçğıöşü])",
                                 folded):
                if best_pos is None or m.start() < best_pos:
                    best_pos, best_label = m.start(), label
    return best_label


def parse_both(text, lexicon=None):
    s = strict_parse(text, lexicon)
    l = loose_parse(text, lexicon)
    # gevşek, katının üst kümesidir: katı bulduysa gevşek de en az onu bulur
    if s is not None and l is None:
        l = s
    return s, l
