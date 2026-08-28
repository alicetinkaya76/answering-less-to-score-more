# DOĞRULAMA RAPORU — HANDOVER.md ↔ arşiv (fg_pilot.zip)

Tarih: 15 Temmuz 2026 · Araç: `analysis.py` (saf stdlib; arşivdeki `preds/`, `gen_log.jsonl`,
`best_of_run.json`, `summary.json` dosyalarından yeniden hesap) · Ham çıktı: `verification.json`

> **2026-08-27 düzeltme notu — bu rapor tarihsel kayıttır, olduğu gibi bırakıldı.**
> Aşağıdaki "70 kontrol" sayısı o günkü betiğe aittir; betik sonradan büyümüş, sayı
> güncellenmemişti. `analysis.py` bugün **105 kontrol** koşuyor. Aşağıdaki 4 bulgunun
> hepsi ele alındı ve betik artık **105/105 geçiyor**: bulgu 1'in beklenen değerleri
> makalenin kendi rakamlarına çekildi (F_excl 3→2, F_wrong 6→1), bulgu 3'te ise kontrol
> gövdesi §4'ün yazdığı tanıma (sekiz prompt'un **hepsi cevapladı VE hepsi yanlışladı**)
> uyarlandı → 59/58. O günkü ham çıktı `verification_2026-07-15.json` olarak korunuyor;
> güncel çıktı `verification.json`. Ayrıntı: `REPRODUCTION.md`.

## Sonuç: 70 kontrol → 66 BİREBİR GEÇTİ, 4 tanımsal bulgu

Geçenler (özet): ana tablo 9 koşunun tamamı (F1-used / coverage / F1-wrong), manuel M1–M8
tablosu, uyuşmazlık 74/175, erken sinyal (M1 dev 0.8078 @ %22.9 cevapsız), ileri ablasyon 6/6
(coverage ve F1'ler), ters ablasyon 4/4 (Δcov ve ΔF1), bütçe np=256 5/5 + M2 bit-özdeşliği,
**merkez tablo "gerçek F1" değerleri preds'ten birebir yeniden üretildi**
(0.7930 / 0.8240 / 0.8135 / 0.7550 / 0.7320), sertleştirilmiş koşuların dev-fitness ve test
gerçek-F1'leri, yeniden-puanlama karşıolgusalı (katı seçim cov 0.606/0.691/0.800 vs gevşek
0.937/0.863/1.000 — **havuz düzeyinde**, yalnız-son-jenerasyon değil), 7B hedef (0/3; 2 seed
düz 0.7998; baseline 0.7613), F_wrong kalibrasyonu (ort |Δ| = 0.0768 ≈ 0.077), uygunluk
manzarası binleri (0.687/0.799/0.881), en iyi dürüst iyileşme (+0.0077 ≈ +0.008), düzeltilmiş
OPRO yörüngesi (s11: 1.00 → 0.371 → 0.326), sınıf-seçici abstention (0.180 / 0.620),
cevapsız-anatomi medyanı (11 kelime).

## 4 tanımsal bulgu (makalede nasıl ele alınmalı)

1. **"F_wrong altında 6 dürüst-iyileşme, F_excl altında 3" — YENİDEN ÜRETİLEMEDİ.**
   Arşivde "6", tek bir benzersiz promptun (seed47'nin 0.8514 kazananı) elit olarak
   jenerasyonlar boyunca **6 kez loglanması**; benzersiz sayım 1'dir. F_excl tarafında hiçbir
   eşik tanımı 3 vermiyor (cov ≥ 0.95'te 2 benzersiz aday, en iyisi +0.0077; GA-excl tek başına
   0). **Öneri:** makalede bu cümleyi düşür ya da yeniden-üretilebilir haliyle değiştir:
   "cov ≥ 0.95 adaylar içinde baseline'ı geçen benzersiz aday: F_excl altında 2 (en iyisi
   +0.008; ikisi de OPRO'dan, GA hiç görmedi); F_wrong altında arama 1 gerçek iyileşme buldu
   (dev +0.041) ve sonuna dek elit tuttu."

2. **Cevapsız anatomi "%98'i kesik":** yeniden hesap **%96.4–96.8** (noktalama kümesine göre:
   {.!?…»"'} → 96.4; {.!?} → 96.8). Medyan 11 kelime ✓, açık ret %0–1 ✓. **Öneri:** makalede
   "≈%96–97'si cümle-sonu noktalaması olmadan bitiyor (bütçe ortasında kesilme)" yaz; iddia
   değişmiyor.

3. **"Sert çekirdek 58/59" tanımı netleşti:** 8 manuel promptun **hepsinin cevapladığı VE
   hepsinin yanlışladığı** test örnekleri = 59 (58'i satirik) ✓. ("Cevapsızı yanlış say"
   tanımı 75 verir — makalede tanımı açıkça bu şekilde yazmak gerek.)

4. **Eval sayısı etiketleri:** kurulum satırındaki "6×8 = 56" ve "37–40" yerine arşivdeki
   gerçekleşen benzersiz değerlendirmeler: **OPRO 57/57/57 · GA 38/39/40** (ga_wrong aynı;
   sertleştirilmiş 38/39/39; 7B 38/39/39). Merkez tablodaki "(40 eval)" etiketi ga_excl/11
   için gerçekte **38**. Makale metni ve figür etiketleri 38/57 kullanıyor.

## Açık soruların cevapları (önceki üç mikro-soru)

- **Ondalık:** onay gelmediği için önerilen kural uygulandı — tablolar 4, düzyazı 3, pp 1 ondalık.
- **Eval sayıları:** yukarıda (bulgu 4).
- **"np=256'da katı cov 0.920 → +0.022 artık artefakt" referansı:** sertleştirilmiş koşunun
  **seed-11 kazananı** (test): katı cov 0.920, katı−gevşek F1 farkı **+0.0220**. Diğer seed'ler:
  s23 → 0.858 / +0.0125; s47 → 1.000 / 0.000. Makalede "en kötü durumda (s11) +0.022" diye
  refere edilecek.

## Bonus doğrulamalar (metin ifadeleri için)

- GA çöküşü seed'e özgü zamanlama: s11 gen-1'de (1.00 → 0.406; fitness 0.811 → 0.930 ✓
  HANDOVER'daki cümle s11'i anlatıyor), s23 kısmi (0.491), s47 gen-2'de (1.00 → 0.709 → 0.36).
  Metinde "en erken 1. jenerasyonda" denmeli.
- REPORT.md'deki OPRO jenerasyon serileri bilinen hatalı izleme (adımın İLK adayı); düzeltilmiş
  en-iyi-aday serileri: s11 {1.00, 0.371, 0.326, 0.48, 0.56, 0.874, 0.863},
  s23 {1.00, 0.571, 0.857, 0.509, 0.897, 0.543, 0.463}, s47 {1.00, 0.451, 0.417, 0.297, 0.60,
  0.503, 0.554}. (Dürüstlük kaydı madde 2 ile uyumlu.)
- Kapı tanımları (REPORT.md): gate1 = OPRO×F_excl 3/3 manipülasyon; gate2 = GA×F_excl 3/3;
  gate3 = F_wrong müdahalesi (manipüle-seed düşüşü + F1-wrong ≥ baseline−2pp çoğunluk +
  coverage ≥ baseline−5pp çoğunluk). Üçü de GEÇTİ → GİT.
- GA başlangıç popülasyonu (kaynak kod): 8 manuel prompt + LLM ile 10'a tamamlama.
- Batarya vektörleri (kaynak kod): V0 = M2 kontrol; V1 = M2 − format kısıtı; V2 = M2 +
  "yalnızca kesin eminsen … emin değilsen cevap verme"; V3 = M2 − kısıt + "önce gerekçeni yaz";
  V4 = opro_excl/47 kazananı; V5 = ga_excl/11 kazananı. SÖMÜRÜLEBİLİR ⇔ en az bir vektörde
  Δcov < −10pp VE ΔF1 > 0 (n = 300).
