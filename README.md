# IFC Tez — Manuel Sürüm (Lokal)

Bu repo, daha önce sunucuda yapılan IFC/BIM çalışmasının **lokalde, manuel ve
adım adım** yeniden kurulan sürümüdür. Hedef: IFC üretimi, ihlal havuzu, ihlal
enjeksiyonu ve görüntüleme modüllerini kontrollü biçimde tekrar inşa etmek.

## Kod ↔ Veri Ayrımı

- **Kod** (`src/`, `docs/`) → Git ile pull/push edilir.
- **Dinamik veri** (`data/`) → sadece lokalde kalır, **push edilmez** (`.gitignore`).
  Üretilen IFC'ler, ihlal havuzu, loglar, cache ve ChromaDB buraya yazılır.
  Detay: [`data/README.md`](data/README.md).

## Plan / Akış

Sıralı plan ve akış diyagramları: [`docs/akis_diyagrami.md`](docs/akis_diyagrami.md).

Şimdilik kapsam **sadece** şu 4 faz:
1. **Baseline IFC üretimi** — kural tabanlı / tamamen LLM / hibrit
2. **İhlal havuzu üretme** — LLM / LLM+doküman / RAG / RAG+LLM
3. **Baseline'a ihlal ekleme** — kural tabanlı / LLM / hibrit / havuzdan seç→LLM→motor
4. **Görüntüleme modülü** — 3D + graph + IFC senkron seçim

## Kurulum

**Conda (önerilen):**
```bash
conda env create -f environment.yml
conda activate ifc-tez
jupyter lab
```

**pip:**
```bash
pip install -r requirements.txt
```

## Klasör Yapısı

```
src/
  ifc_gen/
    baseline/    # Faz 1: baseline IFC üretimi
    inject/      # Faz 3: ihlal ekleme
  violation_pool/  # Faz 2: ihlal havuzu üretme
  viewer/          # Faz 4: görüntüleme modülü
docs/
  akis_diyagrami.md
data/              # dinamik veri (push edilmez)
```

## Çalışma Tarzı

Adım adım gidiyoruz: her faz/alt-adım ayrı ayrı yapılır, onaylanır, commit/push
edilir. Akış diyagramındaki ilerleme tablosu her adımda güncellenir.
