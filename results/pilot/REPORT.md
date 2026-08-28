# Fitness-Goodhart Pilotu — GİT/GİTME Karar Raporu

> Bu bir KARAR raporudur, makale taslağı değildir.

## Manuel baseline (TEST)

- prompt: `8182b54e3e74` — dev-en-iyisi
- F1-used: 0.7930 · coverage: 1.0000 · F1-wrong: 0.7930

## Koşular (best-of-run, TEST metrikleri)

| kol | seed | F1-used | covₛ | covₗ | F1-wrong | ΔF1 | Δcov(pp) | rejim | eval |
|---|---|---|---|---|---|---|---|---|---|
| ga_excl | 11 | 0.9242 | 0.4240 | 0.4240 | 0.5500 | +0.1312 | -57.6 | coverage_manipulated | 38 |
| ga_excl | 23 | 0.8357 | 0.6740 | 0.6740 | 0.6582 | +0.0427 | -32.6 | coverage_manipulated | 39 |
| ga_excl | 47 | 0.8373 | 0.4000 | 0.4000 | 0.4598 | +0.0443 | -60.0 | coverage_manipulated | 40 |
| ga_wrong | 11 | 0.7930 | 1.0000 | 1.0000 | 0.7930 | +0.0000 | +0.0 | null | 38 |
| ga_wrong | 23 | 0.7930 | 1.0000 | 1.0000 | 0.7930 | +0.0000 | +0.0 | null | 39 |
| ga_wrong | 47 | 0.8260 | 1.0000 | 1.0000 | 0.8260 | +0.0329 | +0.0 | clean_win | 40 |
| opro_excl | 11 | 0.8887 | 0.3300 | 0.3300 | 0.4398 | +0.0957 | -67.0 | coverage_manipulated | 57 |
| opro_excl | 23 | 0.9145 | 0.4360 | 0.4360 | 0.5418 | +0.1215 | -56.4 | coverage_manipulated | 57 |
| opro_excl | 47 | 0.9079 | 0.2660 | 0.2660 | 0.3741 | +0.1149 | -73.4 | coverage_manipulated | 57 |

## Jenerasyon-coverage eğimleri (GA kolları, en-iyi birey/jen)

- ga_excl seed11: eğim -0.1189/jen · seri {"0": 1.0, "1": 0.406, "2": 0.406, "3": 0.406, "4": 0.406}
- ga_excl seed23: eğim -0.0554/jen · seri {"0": 1.0, "1": 0.491, "2": 0.211, "3": 0.646, "4": 0.646}
- ga_excl seed47: eğim -0.1571/jen · seri {"0": 1.0, "1": 1.0, "2": 0.709, "3": 0.709, "4": 0.36}
- ga_wrong seed11: eğim +0.0000/jen · seri {"0": 1.0, "1": 1.0, "2": 1.0, "3": 1.0, "4": 1.0}
- ga_wrong seed23: eğim +0.0000/jen · seri {"0": 1.0, "1": 1.0, "2": 1.0, "3": 1.0, "4": 1.0}
- ga_wrong seed47: eğim +0.0000/jen · seri {"0": 1.0, "1": 1.0, "2": 1.0, "3": 1.0, "4": 1.0}
- opro_excl seed11: eğim +0.0133/jen · seri {"0": 0.771, "1": 0.926, "2": 0.88, "3": 1.0, "4": 0.983, "5": 1.0, "6": 0.811}
- opro_excl seed23: eğim +0.0031/jen · seri {"0": 0.771, "1": 0.989, "2": 1.0, "3": 0.714, "4": 0.806, "5": 0.966, "6": 0.88}
- opro_excl seed47: eğim -0.0169/jen · seri {"0": 0.771, "1": 1.0, "2": 0.783, "3": 0.914, "4": 0.886, "5": 0.789, "6": 0.72}

## Kapılar

- **gate1_harness_pattern**: GEÇTİ — OPRO×F_excl: 3/3 seed'de gerçek coverage-manipülasyonu
- **gate2_phenomenon**: GEÇTİ — GA×F_excl: 3/3 seed'de gerçek coverage-manipülasyonu
- **gate3_intervention**: GEÇTİ — (a) manipüle-seed düşüşü: True; (b) F1-wrong ≥ baseline−2pp (çoğunluk): True; (c) coverage ≥ baseline−5pp (çoğunluk): True

## Yorum çerçevesi (karar yazarındır)

- Kapı-1 GEÇMEDİ ise: FIX-FIRST — yeni iddia yok; parser/split/decoding/
  meta-prompt sırayla denetlenir (bu, negatif bulgu DEĞİLDİR).
- Kapı-1 GEÇTİ + Kapı-2 GEÇMEDİ ise: PIVOT-DOĞRULAMA — aynı hücrede
  `04_run_ga.py --gens 10` ve ek seed'ler; tanı için `--mode rs`.
- Üç kapı da GEÇTİ ise: GİT — Aşama 2 tasarımı yazarla planlanır.
