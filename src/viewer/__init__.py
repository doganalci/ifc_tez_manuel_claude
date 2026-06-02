"""Faz 4 — Görüntüleme modülü.

IFC dosyasını parse edip üç görünümü (3D, graph, IFC metni) tek bir ortak veri
modeli üzerinden birbirine bağlar. Senkron seçim/vurgu bu model üzerinden yürür.

Hızlı kullanım (herhangi bir notebook'tan):

    from viewer import view
    view("data/baseline_ifc/xxx.ifc")                       # baseline
    view(ifc_path, labels={ekey: "violation"})              # ihlal renkleriyle
    view(ifc_path, labels="data/violated_ifc/xxx.meta.json")  # etiket dosyasından
"""
from .model import (  # noqa: F401
    ViewerModel, Element, load_viewer_model, load_labels,
)
from .render import InteractiveViewer, view  # noqa: F401

__all__ = [
    "view", "InteractiveViewer",
    "ViewerModel", "Element", "load_viewer_model", "load_labels",
]
