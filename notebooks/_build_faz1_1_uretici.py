"""Faz 1.1 baseline ÜRETİCİ notebook'unu üretir (parametrik, çok varyantlı).

Çalıştır:  python notebooks/_build_faz1_1_uretici.py
Üretir:    notebooks/faz1_1_baseline_uretici.ipynb
"""
from pathlib import Path
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

nb = new_notebook()
c = nb.cells

c.append(new_markdown_cell(
    "# Faz 1.1 — Kural Tabanlı Motorlu Baseline ÜRETİCİ\n"
    "\n"
    "**LLM yok.** Parametrik, deterministik motor. Topoloji: **dikdörtgen/kare bina**\n"
    "içinde **3 oda + 1 koridor + 1 salon**.\n"
    "\n"
    "```\n"
    "+-----------------------------+  üst bant: 3 oda (yan yana)\n"
    "|  Oda1  |  Oda2  |  Oda3     |\n"
    "+--------+--------+-----------+\n"
    "|        KORİDOR (tam en)     |  orta bant: yatay koridor\n"
    "+-----------------------------+\n"
    "|        SALON (tam en)       |  alt bant: salon\n"
    "+-----------------------------+\n"
    "```\n"
    "\n"
    "**Parametreler** (`BaselineConfig`):\n"
    "\n"
    "| Parametre | Açıklama | Varsayılan |\n"
    "|-----------|----------|------------|\n"
    "| `doors_per_room` | her oda/salonda kaç kapı | 3 |\n"
    "| `room_min` / `room_max` | oda kenar boyutları (m) | 3 / 5 |\n"
    "| `corridor_min` / `corridor_max` | koridor genişlik+uzunluk (m) | 3 / 5 |\n"
    "| `shape` | `rectangle` veya `square` | rectangle |\n"
    "| `n_baselines` | kaç farklı baseline üretilecek | 1 |\n"
    "\n"
    "> Ek varsayılan (parametre değil): her oda/salona R2'yi (pencere/taban ≥%10)\n"
    "> sağlayacak pencere eklenir; koridor sirkülasyon olduğu için R2'den muaftır.\n"
    "> Mantık `src/ifc_gen/baseline/procedural.py` içinde; motor `layout_to_ifc`'i yeniden kullanır."
))

c.append(new_markdown_cell("## 0) Kurulum"))
c.append(new_code_cell(
    "import sys, json\n"
    "from pathlib import Path\n"
    "REPO = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n"
    "SRC = REPO / 'src'\n"
    "if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))\n"
    "print('src:', SRC)"
))

c.append(new_markdown_cell(
    "## 1) Konfigürasyon\n"
    "Senin belirlediğin 5 parametre. (Burada varsayılanlar; istediğini değiştir.)"
))
c.append(new_code_cell(
    "from ifc_gen.baseline.procedural import BaselineConfig, generate_baselines\n"
    "\n"
    "cfg = BaselineConfig(\n"
    "    doors_per_room = 3,\n"
    "    room_min = 3.0, room_max = 5.0,\n"
    "    corridor_min = 3.0, corridor_max = 5.0,\n"
    "    shape = 'rectangle',\n"
    "    n_baselines = 1,\n"
    "    seed = 42,            # tekrar üretilebilirlik için (None = rastgele)\n"
    ")\n"
    "print(cfg)"
))

c.append(new_markdown_cell(
    "## 2) Üret\n"
    "`generate_baselines(cfg)` → her varyantı `data/baseline_ifc/` altına IFC + `meta.json` yazar."
))
c.append(new_code_cell(
    "sonuc = generate_baselines(cfg)\n"
    "print(f'{len(sonuc)} baseline üretildi:')\n"
    "for r in sonuc:\n"
    "    pr = r['meta']['params']\n"
    "    print(f\"  {r['ifc_path'].name}\")\n"
    "    print(f\"     shape={pr['shape']} W={pr['width']} D={pr['depth']} \"\n"
    "          f\"oda_gen={pr['room_widths']} koridor={pr['corridor']} salon={pr['salon_depth']}\")\n"
    "    print(f\"     sayılar={r['meta']['counts']}\")"
))

c.append(new_markdown_cell(
    "## 3) Doğrulama — geçerli mi + kurallara uygun mu?\n"
    "Her baseline: şema 0 hata olmalı ve **0 kural ihlali** (kural tabanlı baseline temizdir)."
))
c.append(new_code_cell(
    "import ifcopenshell\n"
    "from ifcopenshell import validate\n"
    "from ifc_gen.inject import rules\n"
    "from viewer.model import load_viewer_model\n"
    "\n"
    "for r in sonuc:\n"
    "    p = str(r['ifc_path'])\n"
    "    f = ifcopenshell.open(p)\n"
    "    lg = validate.json_logger(); validate.validate(f, lg)\n"
    "    vm = load_viewer_model(p)\n"
    "    viol = rules.violations_only(vm)\n"
    "    spaces = [e.name for e in vm.elements.values() if e.ifc_type=='IfcSpace']\n"
    "    print(f\"{r['ifc_path'].name}: şema_hata={len(lg.statements)} | \"\n"
    "          f\"kural_ihlali={len(viol)} | mekanlar={spaces}\")\n"
    "    for v in viol: print('   ihlal:', v.rule, vm.elements[v.ekey].name, v.detail)"
))

c.append(new_markdown_cell("## 4) Görselleştir — ilk baseline"))
c.append(new_code_cell(
    "import matplotlib.pyplot as plt\n"
    "from viewer import static\n"
    "vm = load_viewer_model(str(sonuc[0]['ifc_path']))\n"
    "fig = plt.figure(figsize=(13, 5))\n"
    "ax1 = fig.add_subplot(121, projection='3d'); static.plot_3d(vm, ax=ax1)\n"
    "ax2 = fig.add_subplot(122); static.plot_graph(vm, ax=ax2)\n"
    "plt.tight_layout(); plt.show()"
))
c.append(new_code_cell(
    "from viewer import view\n"
    "view(str(sonuc[0]['ifc_path']))"
))

c.append(new_markdown_cell(
    "## 5) Parametreyi değiştir — çok varyant + kare bina\n"
    "Örnek: kare bina, oda başına 2 kapı, 3 farklı baseline."
))
c.append(new_code_cell(
    "cfg2 = BaselineConfig(shape='square', doors_per_room=2, n_baselines=3, seed=7)\n"
    "sonuc2 = generate_baselines(cfg2)\n"
    "for r in sonuc2:\n"
    "    pr = r['meta']['params']\n"
    "    print(f\"{r['ifc_path'].name}: shape={pr['shape']} W={pr['width']} D={pr['depth']} \"\n"
    "          f\"sayılar={r['meta']['counts']}\")"
))

c.append(new_markdown_cell(
    "## Özet\n"
    "- `BaselineConfig` + `generate_baselines()` → 5 parametreli, çok varyantlı **kural tabanlı** baseline.\n"
    "- Topoloji: 3 oda + koridor + salon; dikdörtgen/kare; her varyant farklı (seed ile tekrar üretilebilir).\n"
    "- Çıktı: geçerli IFC4 (şema 0 hata) + `meta.json`, **0 kural ihlali**.\n"
    "- `.py` modül olduğu için diğer fazlardan da çağrılır (ihlal ekleme bu baseline'lar üzerine işler)."
))

nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
out = Path(__file__).resolve().parent / "faz1_1_baseline_uretici.ipynb"
nbf.write(nb, str(out))
print("Yazıldı:", out)
