"""Faz 3.1 notebook'unu üretir (kural tabanlı ihlal ekleme).

Çalıştır:  python notebooks/_build_faz3_1.py
Üretir:    notebooks/faz3_1_kural_tabanli_ihlal.ipynb
"""
from pathlib import Path
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

nb = new_notebook()
c = nb.cells

c.append(new_markdown_cell(
    "# Faz 3.1 — Kural Tabanlı (Motorlu) İhlal Ekleme\n"
    "\n"
    "**LLM yok.** Baseline'a deterministik olarak ihlal ekliyoruz ve viewer'da görüyoruz.\n"
    "\n"
    "| | Anlam | IFC |\n"
    "|--|--|--|\n"
    "| 🔴 `violation` | Kuralı bozan gerçek değişim | değişir |\n"
    "| 🟡 `decoy` | 'İhlal' denmiş ama uygun | değişmez |\n"
    "| 🟢 `compliant` | Kural bozmayan yeni ekleme | eklenir |\n"
    "\n"
    "Çıktı: `data/violated_ifc/<ad>.ifc` + `<ad>.meta.json` (ground-truth etiketler).\n"
    "Kural seti: [`docs/kural_seti.md`](../docs/kural_seti.md) — R1 kapı genişliği, "
    "R2 pencere/taban oranı, R3 kat yüksekliği."
))

c.append(new_markdown_cell("## 0) Kurulum"))
c.append(new_code_cell(
    "import sys, glob, json\n"
    "from pathlib import Path\n"
    "REPO = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n"
    "SRC = REPO / 'src'\n"
    "if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))\n"
    "print('src:', SRC)"
))

c.append(new_markdown_cell(
    "## 1) Baseline kurallara uygun mu?\n"
    "Kural tabanlı baseline **tüm kuralları sağlamalı** (ihlal sayısı 0). Önce bunu doğruluyoruz."
))
c.append(new_code_cell(
    "from ifc_gen.baseline.rule_based import build_baseline\n"
    "from ifc_gen.inject import rules\n"
    "from viewer.model import load_viewer_model\n"
    "\n"
    "_, baseline_path, _ = build_baseline()\n"
    "vmb = load_viewer_model(str(baseline_path))\n"
    "ihlaller = rules.violations_only(vmb)\n"
    "print('Baseline:', baseline_path.name)\n"
    "print('Baseline ihlal sayısı (0 olmalı):', len(ihlaller))\n"
    "for f in rules.detect(vmb):\n"
    "    if f.rule == 'R2_window_floor_ratio':\n"
    "        print(f'  {vmb.elements[f.ekey].name}: {f.detail}')"
))

c.append(new_markdown_cell(
    "## 2) Manuel ihlal ekleme — adım adım\n"
    "`ViolationInjector` ile her ihlali tek tek uyguluyoruz:"
))
c.append(new_code_cell(
    "from ifc_gen.inject.rule_based import ViolationInjector\n"
    "\n"
    "inj = ViolationInjector()\n"
    "inj.narrow_door('Kapi-IC1', new_width=0.70)   # R1 🔴 iç kapı 0.70 < 0.90 m\n"
    "inj.remove_window('Pencere-R2')               # R2 🔴 orta odanın penceresi gider\n"
    "inj.mark_decoy('Kapi-Giris')                  # 🟡 uygun ama 'ihlal' etiketli\n"
    "inj.add_compliant_column((6.0, 4.0))          # 🟢 kural bozmayan kolon\n"
    "print('Uygulanan mutasyonlar:')\n"
    "for m in inj._mutations: print('  -', m)"
))

c.append(new_markdown_cell("## 3) Üret → violated IFC + meta.json"))
c.append(new_code_cell(
    "model, violated_path, meta = inj.build()\n"
    "print('Violated IFC:', violated_path.name)\n"
    "print('Etiket sayıları:', meta['counts'])\n"
    "print()\n"
    "for a in meta['annotations']:\n"
    "    print(f\"  {a['status']:10s} {a['rule']:24s} {a['name']:12s} | {a['detail']}\")"
))

c.append(new_markdown_cell(
    "## 4) Doğrulama — enjekte edilen ihlaller gerçekten kuralı bozuyor mu?\n"
    "Tespit (`rules.detect`) **tam olarak gerçek ihlalleri** bulmalı; decoy 🟡 ve "
    "compliant 🟢 ihlal olarak görünmemeli. Ground-truth ↔ tespit tutarlılığı."
))
c.append(new_code_cell(
    "vm = load_viewer_model(str(violated_path))\n"
    "tespit = rules.violations_only(vm)\n"
    "print('Tespit edilen ihlaller:')\n"
    "for f in tespit:\n"
    "    print(f'  {f.rule:24s} {vm.elements[f.ekey].name:10s} {f.detail}')\n"
    "\n"
    "gt = {a['ekey'] for a in meta['annotations'] if a['status']=='violation'}\n"
    "det = {f.ekey for f in tespit}\n"
    "print()\n"
    "print('Ground-truth ihlal ekey =', gt)\n"
    "print('Tespit edilen ekey      =', det)\n"
    "print('EŞLEŞME:', 'EVET ✅' if gt == det else 'HAYIR ⚠️')"
))

c.append(new_markdown_cell(
    "## 5) Görselleştir — 🔴/🟡/🟢\n"
    "Statik önizleme (her ortam) + tek satır interaktif `view(...)`."
))
c.append(new_code_cell(
    "import matplotlib.pyplot as plt\n"
    "from viewer import static, load_labels\n"
    "labels = load_labels(str(violated_path).replace('.ifc', '.meta.json'))\n"
    "fig = plt.figure(figsize=(13, 5))\n"
    "ax1 = fig.add_subplot(121, projection='3d'); static.plot_3d(vm, labels=labels, ax=ax1)\n"
    "ax2 = fig.add_subplot(122); static.plot_graph(vm, labels=labels, ax=ax2)\n"
    "plt.tight_layout(); plt.show()"
))
c.append(new_code_cell(
    "from viewer import view\n"
    "# meta.json yolunu doğrudan labels olarak verebiliriz:\n"
    "view(str(violated_path), labels=str(violated_path).replace('.ifc', '.meta.json'))"
))

c.append(new_markdown_cell(
    "## Özet\n"
    "- Baseline kurallara uygun (0 ihlal) → üzerine **kural tabanlı** 🔴/🟡/🟢 eklendi.\n"
    "- `meta.json` ground-truth etiketleri taşır; viewer otomatik renklendirir.\n"
    "- Tespit, enjekte edilen gerçek ihlallerle birebir eşleşir (decoy/compliant hariç).\n"
    "- Sıradaki yöntemler: 3.2 tam LLM, 3.3 hibrit, 3.4 havuzdan seç→LLM→motor."
))

nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
out = Path(__file__).resolve().parent / "faz3_1_kural_tabanli_ihlal.ipynb"
nbf.write(nb, str(out))
print("Yazıldı:", out)
