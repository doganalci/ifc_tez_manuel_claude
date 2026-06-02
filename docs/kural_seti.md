# Kural Seti — Taslak v0.1 (tartışmaya açık)

İhlal / sahte ihlal (decoy) / uyumlu ekleme üretiminin temeli. Her kural:
**ölçülebilir bir eşik** + **IFC'den nasıl ölçülür** + **nasıl ihlal edilir** +
decoy/compliant notu. Eşikler **parametrik** (config'ten gelir) ki ileride
train/test'te eşik perturbation yapılabilsin.

> Durum: kurallar **netleştiriliyor**, henüz kod yazılmadı. Seçilenler: R1, R2, R3.
> R4 = senin eklemek istediğin kural (aşağıda placeholder).

## Ortak kavramlar

| Etiket | Anlam | IFC değişir mi? |
|--------|-------|-----------------|
| 🔴 `violation` | Kuralı bozan gerçek geometri | Evet |
| 🟡 `decoy` | "İhlal" denmiş ama eleman kurala uygun | Hayır |
| 🟢 `compliant` | Kural bozmayan yeni ekleme | Evet (ekleme) |

Her üretimde yanına `*.meta.json` yazılır:
```json
{
  "source_baseline": "baseline_rule_20260602_193630.ifc",
  "method": "rule_based",
  "rules_config": { "...eşikler..." },
  "annotations": [
    {"ekey": "<GlobalId>", "status": "violation",
     "rule": "R1_min_door_width", "detail": "0.70 m < 0.90 m"}
  ]
}
```

---

## R1 — Minimum kapı net genişliği

| Alan | Tanım |
|------|-------|
| **Eşik** | İç kapı ≥ **0.90 m**, dış/giriş kapısı ≥ **1.00 m** (parametrik) |
| **Ölçüm** | `IfcDoor.OverallWidth` (net geçiş). İç/dış ayrımı: kapının bağlı olduğu duvarın `Pset_WallCommon.IsExternal` |
| **İhlal üretimi** | Seçilen kapının genişliğini eşik altına indir (ör. 0.70 m); hem kapı temsili hem duvar boşluğu güncellenir → 🔴 |
| **Decoy** | Genişliği uygun bir kapıyı "ihlal" etiketle, geometriye dokunma → 🟡 |
| **Compliant** | Eşiğe uygun yeni bir iç kapı ekle → 🟢 |
| **Tespit kuralı** | `OverallWidth < eşik` |

## R2 — Pencere / taban alanı oranı (doğal aydınlatma)

| Alan | Tanım |
|------|-------|
| **Eşik** | Oda pencere alanı toplamı ≥ taban alanının **%10'u** (parametrik) |
| **Ölçüm** | Odaya ait pencerelerin Σ(`OverallWidth × OverallHeight`) / oda taban alanı. Oda↔pencere eşlemesi viewer'daki `bounds` ilişkisinden |
| **İhlal üretimi** | Bir odanın penceresini sil ya da küçült → oran eşik altına düşsün → 🔴 (etkilenen oda + pencere) |
| **Decoy** | Oranı yeterli bir odayı "ihlal" etiketle → 🟡 |
| **Compliant** | Uygun boyutta ek pencere koy (oran zaten/halen sağlanır) → 🟢 |
| **Tespit kuralı** | `Σ pencere alanı / taban alanı < eşik` |

## R3 — Minimum kat (net tavan) yüksekliği

| Alan | Tanım |
|------|-------|
| **Eşik** | Net kat yüksekliği ≥ **2.40 m** (parametrik; ıslak hacim için ayrı eşik düşünülebilir) |
| **Ölçüm** | Kat yüksekliği = duvar `height` (modelde storey yüksekliğine eşit) |
| **İhlal üretimi** | Kat yüksekliğini eşik altına indir (ör. 2.20 m): tüm duvarlar + pencere lentosu yeniden konumlanır → 🔴 |
| **Decoy** | Yüksekliği uygun modeli/elemanı "ihlal" etiketle → 🟡 |
| **Compliant** | — (yükseklik bina geneli; ekleme ile çözülmez) |
| **Tespit kuralı** | `height < eşik` |

## R4 — (senin eklemek istediğin kural) 🔧

> "Something else" seçtin. Buraya senin kuralını koyacağız. Birkaç olası aday
> (sadece fikir — sen söyle):
>
> - **Kaçış / engel (egress/obstruction):** kapı önünde belirli bir net alanın
>   boş olması; önüne kolon/eşya koymak ihlal. (Önceki projede `add_obstruction`
>   vardı.)
> - **Merdiven/rampa eğimi:** rampa eğimi ≤ %8 gibi.
> - **Koridor min genişliği:** geçiş genişliği ≥ 1.20 m.
> - **Min oda alanı:** taban alanı ≥ 9 m² (ankette vardı, seçmedin — istersen ekleriz).
> - **Yangın kapısı / çıkış sayısı**, **kapı açılış yönü**, vb.
>
> | Alan | Tanım |
> |------|-------|
> | **Eşik** | _(belirlenecek)_ |
> | **Ölçüm** | _(belirlenecek)_ |
> | **İhlal üretimi** | _(belirlenecek)_ |
> | **Tespit kuralı** | _(belirlenecek)_ |

---

## Eşik konfigürasyonu (parametrik — taslak)

```python
RULES = {
    "R1_min_door_width":      {"inner": 0.90, "entrance": 1.00},  # m
    "R2_window_floor_ratio":  {"min_ratio": 0.10},                # -
    "R3_min_ceiling_height":  {"min_height": 2.40},               # m
    # "R4_...": {...}
}
```

> Bu config Faz 3.1 injector ve (sonra) tespit/etiketleme için tek kaynak olacak.
> Onayınla R4'ü doldurup eşikleri sabitleyince koda geçeriz.
