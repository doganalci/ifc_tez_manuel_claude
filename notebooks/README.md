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
| `faz4_gorsellestirme.ipynb` | 4 | IFC → 3D model + graph + IFC metni, **senkron seçim**. Bir görünümde seçim diğerlerini renklendirir; node'lar sürüklenebilir; "Seçimi kaldır" sıfırlar; **⛶ Tam ekran**; **🔴/🟡/🟢 ihlal katmanı**. |

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

## Notlar

- **Çıktılar push edilmez:** Notebook'ları commit'lemeden önce çıktıları
  temizleyin (`jupyter nbconvert --clear-output --inplace <nb>.ipynb`). Çıktılar
  ve widget state'i dinamik kabul edilir.
- `_build_*.py` betikleri ilgili notebook'u programatik üretir (yeniden üretilebilirlik).
- Üretilen IFC/veri `data/` altına yazılır (push edilmez).
