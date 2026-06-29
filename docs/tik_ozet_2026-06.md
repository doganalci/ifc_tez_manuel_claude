# Tez İzleme Komitesi — Ara Dönem İlerleme Özeti
**Konu:** IFC/BIM modelleri üzerinde yapı kuralı (yönetmelik) ihlallerinin
sentetik üretimi, görselleştirilmesi ve makine öğrenmesi için etiketli veri
hazırlığı
**Dönem:** 2026 — manuel, adım adım yeniden inşa edilen lokal sürüm

---

## 1. Çalışmanın amacı ve kapsamı

Tezin temel hedefi, bina bilgi modelleri (IFC/BIM) üzerinde **yapı kuralı
ihlallerini otomatik tespit edebilen** yöntemler geliştirmek ve bunun için
**kontrollü, etiketli (ground-truth) bir veri üretim hattı** kurmaktır. Gerçek
projelerde "doğru cevabın" (hangi elemanın hangi kuralı ihlal ettiği) bilinmemesi,
denetimli öğrenme için en büyük engeldir. Bu nedenle çalışmada **sentetik ama
gerçekçi** binalar üretilip, üzerlerine **bilinen ihlaller** enjekte edilerek,
modelin başarısının nesnel ölçülebileceği bir zemin oluşturulmaktadır.

Bu dönemde sistemin **çekirdek hattı uçtan uca** kuruldu: baseline (kurala uygun)
bina üretimi → kural seti ve otomatik tespit → ihlal enjeksiyonu (etiketli) →
görselleştirme. Çalışma bilinçli olarak **modüler** (her mantık `src/` altında
fonksiyon) ve **adım adım gösterilebilir** (her aşama ayrı Jupyter notebook)
biçimde tasarlandı.

---

## 2. Genel mimari ve yöntem

- **Kod ↔ veri ayrımı:** Üretici kod (`src/`) ile üretilen dinamik veri (`data/`)
  birbirinden ayrıldı. Üretilen IFC dosyaları, etiketler ve loglar versiyon
  kontrolüne girmez; sadece kod ve dokümantasyon paylaşılır. Bu, hem tekrar
  üretilebilirliği hem de veri-kod karışıklığının önlenmesini sağlar.
- **Modülerlik:** Tüm üretim/analiz mantığı yeniden kullanılabilir Python
  fonksiyonlarıdır; notebook'lar bunları yalnızca **çağırır**. Örneğin bina
  üreten motor (`layout_to_ifc`), hem baseline üretiminde hem ihlal eklemede
  aynen kullanılır — yani kural motoru tek ve tutarlı bir kaynaktır.
- **Teknik temel:** IFC kütüphanesi olarak **ifcopenshell 0.8.x** yüksek seviye
  API; birim **metre**; şema doğrulaması ve geometri üretimi her adımda kontrol
  edilir.

---

## 3. Tamamlanan modüller ve elde edilen sonuçlar

### 3.1 Kural tabanlı (motorlu) baseline IFC üretimi
Yönetmeliklere uygun, ihlalsiz binaların deterministik üretimi. İki üretici:

1. **Basit üretici** (`medium_layout` → `build_baseline`): 1 kat, 3 oda, giriş +
   iç kapılar, pencereler, döşeme ve mekânlar. Modüler fonksiyon mantığını ve
   uçtan uca üretimi gösterir.
2. **Parametrik üretici** (`procedural.generate_baselines`): Tez için asıl üretici.
   Topoloji: **dikdörtgen veya kare bina**; üstte **3 oda**, ortada **koridor**,
   altta **salon** (toplam 5 mekân). Parametreler:
   - oda başına kapı sayısı (varsayılan 3)
   - oda min/maks boyutları (varsayılan 3–5 m)
   - koridor genişlik/uzunluk aralığı (varsayılan 3–5 m)
   - bina biçimi: dikdörtgen / kare
   - üretilecek **farklı varyant sayısı** (tek konfigürasyondan N adet)

**Sonuç (doğrulanmış):** Üretilen her IFC modeli **IFC4 şemasına %100 uygun**
(doğrulayıcı 0 hata), **geometrisi eksiksiz** (tüm elemanlar çizilebilir) ve
**tüm kuralları sağlar** (otomatik tespit → 0 ihlal). Tek konfigürasyondan,
seed ile tekrar üretilebilir, birbirinden farklı çok sayıda baseline elde
edilebilir — yani **ölçeklenebilir bir veri seti üreticisi** kuruldu.

### 3.2 Kural seti ve otomatik tespit
Tez kapsamında ölçülebilir, eşik tabanlı kurallar tanımlandı (parametrik):
- **R1 — Minimum kapı net genişliği:** iç kapı ≥ 0.90 m, giriş ≥ 1.00 m
- **R2 — Pencere/taban alanı oranı (doğal aydınlatma):** ≥ %10 (koridor/sirkülasyon
  mekânları muaf)
- **R3 — Minimum net kat yüksekliği:** ≥ 2.40 m
- **R4 — (planlandı):** araştırmacının ekleyeceği kural (henüz tanımsız)

Aynı modül hem **ölçüm/tespit** (`detect`) hem de ihlal üretiminde eşik kaynağı
olarak kullanılır. Eşikler parametrik olduğundan, ileride eğitim/test setlerinde
**eşik perturbation** gibi deneyler mümkündür.

### 3.3 Kural tabanlı ihlal ekleme — etiketli veri üretimi
Baseline'a deterministik ihlaller enjekte edilerek **ground-truth etiketli**
"violated" modeller üretilir. Üç kavram ayrıştırıldı:
- 🔴 **İhlal (violation):** kuralı gerçekten bozan geometri değişimi (ör. kapıyı
  0.70 m'ye daraltmak, bir odanın penceresini kaldırmak).
- 🟡 **Sahte ihlal (decoy):** "ihlal" etiketi taşıyan ama aslında kurala uygun
  eleman — modelin **yanlış pozitif** eğilimini sınamak için.
- 🟢 **Uyumlu ekleme (compliant):** kural bozmayan yeni eleman (ör. süs kolon) —
  modelin "her değişikliği ihlal sanma" hatasını sınamak için.

Her üretim, yanında bir `meta.json` (etiket dosyası: hangi eleman, hangi durum,
hangi kural, ölçülen değer) ile saklanır.

**Sonuç (doğrulanmış — tezin en kritik bulgusu):** Üretilen violated model bağımsız
tespit motorundan geçirildiğinde, **enjekte edilen gerçek ihlaller birebir geri
bulunuyor**; decoy ve compliant elemanlar ihlal olarak işaretlenmiyor.
Yani **ground-truth ↔ otomatik tespit tam tutarlı**. Bu, veri üretim hattının
güvenilir ve denetimli öğrenme için kullanılabilir olduğunu kanıtlar.

### 3.4 Görselleştirme modülü
Girdi bir IFC dosyası; çıktı **eşzamanlı senkron** üç görünüm:
- **3D model** (döndür/yakınlaştır, elemana tıkla)
- **Graph** (eleman = düğüm, ilişkiler = kenar; düğümler sürüklenebilir)
- **IFC metni** (ilgili STEP satırları vurgulanır)

Bir görünümde seçilen eleman, ortak anahtar (**GlobalId**) üzerinden diğer iki
görünümde de anında renk değiştirir; "seçimi kaldır" sıfırlar. Ek olarak:
seçilen elemanın **detay paneli** (tip, boyut, özellik setleri, ilişkiler), **tam
ekran** modu ve **ihlal renk katmanı** (🔴/🟡/🟢) bulunur. Bu modül, üretilen
veriyi ve etiketleri **görsel olarak denetlemeyi** sağlar — tez savunmasında ve
hata ayıklamada doğrudan kullanılabilir.

---

## 4. Sonuçlar nerede? (çıktı konumları)

| İçerik | Konum | Not |
|--------|-------|-----|
| Üretici kod (modüller) | `src/ifc_gen/`, `src/viewer/` | versiyonlu |
| Gösterim notebook'ları | `notebooks/faz1_1_*`, `faz3_1_*`, `faz4_*` | her aşama ayrı |
| **Üretilen baseline IFC'ler** | `data/baseline_ifc/*.ifc` (+ `.meta.json`) | lokal, dinamik |
| **Üretilen ihlalli IFC'ler + etiketler** | `data/violated_ifc/*.ifc` (+ `.meta.json`) | lokal, dinamik |
| Sıralı plan + akış diyagramı | `docs/akis_diyagrami.md` | ilerleme tablosu |
| Kural seti tanımları | `docs/kural_seti.md` | R1/R2/R3 (+R4) |
| Proje rehberi | `CLAUDE.md`, `README.md` | bağlam/kurulum |

> Notebook'lar **Run All** ile çalıştırıldığında veriyi yeniden üretir; üretilen
> IFC ve etiketler `data/` altına yazılır (paylaşıma girmez, tekrar üretilebilir).

---

## 5. Hangi sonuçları kullanabilirsiniz ve ne anlama geliyor?

Komitede sunulabilecek somut, doğrulanmış çıktılar:

1. **Kurala uygun baseline üretimi.** "Sentetik ama geçerli ve yönetmeliğe uygun
   bina üretebiliyoruz" — şema 0 hata, geometri tam, 0 kural ihlali. Bu, hattın
   **temiz başlangıç noktası** (negatif örnekler) sağladığı anlamına gelir.
2. **Ölçeklenebilir, parametrik veri seti.** Tek konfigürasyondan çok sayıda farklı
   bina. Bu, ileride makine öğrenmesi için **gereken hacimde ve çeşitlilikte veri**
   üretilebileceği anlamına gelir.
3. **Etiketli ihlal verisi (ground-truth).** Hangi elemanın hangi kuralı ihlal
   ettiği **kesin biliniyor**. Bu, denetimli öğrenmenin temel şartıdır ve gerçek
   veride bulunmayan en değerli unsurdur.
4. **Tespit ↔ etiket tutarlılığı.** Bağımsız kural motoru, enjekte edilen ihlalleri
   birebir geri buluyor. Bu, hem **veri kalitesinin** hem de kuralların
   **doğru biçimlendirildiğinin** kanıtıdır; aynı zamanda ileride öğrenilecek
   modeller için bir **referans (baseline) tespit başarısı** sağlar.
5. **Decoy / compliant kavramları.** Modelin yalnızca "ihlali bulması" değil,
   **yanlış alarm vermemesi** de ölçülebilir. Bu, literatürdeki etiket sızıntısı /
   yanlış pozitif sorununa karşı tezin **metodolojik bir katkısıdır**.
6. **Senkron görselleştirme.** Üretilen veri ve tahminler 3D + graph + IFC üzerinde
   birlikte denetlenebilir — savunma sunumunda güçlü bir görsel araç.

---

## 6. Yöntemsel katkı ve tez açısından önemi

- Kural motoru **hem üretici hem doğrulayıcı** olarak kullanılarak iç tutarlılık
  garanti edildi (üretilen ihlal, bağımsız tespitle örtüşüyor).
- Veri **graf yapısına** doğal biçimde dönüştürülebiliyor (eleman = düğüm, ilişki =
  kenar). Bu, sonraki adımda **graf tabanlı öğrenme** (ör. GAT) için zemin hazırlar.
- Decoy/compliant tasarımı, modeli yalnızca doğruluk değil **dayanıklılık** açısından
  da sınamayı mümkün kılar.
- Tüm hat **tekrar üretilebilir** (seed, modüler kod, doğrulama adımları) ve
  **şeffaf** (her adım ayrı notebook'ta gösteriliyor).

---

## 7. Sıradaki adımlar (planlanan)

1. **R4 kuralının tanımlanması** (ör. kaçış/engel, koridor genişliği, rampa eğimi).
2. **LLM tabanlı üretim hattı:**
   - Faz 1.2 tamamen LLM ile baseline, 1.3 hibrit (LLM + motor)
   - Faz 2 ihlal havuzu (LLM / LLM+doküman / RAG / RAG+LLM)
   - Faz 3.2–3.4 LLM'li ihlal ekleme
3. **Makine öğrenmesi:** üretilen etiketli graf verisi üzerinde tespit modeli
   (graf sinir ağları) eğitimi ve decoy/compliant dahil değerlendirme.

---

## 8. Tekrar üretilebilirlik / teknik altyapı

- Ortam: `conda env create -f environment.yml` (ifcopenshell, jupyterlab, pythreejs,
  ipycytoscape, vb.).
- Çalıştırma: ilgili notebook'u **Run All** — veriyi `data/` altına üretir.
- Doğrulama: her notebook üretimi şema/geometri/kural kontrolünden geçirir.
- Sürüm yönetimi: kod versiyonlu; dinamik veri (`data/`, notebook çıktıları)
  ayrı tutulur (`nbstripout` ile notebook çıktıları otomatik temizlenir).
