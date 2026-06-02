"""Faz 4 — Görüntüleme modülü.

IFC dosyasını parse edip üç görünümü (3D, graph, IFC metni) tek bir ortak veri
modeli üzerinden birbirine bağlar. Senkron seçim/vurgu bu model üzerinden yürür.
"""
from .model import ViewerModel, Element, load_viewer_model  # noqa: F401
