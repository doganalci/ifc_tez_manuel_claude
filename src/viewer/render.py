"""Faz 4 — Render + interaktif senkron seçim (Jupyter).

Üç görünüm tek bir `selected_ekey` durumu üzerinden bağlanır:
  - 3D (pythreejs): tıklanan mesh -> seçim; seçili eleman rengi değişir
  - graph (ipycytoscape): sürüklenebilir node'lar; tıklanan node -> seçim
  - IFC metni (ipywidgets): elemanı seç -> ilgili STEP satırları vurgulanır

Bir görünümde seçim yapılınca diğer ikisi senkron güncellenir. "Seçimi kaldır"
tüm vurguları sıfırlar. `labels` ile ihlal/decoy/compliant renklendirmesi de
desteklenir (baseline'da boş).
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .model import ViewerModel, Element

# --- Renk paleti ---
TYPE_COLOR = {
    "IfcWall": "#cfcfcf", "IfcWallStandardCase": "#cfcfcf",
    "IfcSlab": "#b0a08f", "IfcDoor": "#8b5a2b", "IfcWindow": "#7fb3d5",
    "IfcColumn": "#9e9e9e", "IfcStair": "#a1887f", "IfcRamp": "#a1887f",
    "IfcSpace": "#d6eaf8",
}
SELECT_COLOR = "#ff5722"          # seçili eleman (turuncu-kırmızı)
LABEL_COLOR = {                   # ihlal katmanı
    "violation": "#e53935",       # 🔴 gerçek ihlal
    "decoy": "#fbc02d",           # 🟡 sahte etiket (IFC değişmedi)
    "compliant": "#43a047",       # 🟢 kural bozmayan ekleme
}
_DEFAULT = "#bdbdbd"

# Tam ekran: container'a .ifc-viewer-root sınıfı eklenir. Buton, tarayıcının
# tüm penceresini dolduran güvenilir bir "fixed overlay" tam ekran açar
# (Fullscreen API bazı Jupyter ortamlarında engellenir; bu her yerde çalışır).
_FULLSCREEN_CSS = """
<style>
.ifc-viewer-root.ifc-fs {
  position:fixed; inset:0; z-index:99999; background:#1e1e1e;
  overflow:auto; padding:12px; box-sizing:border-box;
}
.ifc-viewer-root.ifc-fs canvas { width:100% !important; height:auto !important; }
.ifc-viewer-root.ifc-fs .ifc-text-panel { height:78vh !important; }
</style>
"""
_FULLSCREEN_BUTTON = """
<button style="padding:5px 12px;cursor:pointer;border:1px solid #888;
border-radius:4px;background:#2d2d2d;color:#eee;font-weight:bold"
onclick="(function(b){var r=b.closest('.ifc-viewer-root');if(!r)return;
var on=r.classList.toggle('ifc-fs');b.textContent=on?'✕ Tam ekrandan çık':'⛶ Tam ekran';
window.dispatchEvent(new Event('resize'));})(this)">
⛶ Tam ekran</button>
"""


def _base_color(el: Element, labels: dict[str, str]) -> str:
    if el.ekey in labels and labels[el.ekey] in LABEL_COLOR:
        return LABEL_COLOR[labels[el.ekey]]
    return TYPE_COLOR.get(el.ifc_type, _DEFAULT)


# ============================================================================
# 3D (pythreejs)
# ============================================================================
def build_threejs(vm: ViewerModel, labels: dict[str, str] | None = None):
    import pythreejs as p3

    labels = labels or {}
    meshes: dict[str, "p3.Mesh"] = {}
    objs = []
    all_pts = []

    for ek, el in vm.elements.items():
        if el.verts is None or el.faces is None or not len(el.faces):
            continue
        verts = el.verts.astype("float32")
        faces = el.faces.astype("uint32").ravel()
        all_pts.append(verts)
        geom = p3.BufferGeometry(
            attributes={"position": p3.BufferAttribute(verts, normalized=False)},
            index=p3.BufferAttribute(faces, normalized=False),
        )
        geom.exec_three_obj_method("computeVertexNormals")
        transparent = el.ifc_type == "IfcSpace"
        mat = p3.MeshLambertMaterial(
            color=_base_color(el, labels),
            transparent=transparent, opacity=0.18 if transparent else 1.0,
            side="DoubleSide",
        )
        mesh = p3.Mesh(geometry=geom, material=mat, name=ek)
        meshes[ek] = mesh
        objs.append(mesh)

    pts = np.vstack(all_pts) if all_pts else np.zeros((1, 3))
    center = pts.mean(axis=0)
    span = float(np.linalg.norm(pts.max(axis=0) - pts.min(axis=0))) or 10.0
    cam_pos = (center + np.array([span, -span, span])).tolist()

    camera = p3.PerspectiveCamera(position=cam_pos, fov=50,
                                  up=[0, 0, 1], aspect=1.4)
    key = p3.DirectionalLight(color="#ffffff", intensity=0.7, position=cam_pos)
    amb = p3.AmbientLight(color="#ffffff", intensity=0.5)
    scene = p3.Scene(children=objs + [camera, key, amb], background="#1e1e1e")
    controls = p3.OrbitControls(controlling=camera, target=center.tolist())
    renderer = p3.Renderer(scene=scene, camera=camera, controls=[controls],
                           width=560, height=420)
    picker = p3.Picker(controlling=scene, event="click")
    renderer.controls = renderer.controls + [picker]
    return renderer, meshes, picker


def set_mesh_selection(meshes: dict, vm: ViewerModel, selected: Optional[str],
                       labels: dict[str, str] | None = None):
    labels = labels or {}
    for ek, mesh in meshes.items():
        if ek == selected:
            mesh.material.color = SELECT_COLOR
            mesh.material.opacity = 1.0
        else:
            mesh.material.color = _base_color(vm.elements[ek], labels)
            mesh.material.opacity = 0.18 if vm.elements[ek].ifc_type == "IfcSpace" else 1.0


# ============================================================================
# Graph (ipycytoscape)
# ============================================================================
_REL_STYLE = {"hosts": "#888", "bounds": "#5dade2"}


def build_cytoscape(vm: ViewerModel, labels: dict[str, str] | None = None):
    import ipycytoscape

    labels = labels or {}
    nodes = []
    for ek, el in vm.elements.items():
        nodes.append({"data": {
            "id": ek, "label": el.name, "etype": el.ifc_type,
            "color": _base_color(el, labels), "ifc_id": el.ifc_id,
        }})
    edges = [{"data": {"source": s, "target": d, "rel": r}}
             for (s, d, r) in vm.edges]

    cyto = ipycytoscape.CytoscapeWidget()
    cyto.graph.add_graph_from_json({"nodes": nodes, "edges": edges},
                                   directed=True)
    cyto.set_layout(name="cose", nodeRepulsion=8000, idealEdgeLength=80,
                    animate=False)
    cyto.set_style([
        {"selector": "node", "style": {
            "background-color": "data(color)", "label": "data(label)",
            "font-size": "9px", "color": "#eee", "text-valign": "top",
            "width": 22, "height": 22, "border-width": 1, "border-color": "#333"}},
        {"selector": "node.sel", "style": {
            "background-color": SELECT_COLOR, "border-width": 3,
            "border-color": "#fff", "width": 30, "height": 30}},
        {"selector": "edge", "style": {
            "width": 1.5, "line-color": "#777", "target-arrow-color": "#777",
            "target-arrow-shape": "triangle", "curve-style": "bezier"}},
        {"selector": "edge.sel", "style": {"line-color": SELECT_COLOR,
            "target-arrow-color": SELECT_COLOR, "width": 3}},
    ])
    return cyto


def set_graph_selection(cyto, vm: ViewerModel, selected: Optional[str]):
    for n in cyto.graph.nodes:
        n.classes = "sel" if n.data.get("id") == selected else ""
    for e in cyto.graph.edges:
        on = selected is not None and (e.data.get("source") == selected
                                       or e.data.get("target") == selected)
        e.classes = "sel" if on else ""


# ============================================================================
# IFC metni (ipywidgets HTML)
# ============================================================================
def ifc_text_html(vm: ViewerModel, highlight: set[int] | None = None,
                  window: int = 1200) -> str:
    highlight = highlight or set()
    rows = []
    show_from = min(highlight) - 3 if highlight else 0
    show_to = (max(highlight) + 4) if highlight else min(window, len(vm.ifc_lines))
    show_from = max(0, show_from)
    show_to = min(len(vm.ifc_lines), max(show_to, show_from + 40))
    for i in range(show_from, show_to):
        ln = (vm.ifc_lines[i].replace("&", "&amp;")
              .replace("<", "&lt;").replace(">", "&gt;"))
        if i in highlight:
            rows.append(f'<div style="background:#ff5722;color:#fff;'
                        f'padding:0 4px"><b>{i+1:>5}</b>  {ln}</div>')
        else:
            rows.append(f'<div style="color:#bbb;padding:0 4px">'
                        f'<span style="color:#666">{i+1:>5}</span>  {ln}</div>')
    return ('<div class="ifc-text-panel" style="font-family:monospace;'
            'font-size:11px;height:460px;overflow:auto;background:#1e1e1e;'
            'border:1px solid #333">' + "".join(rows) + "</div>")


# ============================================================================
# Detay paneli — seçilen node'un içeriği
# ============================================================================
def detail_html(vm: ViewerModel, ekey: Optional[str],
                labels: dict[str, str] | None = None) -> str:
    labels = labels or {}
    if not ekey or ekey not in vm.elements:
        return ('<div style="font-size:12px;color:#888;padding:8px;'
                'border:1px solid #333;background:#1e1e1e">'
                'Bir node / 3D eleman / IFC öğesi seç → içeriği burada görünür.</div>')
    el = vm.elements[ekey]
    rows = [f"<b>{el.name}</b> <span style='color:#888'>({el.ifc_type})</span>"]
    rows.append(f"<span style='color:#888'>GlobalId:</span> <code>{el.ekey}</code>"
                f" &nbsp; <span style='color:#888'>STEP:</span> #{el.ifc_id}")

    dims = vm.dimensions(ekey)
    if dims:
        rows.append(f"<span style='color:#888'>Boyut (G×D×Y):</span> "
                    f"{dims[0]:.2f} × {dims[1]:.2f} × {dims[2]:.2f} m")

    if ekey in labels:
        st = labels[ekey]
        col = LABEL_COLOR.get(st, "#888")
        tr = {"violation": "🔴 İhlal", "decoy": "🟡 Sahte (decoy)",
              "compliant": "🟢 Uyumlu ekleme"}.get(st, st)
        rows.append(f"<span style='color:#888'>Etiket:</span> "
                    f"<span style='color:{col};font-weight:bold'>{tr}</span>")

    psets = vm.psets(ekey)
    if psets:
        ps = []
        for pname, props in psets.items():
            kv = ", ".join(f"{k}={v}" for k, v in props.items() if k != "id")
            ps.append(f"<div style='margin-left:8px'><i>{pname}</i>: {kv}</div>")
        rows.append("<span style='color:#888'>Pset'ler:</span>" + "".join(ps))

    nbrs = vm.neighbors(ekey)
    if nbrs:
        items = []
        for nek, rel, dirn in nbrs[:12]:
            arrow = "→" if dirn == "->" else "←"
            items.append(f"<li>{arrow} <b>{vm.elements[nek].name}</b> "
                         f"<span style='color:#888'>({rel})</span></li>")
        more = f"<li style='color:#888'>… +{len(nbrs)-12}</li>" if len(nbrs) > 12 else ""
        rows.append(f"<span style='color:#888'>İlişkiler ({len(nbrs)}):</span>"
                    f"<ul style='margin:2px 0 0 0;padding-left:18px'>"
                    + "".join(items) + more + "</ul>")

    return ('<div style="font-size:12px;color:#ddd;padding:8px;line-height:1.5;'
            'border:1px solid #333;background:#1e1e1e;height:460px;overflow:auto">'
            + "<br>".join(rows) + "</div>")


# ============================================================================
# Interaktif kontrolör — üç görünümü bağlar
# ============================================================================
class InteractiveViewer:
    """Üç görünümü tek seçim durumuyla senkronlar.

    viewer = InteractiveViewer(vm)
    viewer.show()        # Jupyter'de interaktif arayüz
    """

    def __init__(self, vm: ViewerModel, labels: dict[str, str] | None = None):
        self.vm = vm
        self.labels = labels or {}
        self.selected: Optional[str] = None
        self._build()

    def _build(self):
        import ipywidgets as W

        self.renderer, self.meshes, self.picker = build_threejs(self.vm, self.labels)
        self.cyto = build_cytoscape(self.vm, self.labels)
        try:
            self.cyto.layout.height = "460px"
        except Exception:
            pass
        self.ifc_box = W.HTML(value=ifc_text_html(self.vm))
        self.detail_box = W.HTML(value=detail_html(self.vm, None, self.labels))

        # IFC tarafından seçim: eleman seçici (satır tıklamasının pratik karşılığı)
        opts = [("— seçim yok —", "")] + [
            (f"#{el.ifc_id}  {el.ifc_type[3:]:8s} {el.name}", ek)
            for ek, el in self.vm.elements.items()]
        self.selector = W.Dropdown(options=opts, description="IFC öğe:",
                                   layout=W.Layout(width="320px"))
        self.clear_btn = W.Button(description="Seçimi kaldır", button_style="warning")
        self.status = W.HTML(value="<i>Seçim yok</i>")

        # --- olay bağlama ---
        self.picker.observe(self._on_pick, names=["object"])
        self.cyto.on("node", "click", self._on_node)
        self.selector.observe(self._on_select, names="value")
        self.clear_btn.on_click(lambda _b: self.select(None))

        # Tam ekran: tarayıcı Fullscreen API'si (kernel'e gitmeden, doğrudan JS)
        style = W.HTML(_FULLSCREEN_CSS)
        fs_btn = W.HTML(_FULLSCREEN_BUTTON)
        legend = W.HTML(self._legend_html())

        toolbar = W.HBox([fs_btn, self.selector, self.clear_btn],
                         layout=W.Layout(align_items="center", flex_flow="row wrap"))

        flex = W.Layout(flex="1 1 0%", min_width="280px")
        left = W.VBox([W.HTML("<b>3D Model</b>"), self.renderer], layout=flex)
        mid = W.VBox([W.HTML("<b>Graph (node'lar sürüklenebilir)</b>"), self.cyto],
                     layout=flex)
        right = W.VBox([W.HTML("<b>IFC</b>"), self.ifc_box], layout=flex)
        detail = W.VBox([W.HTML("<b>Detay (seçilen eleman)</b>"), self.detail_box],
                        layout=flex)
        panels = W.HBox([left, mid, right, detail],
                        layout=W.Layout(flex_flow="row wrap", width="100%"))

        self.widget = W.VBox([style, toolbar, legend, panels, self.status],
                             layout=W.Layout(width="100%"))
        self.widget.add_class("ifc-viewer-root")

    def _legend_html(self) -> str:
        def chip(c, t):
            return (f'<span style="display:inline-block;width:11px;height:11px;'
                    f'background:{c};border:1px solid #333;margin:0 3px 0 10px;'
                    f'vertical-align:middle"></span>{t}')
        base = ("<div style='font-size:11px;color:#888'>Tipler:"
                + chip(TYPE_COLOR["IfcWall"], "Duvar")
                + chip(TYPE_COLOR["IfcDoor"], "Kapı")
                + chip(TYPE_COLOR["IfcWindow"], "Pencere")
                + chip(TYPE_COLOR["IfcSlab"], "Döşeme")
                + chip(SELECT_COLOR, "Seçili"))
        if self.labels:
            base += ("&nbsp;&nbsp;|&nbsp;&nbsp;İhlal katmanı:"
                     + chip(LABEL_COLOR["violation"], "🔴 İhlal")
                     + chip(LABEL_COLOR["decoy"], "🟡 Sahte (decoy)")
                     + chip(LABEL_COLOR["compliant"], "🟢 Uyumlu ekleme"))
        return base + "</div>"

    # --- olay işleyiciler ---
    def _on_pick(self, change):
        obj = change.get("new")
        if obj is not None and getattr(obj, "name", None) in self.vm.elements:
            self.select(obj.name)

    def _on_node(self, node):
        ek = node.get("data", {}).get("id") if isinstance(node, dict) else None
        if ek in self.vm.elements:
            self.select(ek)

    def _on_select(self, change):
        self.select(change["new"] or None)

    # --- ortak seçim ---
    def select(self, ekey: Optional[str]):
        self.selected = ekey
        set_mesh_selection(self.meshes, self.vm, ekey, self.labels)
        set_graph_selection(self.cyto, self.vm, ekey)
        idxs = set(self.vm.highlight_line_indices(ekey)) if ekey else set()
        self.ifc_box.value = ifc_text_html(self.vm, idxs)
        self.detail_box.value = detail_html(self.vm, ekey, self.labels)
        if getattr(self, "selector", None) is not None:
            self.selector.value = ekey or ""
        if ekey:
            el = self.vm.elements[ekey]
            self.status.value = (f"Seçili: <b>{el.name}</b> "
                                 f"({el.ifc_type}, #{el.ifc_id}) — "
                                 f"{len(idxs)} IFC satırı vurgulandı")
        else:
            self.status.value = "<i>Seçim yok</i>"

    def show(self):
        from IPython.display import display
        display(self.widget)
        return self.widget


# ============================================================================
# Tek-çağrı API — başka notebook'lardan kolay kullanım
# ============================================================================
def view(source, labels=None, display: bool = True) -> "InteractiveViewer":
    """Herhangi bir notebook'tan tek satırla görselleştir.

        from viewer import view
        v = view("data/baseline_ifc/xxx.ifc")          # IFC yolu
        v = view(vm, labels={ekey: "violation"})       # ViewerModel + ihlal renkleri

    `source`: IFC dosya yolu (str/Path) ya da hazır ViewerModel.
    `labels`: {ekey: "violation"|"decoy"|"compliant"} — viewer'da 🔴/🟡/🟢.
    """
    from .model import load_viewer_model, ViewerModel, load_labels

    if isinstance(source, ViewerModel):
        vm = source
    else:
        vm = load_viewer_model(source)

    if isinstance(labels, (str,)) or hasattr(labels, "__fspath__"):
        labels = load_labels(labels)

    iv = InteractiveViewer(vm, labels=labels)
    if display:
        iv.show()
    return iv
