"""Kural seti — eşikler + ölçüm + tespit (tek kaynak).

`docs/kural_seti.md` ile birebir. Hem ihlal üretimi (injector) hem de doğrulama
(üretilen ihlalin gerçekten kuralı bozduğunu kontrol) bu modülü kullanır.

Eşikler parametrik; ileride train/test perturbation için `RULES` kopyalanıp
değiştirilebilir.
"""
from __future__ import annotations

from dataclasses import dataclass

# Varsayılan eşikler (metre / oran)
RULES = {
    "R1_min_door_width":     {"inner": 0.90, "entrance": 1.00},  # m
    "R2_window_floor_ratio": {"min_ratio": 0.10},                # -
    "R3_min_ceiling_height": {"min_height": 2.40},               # m
    # "R4_...": gelecek (kullanıcı kuralı)
}


@dataclass
class Finding:
    ekey: str
    rule: str
    violated: bool
    value: float
    threshold: float
    detail: str


# ---------------------------------------------------------------------------
# Ölçüm yardımcıları (bir ViewerModel üzerinden — herhangi bir IFC için çalışır)
# ---------------------------------------------------------------------------
def _door_width(vm, ekey) -> float:
    """Kapı net genişliği (OverallWidth, yoksa bbox plan genişliği)."""
    ent = vm.ifc_file.by_id(vm.elements[ekey].ifc_id)
    if getattr(ent, "OverallWidth", None):
        return float(ent.OverallWidth)
    d = vm.dimensions(ekey)
    return max(d[0], d[1]) if d else 0.0


def _is_entrance(vm, ekey) -> bool:
    """Kapı dış duvarda mı? (hosts ilişkisindeki duvarın IsExternal'ı)."""
    for nek, rel, dirn in vm.neighbors(ekey):
        if rel == "hosts" and dirn == "<-":  # duvar -> kapı
            ps = vm.psets(nek).get("Pset_WallCommon", {})
            return bool(ps.get("IsExternal"))
    return False


def _window_area(vm, ekey) -> float:
    ent = vm.ifc_file.by_id(vm.elements[ekey].ifc_id)
    w = getattr(ent, "OverallWidth", None)
    h = getattr(ent, "OverallHeight", None)
    if w and h:
        return float(w) * float(h)
    d = vm.dimensions(ekey)
    return (max(d[0], d[1]) * d[2]) if d else 0.0


def _room_floor_area(vm, ekey) -> float:
    d = vm.dimensions(ekey)
    return d[0] * d[1] if d else 0.0


def _ceiling_height(vm, ekey) -> float:
    """Duvar yüksekliği = net kat yüksekliği (bbox z)."""
    d = vm.dimensions(ekey)
    return d[2] if d else 0.0


# ---------------------------------------------------------------------------
# Tespit — bir ViewerModel'deki ihlalleri tarar (ground-truth doğrulama için)
# ---------------------------------------------------------------------------
def detect(vm, rules: dict | None = None) -> list[Finding]:
    rules = rules or RULES
    out: list[Finding] = []

    # R1 — kapı genişliği
    r1 = rules.get("R1_min_door_width")
    if r1:
        for ek, el in vm.elements.items():
            if el.ifc_type != "IfcDoor":
                continue
            thr = r1["entrance"] if _is_entrance(vm, ek) else r1["inner"]
            w = _door_width(vm, ek)
            out.append(Finding(ek, "R1_min_door_width", w < thr - 1e-6, w, thr,
                               f"genişlik {w:.2f} m {'<' if w < thr else '≥'} {thr:.2f} m"))

    # R2 — pencere/taban oranı (oda bazında)
    r2 = rules.get("R2_window_floor_ratio")
    if r2:
        thr = r2["min_ratio"]
        for ek, el in vm.elements.items():
            if el.ifc_type != "IfcSpace":
                continue
            floor = _room_floor_area(vm, ek)
            win_area = sum(_window_area(vm, nek)
                           for nek, rel, _ in vm.neighbors(ek)
                           if rel == "bounds" and vm.elements[nek].ifc_type == "IfcWindow")
            ratio = (win_area / floor) if floor else 0.0
            out.append(Finding(ek, "R2_window_floor_ratio", ratio < thr - 1e-6,
                               ratio, thr,
                               f"oran {ratio*100:.1f}% {'<' if ratio < thr else '≥'} {thr*100:.0f}%"))

    # R3 — kat yüksekliği (duvar bazında)
    r3 = rules.get("R3_min_ceiling_height")
    if r3:
        thr = r3["min_height"]
        for ek, el in vm.elements.items():
            if el.ifc_type not in ("IfcWall", "IfcWallStandardCase"):
                continue
            h = _ceiling_height(vm, ek)
            out.append(Finding(ek, "R3_min_ceiling_height", h < thr - 1e-6, h, thr,
                               f"yükseklik {h:.2f} m {'<' if h < thr else '≥'} {thr:.2f} m"))
    return out


def violations_only(vm, rules: dict | None = None) -> list[Finding]:
    return [f for f in detect(vm, rules) if f.violated]
