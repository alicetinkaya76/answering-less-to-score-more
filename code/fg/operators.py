"""LLM tabanlı varyasyon operatörleri (EvoPrompt-tarzı) + geçerlilik/onarım.

Geçerlilik kuralı (handoff v2): her çocuk (i) Türkçe, (ii) boş değil ve uzunluk
sınırları içinde, (iii) talimat-biçimli (EVET ve HAYIR etiket uzayını anıyor) olmalı.
Başarısızsa aynı operatör en fazla max_repair_retries kez yeniden denenir; hâlâ
geçersizse çağıran taraf ebeveyn-kopyası fallback'ine düşer. GEÇERSİZ çocuklar dev'de
DEĞERLENDİRİLMEZ ve gerçekleşen-eval sayımına GİRMEZ (sayım = benzersiz dev eval).
"""

import re

from .parse import tr_fold

TAG_RE = re.compile(r"<TALIMAT>(.*?)</TALIMAT>", re.DOTALL | re.IGNORECASE)

_TR_CHARS = set("çğıöşü")
_TR_HINTS = {"ve", "bir", "bu", "için", "ise", "olarak", "cevap", "metin", "tweet",
             "yalnızca", "sadece", "değil", "olup", "olmadığını", "yaz", "ver"}
_EN_HINTS = {"the", "is", "and", "this", "answer", "with", "your", "should", "text"}


def extract_instruction(reply):
    """Optimize-edici çıktısından talimatı ayıkla: önce <TALIMAT> etiketi, yoksa gövde."""
    if not reply:
        return ""
    m = TAG_RE.search(reply)
    text = m.group(1) if m else reply
    return text.strip().strip('"').strip()


def validity(instr, cfg):
    """(ok: bool, reason: str). Nedenler loglama içindir."""
    gcfg = cfg.get("ga", {})
    lo = int(gcfg.get("child_min_chars", 10))
    hi = int(gcfg.get("child_max_chars", 600))
    if not instr or not instr.strip():
        return False, "bos"
    t = instr.strip()
    if len(t) < lo:
        return False, "cok_kisa"
    if len(t) > hi:
        return False, "cok_uzun"
    folded = tr_fold(t)
    if "evet" not in folded or "hayır" not in folded.replace("hayir", "hayır"):
        return False, "etiket_uzayi_yok"
    words = set(re.findall(r"[a-zçğıöşü]+", folded))
    tr_score = (1 if any(ch in _TR_CHARS for ch in folded) else 0) + \
               len(words & _TR_HINTS)
    en_score = len(words & _EN_HINTS)
    if tr_score < 1 or en_score >= 3:
        return False, "turkce_degil"
    return True, "ok"


def _task_desc(cfg):
    return cfg.get(
        "task_description",
        "Türkçe metinleri (EVET/HAYIR) sınıflandırma",
    )


def _op_prompt_mutation(parent, task):
    return (
        f"Aşağıdaki TALİMAT, şu görev için bir dil modeline verilecektir: {task}.\n"
        "Görevin: bu talimatın amacını koruyan ama ifadesi, vurgusu veya yapısı belirgin "
        "biçimde FARKLI, YENİ bir Türkçe talimat yazmak.\n"
        "Kurallar: yeni talimat kısa ve insan-okunur olsun; modelden YALNIZCA EVET veya "
        "HAYIR üretmesini istesin; Türkçe yaz.\n"
        "Yalnızca yeni talimatı <TALIMAT> ve </TALIMAT> etiketleri arasında ver, başka "
        "hiçbir şey yazma.\n\n"
        f"TALİMAT:\n{parent.strip()}\n"
    )


def _op_prompt_crossover(p1, p2, task):
    return (
        f"Aşağıdaki İKİ TALİMAT, şu görev için bir dil modeline verilecek "
        f"alternatiflerdir: {task}.\n"
        "Görevin: ikisinin güçlü yönlerini BİRLEŞTİREN tek bir YENİ Türkçe talimat yazmak "
        "(ikisinin kopyası olmasın).\n"
        "Kurallar: kısa ve insan-okunur olsun; modelden YALNIZCA EVET veya HAYIR üretmesini "
        "istesin; Türkçe yaz.\n"
        "Yalnızca yeni talimatı <TALIMAT> ve </TALIMAT> etiketleri arasında ver, başka "
        "hiçbir şey yazma.\n\n"
        f"TALİMAT 1:\n{p1.strip()}\n\nTALİMAT 2:\n{p2.strip()}\n"
    )


def llm_variation(kind, parents, client, cfg, seed):
    """kind: 'mut' | 'cx'. Geçerlilik + onarımlı üretim.
    Dönüş: (instr | None, retries_used, reason)."""
    task = _task_desc(cfg)
    if kind == "mut":
        meta = _op_prompt_mutation(parents[0], task)
    elif kind == "cx":
        meta = _op_prompt_crossover(parents[0], parents[1], task)
    else:
        raise ValueError(kind)

    opts_base = dict(cfg.get("optimizer_decoding", {"temperature": 0.9, "num_predict": 400}))
    model = cfg.get("optimizer_model", cfg["target_model"])
    keep = cfg.get("keep_alive", "30m")
    retries = int(cfg.get("ga", {}).get("max_repair_retries", 2))

    reason = "?"
    for attempt in range(retries + 1):
        opts = dict(opts_base)
        opts["seed"] = int(seed) + attempt  # onarım denemesi farklı örnekleme kullansın
        reply = client.generate(meta, model=model, options=opts, keep_alive=keep)
        instr = extract_instruction(reply)
        ok, reason = validity(instr, cfg)
        if ok:
            return instr, attempt, "ok"
    return None, retries, reason
