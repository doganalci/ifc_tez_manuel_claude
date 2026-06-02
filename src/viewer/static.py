"""Statik önizlemeler (matplotlib) — notebook'ta her ortamda görsel üretir.

İnteraktif widget'lar canlı Jupyter çekirdeği ister; bu fonksiyonlar ise her
yerde (nbconvert dahil) PNG üretir. Aynı seçim/renk mantığını gösterir.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .model import ViewerModel
from .render import TYPE_COLOR, SELECT_COLOR, LABEL_COLOR, _DEFAULT


def _color(el, labels, selected):
    if el.ekey == selected:
        return SELECT_COLOR
    if el.ekey in labels and labels[el.ekey] in LABEL_COLOR:
        return LABEL_COLOR[labels[el.ekey]]
    return TYPE_COLOR.get(el.ifc_type, _DEFAULT)


def plot_3d(vm: ViewerModel, selected: Optional[str] = None,
            labels: dict[str, str] | None = None, ax=None):
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    labels = labels or {}
    if ax is None:
        fig = plt.figure(figsize=(7, 5))
        ax = fig.add_subplot(111, projection="3d")
    allpts = []
    for ek, el in vm.elements.items():
        if el.verts is None or el.faces is None or not len(el.faces):
            continue
        if el.ifc_type == "IfcSpace" and ek != selected:
            continue  # mekanlar kalabalık yapmasın
        tris = el.verts[el.faces]
        allpts.append(el.verts)
        col = _color(el, labels, selected)
        pc = Poly3DCollection(tris, alpha=1.0 if ek == selected else 0.85,
                              facecolor=col, edgecolor="#222", linewidths=0.2)
        ax.add_collection3d(pc)
    if allpts:
        pts = np.vstack(allpts)
        mn, mx = pts.min(0), pts.max(0)
        ax.set_xlim(mn[0], mx[0]); ax.set_ylim(mn[1], mx[1]); ax.set_zlim(mn[2], mx[2])
        try:
            ax.set_box_aspect(mx - mn)
        except Exception:
            pass
    ax.set_title("3D Model" + (f" — seçili: {vm.elements[selected].name}"
                               if selected else ""))
    ax.view_init(elev=25, azim=-60)
    return ax


def plot_graph(vm: ViewerModel, selected: Optional[str] = None,
               labels: dict[str, str] | None = None, ax=None, seed: int = 7):
    import matplotlib.pyplot as plt
    import networkx as nx

    labels = labels or {}
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 5))
    g = nx.DiGraph()
    for ek, el in vm.elements.items():
        g.add_node(ek, label=el.name)
    for s, d, r in vm.edges:
        g.add_edge(s, d, rel=r)
    pos = nx.spring_layout(g, seed=seed, k=0.7)
    node_colors = [_color(vm.elements[n], labels, selected) for n in g.nodes]
    sizes = [620 if n == selected else 320 for n in g.nodes]
    edge_colors = [SELECT_COLOR if selected in (s, d) else "#bbb"
                   for s, d in g.edges]
    nx.draw_networkx_edges(g, pos, ax=ax, edge_color=edge_colors,
                           arrows=True, arrowsize=8, width=1.0)
    nx.draw_networkx_nodes(g, pos, ax=ax, node_color=node_colors,
                           node_size=sizes, edgecolors="#333")
    nx.draw_networkx_labels(g, pos, ax=ax,
                            labels={n: vm.elements[n].name for n in g.nodes},
                            font_size=7)
    ax.set_title("Graph" + (f" — seçili: {vm.elements[selected].name}"
                            if selected else ""))
    ax.axis("off")
    return ax
