# Fitness-Goodhart Pilotu — SatireTR Sürümü (v1)

**Fikir (sabit):** EvoPrompt-tarzı talimat-GA ve OPRO, abstain-exclude fitness (F_excl)
boşluğunu istismar ediyor mu (coverage manipülasyonu)? Abstention-farkında F_wrong bunu
tasarım gereği engelliyor mu?

**Substrat (yeni):** Turkish Satirical News Dataset (SatireTR, 2024, MIT lisanslı) —
Zaytung (satirik) vs Anadolu Ajansı (gerçek) haber metinleri. OffensEval-TR tamamen
çıkarıldı; yalnız başarısızlık-tanısı yedeği olarak akılda tutulur (aşağıda).

Tamamen stdlib-Python; tek dış bağımlılık yerel Ollama. Sıfır maliyet, API yok.

## Neden bu veri seti? (karar özeti)
- 2202 satirik + 4744 kullanılabilir gerçek makale → dengeli 4370 örnek: dev 175 /
  test 500 rahat sığar (adaylar içinde istatistiksel yeterliliği tam geçen tek set).
- Tam metin + MIT lisans + anında indirme (tweet-ID rehidrasyon tuzağı yok).
- Anlatı temizliği: "bu metin satirik mi?" sorusunda kitlesel abstain açıkça iş-kaçırmadır
  (fact-checking'te abstain epistemik olarak savunulabilirdi — pilotta bulanıklık istemeyiz).
- Yerleşik zor-dilim probu: reponun stil-arındırılmış 200 satirik makalesi,
  "abstention zor örneklere mi yığılıyor?" sorusunu doğrudan test eder.
- Yedek zincir (önceden adlandırılmış): FCTR-ikili küçük hücre → IronyTR stres hücresi.

## Kurulum
1. Python ≥ 3.10 (pip GEREKMEZ).
2. `ollama serve` çalışıyor; `ollama pull qwen2.5:14b`.

## Koşu sırası
```bash
python3 -m unittest tests.test_parser tests.test_smoke   # 0) Ollama'sız hat doğrulaması
python3 00_prepare_data.py                               # 1) veriyi indir + dönüştür
python3 01_make_splits.py                                # 2) sabit dev/test indeksleri
python3 02_run_baselines.py                              # 3) KAPI 0 + SEÇMECE (GO/ADJUST)
python3 03_run_opro.py                                   # 4) KAPI 1: OPRO fenomeni
python3 04_run_ga.py --fitness excl                      # 5) KAPI 2: GA fenomeni
python3 04_run_ga.py --fitness wrong                     # 6) KAPI 3: müdahale
python3 05_report.py                                     # 7) GİT/GİTME karar raporu
python3 06_probe_hard_slice.py --arm ga_excl --seed 11   # 8) zor-dilim probu (manipüle koldaysa)
```
Tüm runner'lar `--mock` (Ollama'sız kuru koşu) ve `--seeds ...` alır. Zip'te
dönüştürülmüş veri ve sabit split'ler hazır geldiği için 00–01 atlanabilir; yeniden
üretilebilirlik için script'ler duruyor.

## Veri tasarım kararları (00_prepare_data.py)
- **Metin = gövdenin ilk ~400 karakteri, BAŞLIKSIZ.** Zaytung başlıkları en güçlü stil
  sızıntısıdır; gövde-odaklı kırpma görevi yüzeysel stil eşleştirmeden içerik/pragmatik
  yargıya kaydırır (zor-kuyruğu kalınlaştırır) ve çıkarım maliyetini düşürür.
- **Dengeli sınıflar (2185/2185, seed'li örnekleme).** Sınıf önseli burada örnekleme
  artefaktıdır; dengeli set fitness sinyalini güçlendirir.
- Yinelenen/80 karakterden kısa metinler elenir.

## Kapılar (v3 — çıpasız kurulum)
Eski tasarımda Kapı 1 "bilinen-pozitifin reprodüksiyonu" idi; OffensEval çıkınca çıpa
kalmadı. Yeni yapı:
- **KAPI 0 — makullük kalibrasyonu + SEÇMECE:** parser birim testleri + mock uçtan-uca
  (kod düzeyi) VE `02` çıktısındaki önceden-kayıtlı tatlı-bölge kontrolü:
  test coverage ≥ 0.85, dev-en-iyisi F1-used ∈ [0.55, 0.85], prompt-uyuşmazlığı ≥ 0.10.
  **GO değilse 03/04 koşulmaz** → yedek zincir tek komut: `python3 00_prepare_data.py --source fctr && python3 switch_to_fctr.py` (config'i FCTR-küçük hücreye çevirir, FCTR'ye özel M1–M8'i ve görev tanımını devreye alır) → o da olmazsa IronyTR stres hücresi.
- **KAPI 1 — OPRO fenomeni:** OPRO×F_excl ≥1/3 seed'de gerçek (artefakt-olmayan)
  coverage-manipülasyonu üretir (F1-used ↑ VE test Δcoverage < −10pp).
- **KAPI 2 — GA fenomeni** ve **KAPI 3 — sayısal müdahale** öncekiyle aynı
  (05_report.py otomatik değerlendirir).
- **Gizli tanı yedeği:** yeni sette NE OPRO NE GA manipüle ederse, harness'ı bilinen-pozitif
  OffensEval hücresinde BİR KEZ koş (yayında görünmez): desen orada çıkıyorsa harness
  sağlamdır, sorun veri setindedir (bu da bir bulgudur) → FIX-FIRST vs PIVOT ayrımı netleşir.

## Zor-dilim probu (06)
`data/satire_probe_debiased.tsv` = LLM'le stilden arındırılmış 200 satirik makale
(SatireTR reposundan). Manipüle çıkan kolun best-of-run promptu bu dilimde koşulur:
probe-coverage'ın test-coverage'dan belirgin düşük çıkması, abstention'ın zor örneklere
yığıldığını (mekanizmanın kendisini) gösterir. Not: bu 200 metin LLM-üretimidir; ana
sonuçlara karışmaz, yalnız mekanizma probudur.

## Süre bütçesi (M4 Max, qwen2.5:14b 4-bit)
Örnek başına ~2.5–3.5 sn (≈650–750 karakter girdi + 24 token çıktı) varsayımıyla:
baselines ≈ 5.4k, OPRO 3 seed ≈ 31k, GA 6 koşu ≈ 49k → toplam ≈ **86k hedef çıkarımı**
≈ tek-akışta ~60–75 saat. Sunucuda `OLLAMA_NUM_PARALLEL=4` + config'te `parallel_requests: 4` (istemci-tarafı eşzamanlı istekler, sıra-korumalı) birlikte ~3–4× hızlandırır → **~2–3 gece**. Kollar bağımsız script'ler olduğu için gecelere bölünebilir.

## Çıktı düzeni
`results/pilot/{kol}/{seed}/`: `config.json` (model digest'leri, aynı-model koşul
etiketi), `gen_log.jsonl`, `raw/`, `preds/`, `best_of_run.json`, `probe_hard_slice.json`.
Baseline+seçmece: `results/pilot/baselines/`. Rapor: `results/pilot/REPORT.md`.

## Bilinçli sapmalar / notlar
- GA seçilimi turnuva-3+2elit (PeerJ tutarlılığı); yayınlanan EvoPrompt-GA rulet+top-N →
  raporda "EvoPrompt-TARZI" adlandırması.
- OPRO bütçesi 6×8=48 aday, GA'nın ~38–47 gerçekleşen bandına bilinçli yakın.
- Hedef = optimize edici (qwen2.5:14b) → her config anlık görüntüsünde koşul etiketi.
- Operatör/OPRO meta-promptlarındaki görev tanımı `config.task_description`'dan gelir; veri seti değişiminde güncellenmelidir (switch_to_fctr.py bunu otomatik yapar).
- M1–M8 bu görev için BU pakette tanımlanmıştır (yeni sette miras prompt yoktur);
  manuel-baseline = dev-en-iyisi.
