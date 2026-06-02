# CLAUDE.md — Proje Rehberi

Bu dosya, projeye yeni katılan bir Claude Code oturumunun hızla bağlam kazanması
içindir. (Tez: IFC/BIM üzerinde kural ihlali üretimi, görselleştirme, ML hazırlığı.)

## Çalışma tarzı (ÖNEMLİ)
- **Adım adım, manuel** ilerliyoruz. Her adımı önce konuşup onaylıyoruz, sonra yapıyoruz.
- **Tek birleşik arayüz YOK.** Her adım ayrı bir **Jupyter notebook**'ta gösterilir.
- **Mantık `src/` altında modüler fonksiyonlar**; notebook'lar bunları import edip çağırır.
  Aynı fonksiyonlar fazlar arasında yeniden kullanılır (ör. `layout_to_ifc` hem baseline
  hem ihlal eklemede kullanılır).
- Dil: kod yorumları ve notebook'lar **Türkçe**.

## Kod ↔ Veri ayrımı
- **Kod** (`src/`, `notebooks/`, `docs/`, `scripts/`) → git ile takip edilir, push edilir.
- **Dinamik veri** (`data/`) → `.gitignore` ile **push edilmez** (üretilen IFC, meta.json,
  loglar, cache, ChromaDB). Sadece `data/README.md` + `.gitkeep` takipte.
- **Notebook çıktıları** dinamiktir: `nbstripout` ile git'ten temizlenir
  (`.gitattributes` + `scripts/setup_local.sh`). Notebook'u çalıştırmak `git pull`'u bozmamalı.

## Klasör yapısı
```
src/
  ifc_gen/
    paths.py            # data/ tabanlı çıktı yolları (IFC_DATA_DIR ile override)
    baseline/           # Faz 1: kural tabanlı baseline
      layout.py         #   BuildingLayout, Wall/Opening/Room/Column, medium_layout()
      rule_based.py     #   layout_to_ifc(), build_baseline()
      procedural.py     #   BaselineConfig + generate_baselines() (parametrik üretici:
                        #     3 oda+koridor+salon, dikdörtgen/kare, çok varyant)
    inject/             # Faz 3: ihlal ekleme
      rules.py          #   RULES eşikleri + ölçüm + detect() (tespit)
      rule_based.py     #   ViolationInjector (Faz 3.1)
  viewer/               # Faz 4: görselleştirme
    model.py            #   load_viewer_model() -> ViewerModel; psets/dimensions/neighbors
    render.py           #   InteractiveViewer, view(); pythreejs 3D + ipycytoscape graph
    static.py           #   matplotlib statik önizleme (plot_3d, plot_graph)
notebooks/
  _build_*.py           # her notebook'u programatik üreten betik (yeniden üretilebilirlik)
  faz1_1_*.ipynb, faz3_1_*.ipynb, faz4_*.ipynb
docs/
  akis_diyagrami.md     # SIRALI PLAN + Mermaid akış + ilerleme tablosu (durum buradan takip)
  kural_seti.md         # R1/R2/R3 kural tanımları (+ R4 placeholder, kullanıcı kuralı)
```

## Önemli teknik kararlar
- IFC kütüphanesi: **ifcopenshell 0.8.x** yüksek seviye API (`ifcopenshell.api.run`).
- Birim: **metre** (`unit.assign_unit(f, length={"is_metric": True, "raw": "METERS"})`).
- Baseline "orta": 1 kat, 3 oda, giriş+iç kapılar, üst duvarda pencereler, döşeme, mekanlar.
  Kapı/pencerelerde `OverallWidth/Height` set edilir (kural ölçümü için).
- Viewer ortak anahtarı: **GlobalId** (`ekey`). Seçim 3 görünümü (3D/graph/IFC) senkronlar.
  İhlal renkleri: `labels={ekey: "violation"|"decoy"|"compliant"}` → 🔴/🟡/🟢.

## Kural seti (docs/kural_seti.md)
- **R1** min kapı genişliği: iç ≥ 0.90 m, giriş ≥ 1.00 m
- **R2** pencere/taban oranı: ≥ %10
- **R3** min kat yüksekliği: ≥ 2.40 m
- **R4**: kullanıcının ekleyeceği kural (henüz tanımsız)
- Baseline tüm kuralları sağlar (detect → 0 ihlal). İhlal ekleme bunları bozar.

## Durum (2026-06 itibarıyla)
- ✅ Faz 0 iskelet, ✅ Faz 1.1 kural tabanlı baseline, ✅ Faz 4 viewer (+detay+tam ekran+renk),
  ✅ kural seti R1/R2/R3 + tespit, ✅ Faz 3.1 kural tabanlı ihlal ekleme.
- ⬜ Sırada: Faz 1.2 (tam LLM baseline), 1.3 (hibrit), Faz 2 (ihlal havuzu), 3.2–3.4 (LLM'li).
- LLM'li adımlar için lokal LLM (Ollama/yerel) vs API kararı henüz verilmedi.

## Sık komutlar
```bash
# Ortam (conda)
conda env create -f environment.yml && conda activate ifc-tez
# Lokal tek-seferlik (notebook çıktıları git'e girmesin)
bash scripts/setup_local.sh
# Bir notebook'u betikten yeniden üret
python notebooks/_build_faz1_1.py
# Jupyter
jupyter lab
```

## Git
- Geliştirme branch'i: `claude/eager-goodall-ZWQNC`.
- Notebook commit'lemeden önce çıktılar nbstripout ile otomatik temizlenir.
- `data/` asla commit edilmez.
