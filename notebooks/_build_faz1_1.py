"""Faz 1.1 notebook'unu üretir (kural tabanlı baseline IFC).

Çalıştır:  python notebooks/_build_faz1_1.py
Üretir:    notebooks/faz1_1_baseline_kural_tabanli.ipynb
"""
from pathlib import Path
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

nb = new_notebook()
c = nb.cells

c.append(new_markdown_cell(
    "# Faz 1.1 — Kural Tabanlı (Motorlu) Baseline IFC Üretimi\n"
    "\n"
    "**LLM yok.** Deterministik bir motorla (ifcopenshell) kurallara uygun bir bina\n"
    "IFC'si üretiyoruz: 1 kat, 3 oda, giriş + iç kapılar, pencereler, döşeme, mekanlar.\n"
    "\n"
    "**Tasarım:** Mantık `src/ifc_gen/baseline/` altında **fonksiyon** olarak yazılı;\n"
    "bu notebook onları **import edip çağırıyor**. Aynı fonksiyonlar diğer fazlarda da\n"
    "kullanılıyor (ör. Faz 3.1 ihlal ekleme `layout_to_ifc`'i yeniden kullanır).\n"
    "\n"
    "| Fonksiyon | Ne yapar |\n"
    "|-----------|----------|\n"
    "| `medium_layout(...)` | Tasarım verisi (duvar/oda/kapı/pencere) üretir — IFC'den bağımsız |\n"
    "| `layout_to_ifc(layout)` | Tasarımı geçerli IFC4 modeline çevirir (in-memory) |\n"
    "| `build_baseline(layout)` | IFC üretir + `data/baseline_ifc/` altına yazar + `meta.json` |"
))

c.append(new_markdown_cell("## 0) Kurulum — `src/` yolunu ekle"))
c.append(new_code_cell(
    "import sys, json\n"
    "from pathlib import Path\n"
    "REPO = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n"
    "SRC = REPO / 'src'\n"
    "if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))\n"
    "print('src:', SRC)"
))

c.append(new_markdown_cell(
    "## 1) Tasarım verisi — `medium_layout()`\n"
    "Önce IFC'den bağımsız, saf tasarım verisini üretiyoruz (metre)."
))
c.append(new_code_cell(
    "from ifc_gen.baseline import medium_layout\n"
    "\n"
    "layout = medium_layout(width=12, depth=8, height=3, wall_thickness=0.2)\n"
    "print('Parametreler:', layout.params)\n"
    "print(f'Duvar: {len(layout.walls)} | Açıklık: {len(layout.openings)} | Oda: {len(layout.rooms)}')\n"
    "print()\n"
    "print('Duvarlar:')\n"
    "for w in layout.walls:\n"
    "    tip = 'dış' if w.is_external else 'iç'\n"
    "    print(f'  {w.name:9s} {tip:3s}  uzunluk={w.length:.1f}m  kalınlık={w.thickness}m')\n"
    "print('Açıklıklar:')\n"
    "for o in layout.openings:\n"
    "    print(f'  {o.name:12s} {o.kind:6s} @ {o.wall_name:8s} {o.width}×{o.height}m sill={o.sill}')"
))

c.append(new_markdown_cell(
    "## 2) IFC üret — `build_baseline()`\n"
    "Tasarımı geçerli IFC4'e çevirir, `data/baseline_ifc/` altına yazar, `meta.json` kaydeder."
))
c.append(new_code_cell(
    "from ifc_gen.baseline import build_baseline\n"
    "\n"
    "model, ifc_path, meta = build_baseline(layout)\n"
    "print('Yazıldı:', ifc_path)\n"
    "print('Şema:', meta['schema'], '| birim: metre')\n"
    "print('Eleman sayıları:')\n"
    "print(json.dumps(meta['counts'], indent=2))"
))

c.append(new_markdown_cell(
    "## 3) Geçerlilik — şema + geometri\n"
    "Üretilen IFC standart şemaya uygun mu, geometri çiziliyor mu?"
))
c.append(new_code_cell(
    "import ifcopenshell\n"
    "from ifcopenshell import validate\n"
    "\n"
    "f = ifcopenshell.open(str(ifc_path))\n"
    "lg = validate.json_logger(); validate.validate(f, lg)\n"
    "print('Şema hatası:', len(lg.statements))\n"
    "\n"
    "import ifcopenshell.geom as geom\n"
    "s = geom.settings(); it = geom.iterator(s, f)\n"
    "n = bad = 0\n"
    "if it.initialize():\n"
    "    while True:\n"
    "        if not it.get().geometry.verts: bad += 1\n"
    "        n += 1\n"
    "        if not it.next(): break\n"
    "print(f'Geometri şekli: {n} | boş: {bad}')"
))

c.append(new_markdown_cell(
    "## 4) Kural uyumu — baseline temiz olmalı\n"
    "Kural tabanlı baseline **tüm kuralları sağlamalı** (ihlal sayısı = 0). "
    "Aynı kural seti Faz 3.1 ihlal eklemede de kullanılıyor."
))
c.append(new_code_cell(
    "from ifc_gen.inject import rules\n"
    "from viewer.model import load_viewer_model\n"
    "\n"
    "vm = load_viewer_model(str(ifc_path))\n"
    "ihlaller = rules.violations_only(vm)\n"
    "print('Baseline ihlal sayısı (0 olmalı):', len(ihlaller))\n"
    "for f in rules.detect(vm):\n"
    "    durum = 'İHLAL' if f.violated else 'ok'\n"
    "    print(f'  {f.rule:24s} {vm.elements[f.ekey].name:10s} {f.detail:30s} [{durum}]')"
))

c.append(new_markdown_cell(
    "## 5) Görselleştir\n"
    "Statik önizleme (her ortam) + tek satır interaktif `view(...)`."
))
c.append(new_code_cell(
    "import matplotlib.pyplot as plt\n"
    "from viewer import static\n"
    "fig = plt.figure(figsize=(13, 5))\n"
    "ax1 = fig.add_subplot(121, projection='3d'); static.plot_3d(vm, ax=ax1)\n"
    "ax2 = fig.add_subplot(122); static.plot_graph(vm, ax=ax2)\n"
    "plt.tight_layout(); plt.show()"
))
c.append(new_code_cell(
    "from viewer import view\n"
    "view(str(ifc_path))"
))

c.append(new_markdown_cell(
    "## 6) Yeniden kullanım — farklı parametrelerle baseline\n"
    "Fonksiyon olduğu için istediğin boyutta baseline üretebilirsin. Örnek: daha büyük bina."
))
c.append(new_code_cell(
    "buyuk = medium_layout(width=15, depth=10, height=3.2)\n"
    "_, buyuk_path, buyuk_meta = build_baseline(buyuk, filename='baseline_buyuk.ifc')\n"
    "print('Yazıldı:', buyuk_path.name, '| sayılar:', buyuk_meta['counts'])\n"
    "# view(str(buyuk_path))   # istersen görselleştir"
))

c.append(new_markdown_cell(
    "## Özet\n"
    "- Baseline mantığı **modüler fonksiyonlar** (`medium_layout` / `layout_to_ifc` / `build_baseline`).\n"
    "- Çıktı: geçerli IFC4 (şema 0 hata, geometri tam) + `meta.json`, `data/baseline_ifc/` altında.\n"
    "- Baseline **kurallara uygun** (0 ihlal) → ihlal ekleme (Faz 3) için temiz zemin.\n"
    "- Sıradaki baseline yöntemleri: **1.2 tam LLM**, **1.3 hibrit (LLM + motor)**."
))

nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
out = Path(__file__).resolve().parent / "faz1_1_baseline_kural_tabanli.ipynb"
nbf.write(nb, str(out))
print("Yazıldı:", out)
