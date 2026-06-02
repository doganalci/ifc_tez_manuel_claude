"""Faz 4 görselleştirme notebook'unu üretir (nbformat ile).

Çalıştır:  python notebooks/_build_faz4.py
Üretir:    notebooks/faz4_gorsellestirme.ipynb
"""
from pathlib import Path
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

nb = new_notebook()
c = nb.cells

c.append(new_markdown_cell(
    "# Faz 4 — Görüntüleme Modülü\n"
    "\n"
    "**Girdi:** bir IFC dosyası &nbsp;→&nbsp; **Çıktı:** 3D model + graph + IFC metni, **senkron seçim**.\n"
    "\n"
    "Bir görünümde bir öğeye tıklayınca diğer ikisinde de ilgili öğe renk değiştirir; "
    "\"Seçimi kaldır\" sıfırlar. Graph node'ları sürüklenebilir.\n"
    "\n"
    "> Bu notebook adım adım ilerler: (1) IFC yükle, (2) ortak modele parse et, "
    "(3) statik önizleme, (4) IFC satır vurgusu, (5) tam interaktif arayüz."
))

c.append(new_markdown_cell("## 0) Kurulum — `src/` yolunu ekle"))
c.append(new_code_cell(
    "import sys, glob\n"
    "from pathlib import Path\n"
    "REPO = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n"
    "SRC = REPO / 'src'\n"
    "if str(SRC) not in sys.path:\n"
    "    sys.path.insert(0, str(SRC))\n"
    "print('repo :', REPO)\n"
    "print('src  :', SRC)"
))

c.append(new_markdown_cell(
    "## 1) Girdi IFC\n"
    "Varsa `data/baseline_ifc/` içindeki en yeni baseline'ı kullan; yoksa Faz 1.1 "
    "motoruyla üret."
))
c.append(new_code_cell(
    "from ifc_gen.baseline.rule_based import build_baseline\n"
    "from ifc_gen import paths\n"
    "\n"
    "found = sorted(glob.glob(str(paths.baseline_ifc_dir() / 'baseline_rule_*.ifc')))\n"
    "if found:\n"
    "    ifc_path = found[-1]\n"
    "    print('Mevcut baseline kullanılıyor:', ifc_path)\n"
    "else:\n"
    "    _, ifc_path, meta = build_baseline()\n"
    "    print('Yeni baseline üretildi:', ifc_path)"
))

c.append(new_markdown_cell(
    "## 2) Ortak modele parse et\n"
    "`ViewerModel`: her eleman için GlobalId (ortak anahtar), 3D mesh, IFC satırları "
    "ve graph kenarlarını birlikte tutar. Senkron seçimin temeli budur."
))
c.append(new_code_cell(
    "from viewer.model import load_viewer_model\n"
    "vm = load_viewer_model(ifc_path)\n"
    "print(f'Şema: {vm.schema} | eleman: {len(vm.elements)} | kenar: {len(vm.edges)}')\n"
    "print()\n"
    "for e in vm.elements.values():\n"
    "    nv = 0 if e.verts is None else len(e.verts)\n"
    "    print(f'  {e.ifc_type:10s} {e.name:12s} #{e.ifc_id:<4d} verts={nv:<4d} satır={len(e.line_ids)}')"
))
c.append(new_code_cell(
    "# Graph kenarları (ilişki tipleri)\n"
    "nm = {e.ekey: e.name for e in vm.elements.values()}\n"
    "for s, d, r in vm.edges[:15]:\n"
    "    print(f'  {nm[s]:12s} --{r}--> {nm[d]}')\n"
    "print(f'  ... toplam {len(vm.edges)} kenar')"
))

c.append(new_markdown_cell(
    "## 3) Statik önizleme (her ortamda görünür)\n"
    "Bir elemanı seçili kabul edip 3D + graph'ta nasıl senkron renklendiğini gösterir."
))
c.append(new_code_cell(
    "import matplotlib.pyplot as plt\n"
    "from viewer import static\n"
    "\n"
    "secili = next(e.ekey for e in vm.elements.values() if e.ifc_type == 'IfcWall')\n"
    "fig = plt.figure(figsize=(13, 5))\n"
    "ax1 = fig.add_subplot(121, projection='3d'); static.plot_3d(vm, secili, ax=ax1)\n"
    "ax2 = fig.add_subplot(122); static.plot_graph(vm, secili, ax=ax2)\n"
    "plt.tight_layout(); plt.show()"
))

c.append(new_markdown_cell(
    "## 4) IFC satır vurgusu\n"
    "Seçili elemanın STEP dosyasındaki ilgili satırları (kendisi + yerleşim/temsil)."
))
c.append(new_code_cell(
    "idxs = vm.highlight_line_indices(secili)\n"
    "print(f'{vm.elements[secili].name} -> vurgulanan satırlar: {[i+1 for i in idxs]}')\n"
    "for i in idxs:\n"
    "    print(f'  {i+1:>5}  {vm.ifc_lines[i]}')"
))

c.append(new_markdown_cell(
    "## 5) Tam interaktif arayüz (canlı Jupyter)\n"
    "Aşağıdaki hücre üç görünümü birlikte açar:\n"
    "\n"
    "- **Graph** node'una tıkla → o node, 3D'deki eleman ve IFC satırları renk değiştirir.\n"
    "- **3D** modelde bir mesh'e tıkla → graph ve IFC senkron güncellenir.\n"
    "- **IFC öğe** açılır listesinden seç → diğer ikisi güncellenir.\n"
    "- **Seçimi kaldır** → tüm renkler sıfırlanır.\n"
    "- Graph node'ları fareyle **sürüklenebilir**.\n"
    "\n"
    "> Not: İnteraktif görünüm için Jupyter (Lab/Notebook) çekirdeği ve `ipywidgets` "
    "etkin olmalı. `labels` parametresiyle ileride ihlal/decoy/compliant renkleri eklenecek."
))
c.append(new_code_cell(
    "from viewer.render import InteractiveViewer\n"
    "viewer = InteractiveViewer(vm)   # labels={} -> baseline'da ihlal yok\n"
    "viewer.show()"
))
c.append(new_code_cell(
    "# Programatik seçim de mümkün (test/otomasyon):\n"
    "viewer.select(secili)\n"
    "print('Seçili:', vm.elements[viewer.selected].name)\n"
    "# viewer.select(None)  # seçimi kaldır"
))

nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
out = Path(__file__).resolve().parent / "faz4_gorsellestirme.ipynb"
nbf.write(nb, str(out))
print("Yazıldı:", out)
