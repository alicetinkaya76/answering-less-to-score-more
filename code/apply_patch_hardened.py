#!/usr/bin/env python3
"""Sertleştirilmiş-hat testi için gerekli tek seferlik yama (fitness parser seçilebilir olur)."""
def patch(path, old, new):
    s = open(path, encoding="utf-8").read()
    if new.split("\n")[0].strip() in s and old not in s:
        print(f"atlandı (zaten yamalı): {path}"); return
    assert old in s and s.count(old) == 1, f"{path}: hedef blok yok/tekil değil"
    open(path, "w", encoding="utf-8").write(s.replace(old, new))
    print("yamalandı:", path)

patch("fg/evalharness.py",
'''        "f1_wrong_strict": m_s["f1_wrong"], "f1_adj_strict": m_s["f1_adj"],''',
'''        "f1_wrong_strict": m_s["f1_wrong"], "f1_wrong_loose": m_l["f1_wrong"],
        "f1_adj_strict": m_s["f1_adj"],''')

patch("fg/evalharness.py",
'''def fitness_value(name, res):
    if name == "excl":
        return res["f1_used_strict"]
    if name == "wrong":
        return res["f1_wrong_strict"]
    raise ValueError(f"Bilinmeyen fitness: {name!r} (geçerli: {FITNESS_NAMES})")''',
'''def fitness_value(name, res, parser="strict"):
    """parser='strict' (varsayılan) veya 'loose' (SERTLEŞTİRİLMİŞ hat rejimi)."""
    suf = "_loose" if parser == "loose" else "_strict"
    if name == "excl":
        return res["f1_used" + suf]
    if name == "wrong":
        return res["f1_wrong" + suf]
    raise ValueError(f"Bilinmeyen fitness: {name!r} (geçerli: {FITNESS_NAMES})")''')

for f in ("fg/ga.py", "fg/opro.py"):
    s = open(f, encoding="utf-8").read()
    n = s.count("fitness_value(fitness_name, res)")
    if n:
        s = s.replace("fitness_value(fitness_name, res)",
                      'fitness_value(fitness_name, res, cfg.get("fitness_parser", "strict"))')
        open(f, "w", encoding="utf-8").write(s)
    print(f"{'yamalandı' if n else 'atlandı (zaten yamalı)'}: {f}")
print("\nYama tamam. Şimdi: caffeinate -i python3 11_hardened_ga.py --seeds 11")
