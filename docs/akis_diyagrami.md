# Akış Diyagramı — IFC Üretimi (Manuel, Adım Adım)

Bu belge, lokalde **adım adım** ilerleyeceğimiz işin sıralı planıdır. Aşağıda
önce **genel akış**, sonra her modülün **alt akışı** var. Her kutu = ayrı bir
adım. Bir adımı bitirip onaylamadan diğerine geçmiyoruz.

> Kapsam (şimdilik SADECE bunlar):
> 1. Baseline IFC üretimi
> 2. İhlal havuzu üretme
> 3. Baseline'a ihlal ekleme
> 4. Görüntüleme modülü
>
> GAT eğitimi, performans analizi vb. **bu turda yok.**
>
> **Çalışma tarzı:** Tek bir arayüz YOK. Her adımı **Jupyter notebook**'ta tek tek
> yapıp gösteriyoruz (`notebooks/`). Motorlar `src/` altında, notebook'lar onları
> import edip çalıştırır.
>
> **Sıra notu:** Faz 1.1 motoru (baseline IFC) hazır olunca, viewer'a girdi
> oluştuğu için **Faz 4 (görselleştirme) öne alındı** ve yapıldı. Kalan üretim
> yöntemleri sırayla devam edecek.

---

## 0. Genel Akış (bağımlılık sırası)

`öncelikle ifc üretimi yapacağız` dediğin için sıralama, bağımlılıklara göre
şöyle: önce ortada bir bina (baseline) olmalı; sonra ihlal havuzu; sonra
ihlalleri binaya enjekte; en sonda hepsini görselleştiren viewer.

```mermaid
flowchart TD
    P0["FAZ 0\nProje iskeleti + data/ ayrımı\n(repo ↔ dinamik veri)"]
    P1["FAZ 1\nBaseline IFC Üretimi\n(kurallara uygun bina)"]
    P2["FAZ 2\nİhlal Havuzu Üretme\n(sözel ihlal kataloğu)"]
    P3["FAZ 3\nBaseline'a İhlal Ekleme\n(baseline + havuz → violated IFC)"]
    P4["FAZ 4\nGörüntüleme Modülü\n(3D + graph + IFC eşzamanlı)"]

    P0 --> P1
    P1 --> P2
    P1 --> P3
    P2 --> P3
    P1 --> P4
    P3 --> P4
    P2 -. etiket bilgisi .-> P4

    classDef done fill:#bbf7d0,stroke:#16a34a,color:#000;
    classDef now  fill:#fde68a,stroke:#d97706,color:#000;
    class P0 done;
    class P1 now;
```

**Durum:** FAZ 0 bitti (bu commit). Sıradaki: **FAZ 1 — Baseline IFC Üretimi.**

---

## FAZ 1 — Baseline IFC Üretimi

Amaç: kurallara uygun, ihlalsiz bir bina IFC'si üretmek. 3 yöntemi sırayla
yapıp karşılaştıracağız.

```mermaid
flowchart TD
    A["Girdi: bina parametreleri\n(kat sayısı, oda, kapı/pencere, ölçüler)"]

    subgraph M1["1.1 Kural tabanlı (motorlu)"]
      A --> B1["Geometri/IFC motoru\n(ifcopenshell ile deterministik)"]
      B1 --> C1["baseline_ifc/*.ifc"]
    end

    subgraph M2["1.2 Tamamen LLM (motorsuz)"]
      A --> B2["LLM doğrudan IFC metni üretir"]
      B2 --> V2{"IFC geçerli mi?\n(schema validate)"}
      V2 -- "hayır" --> B2
      V2 -- "evet" --> C2["baseline_ifc/*.ifc"]
    end

    subgraph M3["1.3 Hibrit (LLM + motor)"]
      A --> B3["LLM yüksek seviye plan/parametre üretir"]
      B3 --> B3b["Motor planı geçerli IFC'ye çevirir"]
      B3b --> C3["baseline_ifc/*.ifc"]
    end

    C1 --> OUT["data/baseline_ifc/ + meta.json (yöntem, parametre, zaman)"]
    C2 --> OUT
    C3 --> OUT
```

Sıra: **1.1 → 1.2 → 1.3.** Her biri ayrı adım, ayrı onay.

---

## FAZ 2 — İhlal Havuzu Üretme

Amaç: yönetmelik/kural ihlallerinin **sözel** kataloğu (henüz IFC değişmez).
4 yöntem:

```mermaid
flowchart TD
    subgraph G1["2.1 LLM ile"]
      L1["LLM'e: 'tipik ihlalleri listele'"] --> P1o["ihlal havuzu (JSON)"]
    end

    subgraph G2["2.2 LLM + Doküman"]
      D2["Yönetmelik dokümanı (context)"] --> L2["LLM dokümandan ihlal türetir"]
      L2 --> P2o["ihlal havuzu (JSON)"]
    end

    subgraph G3["2.3 RAG ile"]
      C3["RAG corpus → ChromaDB"] --> R3["retrieve: ilgili kural parçaları"]
      R3 --> P3o["kural→ihlal eşlemesi (JSON)"]
    end

    subgraph G4["2.4 RAG + LLM"]
      C4["ChromaDB retrieve"] --> L4["LLM çekilen kuralları\nihlal senaryosuna dönüştürür"]
      L4 --> P4o["zengin ihlal havuzu (JSON)"]
    end

    P1o --> POOL["data/violation_pool/*.json\n(her ihlal: kural, açıklama, hedef eleman tipi, şiddet)"]
    P2o --> POOL
    P3o --> POOL
    P4o --> POOL
```

Sıra: **2.1 → 2.2 → 2.3 → 2.4.**

---

## FAZ 3 — Baseline'a İhlal Ekleme

Amaç: baseline IFC + ihlal → `violated` IFC. Hangi ihlalin nereye uygulandığı
**etiket** olarak saklanır (viewer ve sonraki ML için ground-truth).

```mermaid
flowchart TD
    IN["Girdi: baseline IFC"]

    subgraph J1["3.1 Kural tabanlı (motorlu)"]
      IN --> E1["Motor: kuralı bozacak\ndeterministik düzenleme"]
    end
    subgraph J2["3.2 Tamamen LLM (motorsuz)"]
      IN --> E2["LLM doğrudan IFC'yi düzenler"]
      E2 --> VV{"geçerli IFC?"}
      VV -- hayır --> E2
    end
    subgraph J3["3.3 Hibrit (LLM + motor)"]
      IN --> E3["LLM neyi/nasıl bozacağını söyler"]
      E3 --> E3b["Motor güvenli şekilde uygular"]
    end
    subgraph J4["3.4 Havuzdan seç
    → LLM → LLM+motor"]
      POOLIN["İhlal havuzundan ihlal seç"] --> E4["LLM ihlali somutlaştırır"]
      IN --> E4
      E4 --> E4b["Motor uygular"]
    end

    E1 --> TAG["Etiketleme:\n• uygulanan ihlaller\n• decoy (sahte etiket, IFC değişmez)\n• compliant addition (kural bozmayan ekleme)\n• atlanan"]
    VV -- evet --> TAG
    E3b --> TAG
    E4b --> TAG
    TAG --> OUT["data/violated_ifc/*_violatedN.ifc + meta.json"]
```

Sıra: **3.1 → 3.2 → 3.3 → 3.4.**

---

## FAZ 4 — Görüntüleme Modülü

Girdi: bir IFC dosyası. Çıktı: 3D model + graph + IFC metni, **üçü senkron**.

```mermaid
flowchart TD
    IFCIN["Girdi: IFC dosyası\n(+ varsa ihlal/etiket meta.json)"]
    IFCIN --> PARSE["Parse: elemanlar + ilişkiler"]
    PARSE --> V3D["3D model görünümü"]
    PARSE --> VGR["Graph görünümü\n(node = eleman, taşınabilir)"]
    PARSE --> VTX["IFC metin görünümü\n(satırlar)"]
    PARSE --> VHL["İhlal katmanı:\n🔴 gerçek ihlal\n🟡 decoy (sahte)\n🟢 uyumlu ekleme"]

    SEL(("Seçim olayı\n(herhangi bir görünümden)"))
    V3D <--> SEL
    VGR <--> SEL
    VTX <--> SEL
    SEL --> SYNC["Senkron vurgu:\nseçilen eleman 3 görünümde de renk değiştirir.\n'Seçimi kaldır' → renk sıfırlanır."]
    VHL --> SYNC
```

**Etkileşim kuralı:** graph'ta bir node'a tıkla → o node, 3D'deki eleman ve
IFC'deki ilgili satırlar renk değiştirir. Başka node → güncellenir. "Seçimi
kaldır" → sıfırlanır. Aynısı 3D'den ve IFC satırından tıklayınca da çalışır
(çift yönlü).

---

## İlerleme Takibi

| Faz | Adım | Durum | Notebook / Modül |
|-----|------|-------|------------------|
| 0 | Proje iskeleti + `data/` ayrımı | ✅ Bitti | — |
| 1 | 1.1 Kural tabanlı baseline (metre, kurallara uygun) | ✅ Bitti | `src/ifc_gen/baseline/` |
| 4 | Görüntüleme modülü (3D+graph+IFC senkron, detay paneli, tam ekran) | ✅ Bitti | `notebooks/faz4_gorsellestirme.ipynb` |
| 4 | İhlal/decoy/compliant renk katmanı (🔴/🟡/🟢) | ✅ Bitti | `view(..., labels=meta.json)` |
| — | Kural seti (R1/R2/R3) + tespit | ✅ Bitti | `docs/kural_seti.md`, `src/ifc_gen/inject/rules.py` |
| 3 | 3.1 Kural tabanlı ihlal ekleme | ✅ Bitti | `notebooks/faz3_1_kural_tabanli_ihlal.ipynb` |
| 1 | 1.2 Tamamen LLM baseline | ⬜ Sırada | — |
| 1 | 1.3 Hibrit baseline | ⬜ | — |
| 2 | 2.1 LLM ihlal havuzu | ⬜ | — |
| 2 | 2.2 LLM+doküman ihlal havuzu | ⬜ | — |
| 2 | 2.3 RAG ihlal havuzu | ⬜ | — |
| 2 | 2.4 RAG+LLM ihlal havuzu | ⬜ | — |
| 3 | 3.2 Tamamen LLM ihlal ekleme | ⬜ | — |
| 3 | 3.3 Hibrit ihlal ekleme | ⬜ | — |
| 3 | 3.4 Havuzdan seç → LLM → motor | ⬜ | — |
| — | R4 (kullanıcı kuralı) — `docs/kural_seti.md` placeholder | ⬜ | — |

> Her adım bittiğinde bu tabloyu güncelleyip commit/push edeceğiz.
