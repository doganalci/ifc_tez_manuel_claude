# `data/` — Dinamik Veri Klasörü (PUSH EDİLMEZ)

Bu klasör **lokalde kalır**. İçeriği `.gitignore` ile takip dışı bırakılmıştır;
yalnızca bu `README.md` ve `.gitkeep` GitHub'a gider. Yani klasör yapısı repoda
durur ama **üretilen/değişen veriler push edilmez**.

## Neden ayrı?
Üretilen IFC'ler, ihlal havuzları, loglar, cache ve ChromaDB sürekli değişir.
Bunları versiyonlamak repoyu şişirir ve çakışma yaratır. Kod ↔ veri ayrımı:

- **Kod** → `src/`, `docs/` → pull/push edilir.
- **Veri** → `data/` → sadece lokalde, pull/push edilmez.

## Alt klasörler

| Klasör | İçerik |
|--------|--------|
| `data/baseline_ifc/`   | Üretilen kurallara uygun (baseline) IFC dosyaları |
| `data/violated_ifc/`   | Baseline + ihlal enjekte edilmiş IFC dosyaları (`_violated1`, `_violated2`...) |
| `data/violation_pool/` | Üretilen sözel ihlal havuzu (JSON) |
| `data/rag_corpus/`     | RAG için yönetmelik/standart kaynak dokümanlar (PDF/TXT/MD) |
| `data/chroma/`         | ChromaDB koleksiyonları (vektör veritabanı) |
| `data/cache/<slug>/`   | Veri seti özel cache |
| `data/logs/`           | Çalışma logları, üretim izleri (`meta.json`) |

> Yeni veri buraya yazılır; kod hep `data/` yolunu parametre/konfig üzerinden okur.
