"""Faz 1.1 — Kural tabanlı (motorlu) baseline IFC üretimi.

LLM YOK. Tamamen deterministik: BuildingLayout verisini ifcopenshell yüksek
seviye API'si ile geçerli bir IFC4 modeline çevirir. Aynı parametre → aynı
çıktı (GlobalId hariç).

Kullanım (notebook veya CLI):
    from ifc_gen.baseline.rule_based import build_baseline
    model, path, meta = build_baseline()        # orta yerleşim, data/baseline_ifc/ altına yazar
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import ifcopenshell
from ifcopenshell.api import run

from .layout import BuildingLayout, Wall, Opening, medium_layout
from .. import paths


# ----------------------------------------------------------------------------
# Yardımcılar
# ----------------------------------------------------------------------------
def _placement_matrix(x: float, y: float, z: float, angle_rad: float) -> np.ndarray:
    """Z ekseni etrafında dönmüş, (x,y,z)'ye taşınmış 4x4 yerleşim matrisi."""
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    m = np.eye(4)
    m[0, 0], m[0, 1] = c, -s
    m[1, 0], m[1, 1] = s, c
    m[:3, 3] = (x, y, z)
    return m


def _wall_angle(w: Wall) -> float:
    (x0, y0), (x1, y1) = w.start, w.end
    return math.atan2(y1 - y0, x1 - x0)


def _point_along(w: Wall, distance: float) -> tuple[float, float]:
    (x0, y0), (x1, y1) = w.start, w.end
    L = w.length or 1.0
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    return (x0 + ux * distance, y0 + uy * distance)


# ----------------------------------------------------------------------------
# Motor
# ----------------------------------------------------------------------------
def layout_to_ifc(layout: BuildingLayout) -> ifcopenshell.file:
    """Bir BuildingLayout'tan tam bir IFC4 dosyası (in-memory) üretir."""
    f = run("project.create_file", version="IFC4")

    # Proje / birimler / geometri bağlamı
    project = run("root.create_entity", f, ifc_class="IfcProject", name=layout.name)
    run("unit.assign_unit", f)  # varsayılan SI (metre)
    model_ctx = run("context.add_context", f, context_type="Model")
    body = run(
        "context.add_context", f, context_type="Model",
        context_identifier="Body", target_view="MODEL_VIEW", parent=model_ctx,
    )

    # Mekansal hiyerarşi: Project > Site > Building > Storey
    site = run("root.create_entity", f, ifc_class="IfcSite", name="Saha")
    building = run("root.create_entity", f, ifc_class="IfcBuilding", name="Bina")
    storey = run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Kat-1")
    run("aggregate.assign_object", f, products=[site], relating_object=project)
    run("aggregate.assign_object", f, products=[building], relating_object=site)
    run("aggregate.assign_object", f, products=[storey], relating_object=building)

    wall_by_name: dict[str, ifcopenshell.entity_instance] = {}

    # --- Döşeme (zemin slab) ---
    p = layout.params
    w, d = p.get("width", 12.0), p.get("depth", 8.0)
    slab_t = 0.2
    slab = run("root.create_entity", f, ifc_class="IfcSlab", name="Doseme")
    slab_rep = run(
        "geometry.add_slab_representation", f, context=body, depth=slab_t,
        polyline=[(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)],
    )
    run("geometry.assign_representation", f, product=slab, representation=slab_rep)
    run("spatial.assign_container", f, products=[slab], relating_structure=storey)
    run("geometry.edit_object_placement", f, product=slab,
        matrix=_placement_matrix(0, 0, -slab_t, 0.0))

    # --- Duvarlar ---
    for wl in layout.walls:
        wall = run("root.create_entity", f, ifc_class="IfcWall", name=wl.name)
        rep = run("geometry.add_wall_representation", f, context=body,
                  length=wl.length, height=wl.height, thickness=wl.thickness)
        run("geometry.assign_representation", f, product=wall, representation=rep)
        run("spatial.assign_container", f, products=[wall], relating_structure=storey)
        run("geometry.edit_object_placement", f, product=wall,
            matrix=_placement_matrix(wl.start[0], wl.start[1], 0.0, _wall_angle(wl)))
        # Pset: dış/iç ayrımı (sonraki kural kontrolleri için faydalı)
        pset = run("pset.add_pset", f, product=wall, name="Pset_WallCommon")
        run("pset.edit_pset", f, pset=pset,
            properties={"IsExternal": bool(wl.is_external)})
        wall_by_name[wl.name] = wall

    # --- Kapı/Pencere (boşluk + dolgu) ---
    for op in layout.openings:
        host = wall_by_name.get(op.wall_name)
        if host is None:
            continue
        wl = next(x for x in layout.walls if x.name == op.wall_name)
        angle = _wall_angle(wl)
        # Boşluğun başlangıç noktası: duvar boyunca (distance - width/2)
        ox, oy = _point_along(wl, op.distance - op.width / 2.0)
        oz = op.sill

        opening = run("root.create_entity", f, ifc_class="IfcOpeningElement", name=f"{op.name}-bosluk")
        # Boşluk kutusu: duvardan kalın (tam kessin)
        op_rep = run("geometry.add_wall_representation", f, context=body,
                     length=op.width, height=op.height, thickness=wl.thickness + 0.1)
        run("geometry.assign_representation", f, product=opening, representation=op_rep)
        run("geometry.edit_object_placement", f, product=opening,
            matrix=_placement_matrix(ox, oy, oz, angle))
        run("feature.add_feature", f, feature=opening, element=host)

        if op.kind == "door":
            door = run("root.create_entity", f, ifc_class="IfcDoor", name=op.name)
            d_rep = run("geometry.add_door_representation", f, context=body,
                        overall_height=op.height, overall_width=op.width)
            run("geometry.assign_representation", f, product=door, representation=d_rep)
            run("geometry.edit_object_placement", f, product=door,
                matrix=_placement_matrix(ox, oy, oz, angle))
            run("spatial.assign_container", f, products=[door], relating_structure=storey)
            run("feature.add_filling", f, opening=opening, element=door)
        else:  # window
            win = run("root.create_entity", f, ifc_class="IfcWindow", name=op.name)
            wn_rep = run("geometry.add_window_representation", f, context=body,
                         overall_height=op.height, overall_width=op.width)
            run("geometry.assign_representation", f, product=win, representation=wn_rep)
            run("geometry.edit_object_placement", f, product=win,
                matrix=_placement_matrix(ox, oy, oz, angle))
            run("spatial.assign_container", f, products=[win], relating_structure=storey)
            run("feature.add_filling", f, opening=opening, element=win)

    # --- Mekanlar (IfcSpace) ---
    for rm in layout.rooms:
        (x0, y0), (x1, y1) = rm.min_xy, rm.max_xy
        space = run("root.create_entity", f, ifc_class="IfcSpace", name=rm.name)
        sp_rep = run("geometry.add_slab_representation", f, context=body,
                     depth=layout.storey_height,
                     polyline=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        run("geometry.assign_representation", f, product=space, representation=sp_rep)
        run("aggregate.assign_object", f, products=[space], relating_object=storey)
        run("geometry.edit_object_placement", f, product=space,
            matrix=_placement_matrix(0, 0, 0, 0.0))

    return f


def build_baseline(
    layout: Optional[BuildingLayout] = None,
    out_dir: Optional[Path] = None,
    filename: Optional[str] = None,
) -> tuple[ifcopenshell.file, Path, dict]:
    """Baseline IFC üret, `data/baseline_ifc/` altına yaz, meta.json kaydet.

    Dönüş: (ifc_model, ifc_path, meta_dict)
    """
    layout = layout or medium_layout()
    out_dir = Path(out_dir) if out_dir else paths.baseline_ifc_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc)
    stamp = ts.strftime("%Y%m%d_%H%M%S")
    filename = filename or f"baseline_rule_{stamp}.ifc"
    ifc_path = out_dir / filename

    model = layout_to_ifc(layout)
    model.write(str(ifc_path))

    meta = {
        "method": "rule_based",          # Faz 1.1
        "engine": "ifcopenshell",
        "ifcopenshell_version": ifcopenshell.version,
        "schema": model.schema,
        "layout": layout.name,
        "params": layout.params,
        "counts": {
            "IfcWall": len(model.by_type("IfcWall")),
            "IfcDoor": len(model.by_type("IfcDoor")),
            "IfcWindow": len(model.by_type("IfcWindow")),
            "IfcSpace": len(model.by_type("IfcSpace")),
            "IfcSlab": len(model.by_type("IfcSlab")),
            "IfcOpeningElement": len(model.by_type("IfcOpeningElement")),
        },
        "timestamp": ts.isoformat(),
        "ifc_file": ifc_path.name,
    }
    meta_path = ifc_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return model, ifc_path, meta


if __name__ == "__main__":
    _, path, meta = build_baseline()
    print(f"Yazıldı: {path}")
    print(json.dumps(meta["counts"], indent=2))
