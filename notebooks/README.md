# `notebooks/` — Adım Adım Gösterim

Her iş adımı **ayrı bir Jupyter notebook**'ta yapılır ve gösterilir. Tek bir
birleşik arayüz yoktur. Notebook'lar `src/` altındaki motorları/modülleri import
edip çalıştırır.

## Kurulum

**Conda (önerilen — `ifcopenshell` conda-forge'dan sorunsuz gelir):**

```bash
conda env create -f ../environment.yml
conda activate ifc-tez
jupyter lab
```

**veya pip:**

```bash
pip install -r ../requirements.txt
jupyter lab
```

İnteraktif 3D/graph için `ipywidgets`, `pythreejs`, `ipycytoscape` etkin olmalı
(Jupyter Lab 4 / Notebook 7 bunları otomatik tanır).

## Notebook'lar

| Notebook | Faz | Ne yapar |
|----------|-----|----------|
| `faz1_1_baseline_uretici.ipynb` | 1.1 | **Parametrik baseline ÜRETİCİ** (3 oda + koridor + salon): `BaselineConfig` (kapı sayısı, oda/koridor boyutları, dikdörtgen/kare, varyant sayısı) → `generate_baselines`. Çok varyant + doğrulama (0 ihlal). |
| `faz1_1_baseline_kural_tabanli.ipynb` | 1.1 | Basit baseline (`medium_layout` → `build_baseline`); modüler fonksiyon mantığını gösterir (ihlal ekleme Faz 3.1 bunu kullanır). |
| `faz3_1_kural_tabanli_ihlal.ipynb` | 3.1 | Baseline'a **kural tabanlı ihlal ekleme**: 🔴 ihlal / 🟡 decoy / 🟢 uyumlu ekleme → `violated.ifc` + `meta.json`. Ground-truth ↔ tespit eşleşmesi. |
| `faz4_gorsellestirme.ipynb` | 4 | IFC → 3D model + graph + IFC metni, **senkron seçim**. Detay paneli; node'lar sürüklenebilir; **⛶ Tam ekran**; **🔴/🟡/🟢 ihlal katmanı**. |

## Görselleştirmeyi başka notebook'tan çağırma

Viewer bir modüldür; tek satırla çağrılır:

```python
import sys; sys.path.insert(0, "../src")   # src'yi yola ekle
from viewer import view

view("data/baseline_ifc/xxx.ifc")                 # IFC yolundan
view(vm)                                          # hazır ViewerModel
view(ifc_path, labels={ekey: "violation"})        # ihlal renkleriyle
view(ifc_path, labels="...meta.json")             # etiket dosyasından
```

Renk katmanı: `violation` 🔴, `decoy` 🟡 (IFC değişmedi), `compliant` 🟢 (uyumlu ekleme).

## ÖNEMLİ — Klonladıktan sonra tek seferlik kurulum (nbstripout)

Notebook'ları çalıştırınca çıktılar dosyaya yazılır; bu da `git pull`'da çakışma
yaratır. Bunu **otomatik** önlemek için repoyu klonlayınca bir kez çalıştır:

```bash
nbstripout --install      # repo kökünde; .git filtresini kurar
```

Bundan sonra git, notebook **çıktılarını yok sayar** — çalıştırsan da `pull`/`push`
sorunsuz olur, çıktılar asla commit'lenmez. (Repodaki `.gitattributes` filtreyi
zaten tanımlar; bu komut sadece yerel git'e bağlar.)

> Zaten çalıştırıp çakışma aldıysan: `git checkout -- notebooks/<nb>.ipynb`
> (çıktılar gider, kod kalır) sonra `git pull`. nbstripout kurulduysa bu sorun tekrar olmaz.

## Notlar

- `_build_*.py` betikleri ilgili notebook'u programatik üretir (yeniden üretilebilirlik).
- Üretilen IFC/veri `data/` altına yazılır (push edilmez).
