"""IFC -> ViewerModel parse.

Üç görünümü tek modelde birleştirir:
  - 3D  : her elemanın üçgen mesh'i (dünya koordinatında verts + faces)
  - graph: node = eleman (whitelist tip), edge = IFC ilişkisi / mekan üyeliği
  - IFC metni: her elemanın ilgili STEP satır no'ları (vurgulama için)

Ortak anahtar: `ekey` = elemanın GlobalId'si. Seçim hep bu anahtarla yürür.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import ifcopenshell
import ifcopenshell.geom

# Graph'ta gösterilecek eleman tipleri (yardımcı node'lar dışarıda).
NODE_WHITELIST = (
    "IfcWall", "IfcWallStandardCase", "IfcDoor", "IfcWindow",
    "IfcColumn", "IfcSlab", "IfcStair", "IfcRamp", "IfcSpace",
)

# IFC satır kapanışında izlenmeyecek (paylaşılan/gürültü) tipler.
_LINE_BLOCKLIST = (
    "IfcGeometricRepresentationContext", "IfcGeometricRepresentationSubContext",
    "IfcOwnerHistory", "IfcProject", "IfcUnitAssignment", "IfcSIUnit",
    "IfcDimensionalExponents", "IfcConversionBasedUnit", "IfcMeasureWithUnit",
)


@dataclass
class Element:
    ekey: str                      # GlobalId — ortak anahtar
    ifc_id: int                    # STEP #id
    ifc_type: str
    name: str
    line_ids: list[int] = field(default_factory=list)   # ilgili STEP #id'leri
    verts: Optional[np.ndarray] = None                  # (N,3) dünya koord.
    faces: Optional[np.ndarray] = None                  # (M,3) üçgen indeks
    bbox_min: Optional[np.ndarray] = None
    bbox_max: Optional[np.ndarray] = None

    @property
    def centroid(self) -> Optional[np.ndarray]:
        if self.bbox_min is None:
            return None
        return (self.bbox_min + self.bbox_max) / 2.0


@dataclass
class ViewerModel:
    path: str
    schema: str
    elements: dict[str, Element]              # ekey -> Element
    edges: list[tuple[str, str, str]]         # (src_ekey, dst_ekey, rel)
    ifc_lines: list[str]                      # STEP dosyasının satırları
    id_to_lineidx: dict[int, int]             # STEP #id -> satır indeksi
    line_to_ekey: dict[int, str]              # STEP #id -> ekey (IFC tıklaması için)

    def element_by_ifc_id(self, ifc_id: int) -> Optional[Element]:
        """Bir STEP #id'sinden ilgili elemanı bul (IFC görünümünden seçim)."""
        ek = self.line_to_ekey.get(ifc_id)
        return self.elements.get(ek) if ek else None

    def highlight_line_indices(self, ekey: str) -> list[int]:
        """Bir eleman seçilince IFC metninde vurgulanacak satır indeksleri."""
        el = self.elements.get(ekey)
        if not el:
            return []
        return sorted(self.id_to_lineidx[i] for i in el.line_ids
                      if i in self.id_to_lineidx)


# ----------------------------------------------------------------------------
def _related_line_ids(entity, max_depth: int = 2, cap: int = 40) -> list[int]:
    """Elemanın STEP'te 'ilgili' satırları: kendisi + yerleşim/temsil kapanışı."""
    seen: set[int] = set()
    stack = [(entity, 0)]
    while stack and len(seen) < cap:
        ent, depth = stack.pop()
        try:
            eid = ent.id()
        except Exception:
            continue
        if eid in seen or eid == 0:
            continue
        if ent.is_a() in _LINE_BLOCKLIST:
            continue
        seen.add(eid)
        if depth >= max_depth:
            continue
        for attr in ent:
            vals = attr if isinstance(attr, (list, tuple)) else [attr]
            for v in vals:
                if isinstance(v, ifcopenshell.entity_instance):
                    stack.append((v, depth + 1))
    return sorted(seen)


def _bbox_overlap_xy(a: Element, b: Element, tol: float = 0.3) -> bool:
    if a.bbox_min is None or b.bbox_min is None:
        return False
    return (
        a.bbox_min[0] - tol <= b.bbox_max[0] and a.bbox_max[0] + tol >= b.bbox_min[0]
        and a.bbox_min[1] - tol <= b.bbox_max[1] and a.bbox_max[1] + tol >= b.bbox_min[1]
    )


def load_viewer_model(path: str | Path) -> ViewerModel:
    path = str(path)
    f = ifcopenshell.open(path)

    # STEP #id -> satır metni eşlemesi (vurgulama için)
    raw_lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    id_to_lineidx: dict[int, int] = {}
    for idx, ln in enumerate(raw_lines):
        s = ln.lstrip()
        if s.startswith("#") and "=" in s:
            try:
                id_to_lineidx[int(s[1:s.index("=")].strip())] = idx
            except ValueError:
                pass

    # Whitelist elemanları topla
    elements: dict[str, Element] = {}
    for t in NODE_WHITELIST:
        for ent in f.by_type(t):
            gid = getattr(ent, "GlobalId", None)
            if not gid:
                continue
            elements[gid] = Element(
                ekey=gid, ifc_id=ent.id(), ifc_type=ent.is_a(),
                name=getattr(ent, "Name", None) or ent.is_a(),
                line_ids=_related_line_ids(ent),
            )

    # Geometri (dünya koordinatı) — guid ile eşle
    settings = ifcopenshell.geom.settings()
    try:
        settings.set("use-world-coords", True)
    except Exception:
        try:
            settings.set(settings.USE_WORLD_COORDS, True)
        except Exception:
            pass
    it = ifcopenshell.geom.iterator(settings, f)
    if it.initialize():
        while True:
            shape = it.get()
            gid = getattr(shape, "guid", None)
            el = elements.get(gid)
            if el is not None:
                verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
                faces = np.array(shape.geometry.faces, dtype=int).reshape(-1, 3)
                el.verts, el.faces = verts, faces
                if len(verts):
                    el.bbox_min = verts.min(axis=0)
                    el.bbox_max = verts.max(axis=0)
            if not it.next():
                break

    # IFC #id -> ekey (eleman ve ilgili satırların tıklamasını elemana bağla)
    line_to_ekey: dict[int, str] = {}
    for el in elements.values():
        for lid in el.line_ids:
            line_to_ekey.setdefault(lid, el.ekey)

    # Kenarlar
    edges: list[tuple[str, str, str]] = []
    seen_edge: set[tuple[str, str, str]] = set()

    def add_edge(s: str, d: str, rel: str):
        key = (s, d, rel)
        if s in elements and d in elements and s != d and key not in seen_edge:
            seen_edge.add(key)
            edges.append(key)

    # 1) Açık ilişki: duvar -> kapı/pencere (IfcRelVoids + IfcRelFills)
    for rv in f.by_type("IfcRelVoidsElement"):
        wall = rv.RelatingBuildingElement
        opening = rv.RelatedOpeningElement
        wall_gid = getattr(wall, "GlobalId", None)
        for rf in f.by_type("IfcRelFillsElement"):
            if rf.RelatingOpeningElement == opening:
                filler = rf.RelatedBuildingElement
                add_edge(wall_gid, getattr(filler, "GlobalId", None), "hosts")

    # 2) Mekan üyeliği: space <-> eleman (plan bbox örtüşmesi)
    spaces = [e for e in elements.values() if e.ifc_type == "IfcSpace"]
    others = [e for e in elements.values() if e.ifc_type != "IfcSpace"]
    for sp in spaces:
        for el in others:
            if _bbox_overlap_xy(sp, el):
                add_edge(sp.ekey, el.ekey, "bounds")

    return ViewerModel(
        path=path, schema=f.schema, elements=elements, edges=edges,
        ifc_lines=raw_lines, id_to_lineidx=id_to_lineidx,
        line_to_ekey=line_to_ekey,
    )
