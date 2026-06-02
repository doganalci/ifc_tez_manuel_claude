"""Faz 3.1 — Kural tabanlı (motorlu) ihlal ekleme.

LLM YOK. Baseline yerleşimini deterministik olarak mutasyona uğratıp ihlal,
sahte ihlal (decoy) ve uyumlu ekleme (compliant) üretir; geçerli bir violated
IFC + `*.meta.json` (ground-truth etiketler) yazar.

Etiketler `ekey` (GlobalId) ile saklanır → viewer doğrudan renklendirir:
    from viewer import view
    view(violated_path, labels=str(meta_path))

Manuel kullanım:
    inj = ViolationInjector()
    inj.narrow_door("Kapi-IC1")          # R1 -> 🔴
    inj.remove_window("Pencere-R2")      # R2 -> 🔴 (oda)
    inj.mark_decoy("Kapi-Giris")         # 🟡 (IFC değişmez)
    inj.add_compliant_column((6, 4))     # 🟢
    model, ifc_path, meta = inj.build()
"""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import ifcopenshell

from ..baseline.layout import BuildingLayout, Column, medium_layout
from ..baseline.rule_based import layout_to_ifc
from .. import paths
from .rules import RULES


class ViolationInjector:
    def __init__(self, layout: Optional[BuildingLayout] = None,
                 rules: Optional[dict] = None):
        self.layout = copy.deepcopy(layout) if layout else medium_layout()
        self.rules = rules or RULES
        # ham etiketler: isimle (build'de GlobalId'ye çözülür)
        self._ann: list[dict] = []
        self._mutations: list[str] = []

    # --- yardımcılar ---
    def _find_opening(self, name: str):
        for op in self.layout.openings:
            if op.name == name:
                return op
        raise KeyError(f"Açıklık bulunamadı: {name}")

    def _room_of_window(self, op) -> Optional[str]:
        """Üst duvardaki pencerenin (plan x'ine göre) ait olduğu odayı bul."""
        width = self.layout.params.get("width", 12.0)
        cx = width - op.distance  # DIS-Ust start=(width,depth)
        for rm in self.layout.rooms:
            if rm.min_xy[0] - 1e-6 <= cx <= rm.max_xy[0] + 1e-6:
                return rm.name
        return None

    # --- R1: dar kapı ---
    def narrow_door(self, door_name: str, new_width: float = 0.70):
        op = self._find_opening(door_name)
        r1 = self.rules["R1_min_door_width"]
        # giriş mi? bağlı duvar dış mı (DIS- ön eki) — basit kural
        thr = r1["entrance"] if op.wall_name.startswith("DIS") else r1["inner"]
        op.width = new_width
        self._mutations.append(f"narrow_door({door_name}, {new_width})")
        self._ann.append(dict(name=door_name, status="violation",
                              rule="R1_min_door_width",
                              detail=f"genişlik {new_width:.2f} m < {thr:.2f} m"))
        return self

    # --- R2: pencere kaldır (oranı düşür) ---
    def remove_window(self, window_name: str):
        op = self._find_opening(window_name)
        room = self._room_of_window(op)
        self.layout.openings = [o for o in self.layout.openings if o.name != window_name]
        self._mutations.append(f"remove_window({window_name})")
        # etkilenen odayı işaretle (pencere artık yok, onu işaretleyemeyiz)
        if room:
            self._ann.append(dict(name=room, status="violation",
                                  rule="R2_window_floor_ratio",
                                  detail=f"{window_name} kaldırıldı → pencere/taban oranı düştü"))
        return self

    # --- R3: düşük kat yüksekliği (global) ---
    def low_ceiling(self, new_height: float = 2.20):
        thr = self.rules["R3_min_ceiling_height"]["min_height"]
        self.layout.storey_height = new_height
        for w in self.layout.walls:
            w.height = new_height
        for c in self.layout.columns:
            c.height = new_height
        self._mutations.append(f"low_ceiling({new_height})")
        for w in self.layout.walls:
            self._ann.append(dict(name=w.name, status="violation",
                                  rule="R3_min_ceiling_height",
                                  detail=f"kat yüksekliği {new_height:.2f} m < {thr:.2f} m"))
        return self

    # --- Sahte ihlal (decoy): IFC değişmez ---
    def mark_decoy(self, name: str, rule: str = "R1_min_door_width"):
        self._ann.append(dict(name=name, status="decoy", rule=rule,
                              detail="etiket: ihlal — gerçekte kurala uygun (IFC değişmedi)"))
        return self

    # --- Uyumlu ekleme (compliant): kural bozmayan yeni kolon ---
    def add_compliant_column(self, at: tuple[float, float],
                             name: str = "Kolon-Ek", size: float = 0.3):
        h = self.layout.storey_height
        self.layout.columns.append(Column(name=name, at=at, size=size, height=h))
        self._mutations.append(f"add_compliant_column({name}@{at})")
        self._ann.append(dict(name=name, status="compliant", rule="-",
                              detail="kural bozmayan uyumlu ekleme"))
        return self

    # --- Üret ---
    def build(self, out_dir: Optional[Path] = None,
              filename: Optional[str] = None) -> tuple[ifcopenshell.file, Path, dict]:
        out_dir = Path(out_dir) if out_dir else paths.violated_ifc_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc)
        stamp = ts.strftime("%Y%m%d_%H%M%S")
        filename = filename or f"violated_rule_{stamp}.ifc"
        ifc_path = out_dir / filename

        model = layout_to_ifc(self.layout)
        model.write(str(ifc_path))

        # isim -> GlobalId (etiketleri çöz)
        name2gid: dict[str, str] = {}
        for t in ("IfcWall", "IfcDoor", "IfcWindow", "IfcSpace", "IfcColumn", "IfcSlab"):
            for e in model.by_type(t):
                if getattr(e, "Name", None):
                    name2gid[e.Name] = e.GlobalId

        annotations = []
        for a in self._ann:
            gid = name2gid.get(a["name"])
            if not gid:
                continue
            annotations.append({"ekey": gid, "name": a["name"],
                                "status": a["status"], "rule": a["rule"],
                                "detail": a["detail"]})

        meta = {
            "method": "rule_based_injection",   # Faz 3.1
            "engine": "ifcopenshell",
            "schema": model.schema,
            "source": "baseline (medium params)",
            "params": self.layout.params,
            "rules_config": self.rules,
            "mutations": self._mutations,
            "annotations": annotations,
            "counts": {st: sum(1 for a in annotations if a["status"] == st)
                       for st in ("violation", "decoy", "compliant")},
            "timestamp": ts.isoformat(),
            "ifc_file": ifc_path.name,
        }
        meta_path = ifc_path.with_suffix(".meta.json")
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                             encoding="utf-8")
        return model, ifc_path, meta


def inject_demo() -> tuple[ifcopenshell.file, Path, dict]:
    """Her durumdan birer örnek: 🔴 dar kapı + 🔴 pencere kaldırma, 🟡 decoy, 🟢 kolon."""
    inj = ViolationInjector()
    inj.narrow_door("Kapi-IC1", new_width=0.70)     # R1 🔴
    inj.remove_window("Pencere-R2")                 # R2 🔴 (oda R2)
    inj.mark_decoy("Kapi-Giris")                    # 🟡 (uygun ama 'ihlal' denmiş)
    inj.add_compliant_column((6.0, 4.0))            # 🟢
    return inj.build()


if __name__ == "__main__":
    _, path, meta = inject_demo()
    print("Yazıldı:", path)
    print(json.dumps(meta["counts"], indent=2))
