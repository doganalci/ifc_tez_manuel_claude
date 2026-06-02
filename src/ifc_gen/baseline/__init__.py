"""Faz 1 — Baseline IFC üretimi.

Modüler fonksiyonlar; notebook'lardan (ve diğer fazlardan) çağrılır:

    from ifc_gen.baseline import medium_layout, layout_to_ifc, build_baseline

    layout = medium_layout(width=12, depth=8, height=3)   # tasarım verisi
    model, path, meta = build_baseline(layout)            # IFC üret + yaz + meta.json
"""
from .layout import (  # noqa: F401
    BuildingLayout, Wall, Opening, Room, Column, medium_layout,
)
from .rule_based import layout_to_ifc, build_baseline  # noqa: F401

__all__ = [
    "BuildingLayout", "Wall", "Opening", "Room", "Column", "medium_layout",
    "layout_to_ifc", "build_baseline",
]
