"""Faz 1.1 — Kural tabanlı motorlu baseline ÜRETİCİ (parametrik, çok varyantlı).

Topoloji (dikdörtgen/kare bina):

    +------------------------------------+  y=D
    |   Oda1    |   Oda2    |   Oda3      |   <- üst bant: yan yana 3 oda
    +-----------+-----------+-------------+
    |             KORİDOR (tam genişlik)  |   <- orta bant: yatay koridor
    +------------------------------------+
    |             SALON (tam genişlik)    |   <- alt bant: salon
    +------------------------------------+  y=0
   x=0                                  x=W

Parametreler (BaselineConfig):
  - doors_per_room : her oda/salonda kaç kapı (varsayılan 3)
  - room_min/max   : oda kenar boyutları (m) (varsayılan 3 / 5)
  - corridor_min/max : koridor genişlik (kalınlık) ve uzunluk aralığı (varsayılan 3 / 5)
  - shape          : "rectangle" | "square" (varsayılan rectangle)
  - n_baselines    : bu konfigürasyonla kaç farklı baseline üretilecek (varsayılan 1)
  - height, wall_thickness, seed

Notlar (varsayılan ek davranışlar — istenirse kaldırılır):
  * Baseline'ın kurallara uygun olması için her oda/salona R2'yi (pencere/taban ≥%10)
    sağlayacak birer pencere eklenir.
  * Koridor sirkülasyon mekânıdır; R2 onun için aranmaz (bkz. inject/rules.py).

Kullanım (notebook):
    from ifc_gen.baseline.procedural import BaselineConfig, generate_baselines
    cfg = BaselineConfig(doors_per_room=3, n_baselines=3)
    sonuc = generate_baselines(cfg)   # [{path, meta}, ...]
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from .layout import BuildingLayout, Wall, Opening, Room
from .rule_based import build_baseline


@dataclass
class BaselineConfig:
    doors_per_room: int = 3
    room_min: float = 3.0
    room_max: float = 5.0
    corridor_min: float = 3.0
    corridor_max: float = 5.0
    shape: str = "rectangle"        # "rectangle" | "square"
    n_baselines: int = 1
    height: float = 3.0
    wall_thickness: float = 0.2
    seed: Optional[int] = None


# ---------------------------------------------------------------------------
def _dist_along(wall: Wall, x: float, y: float) -> float:
    """(x,y) noktasının duvar başlangıcından eksen boyu uzaklığı."""
    (sx, sy), (ex, ey) = wall.start, wall.end
    L = wall.length or 1.0
    dx, dy = (ex - sx) / L, (ey - sy) / L
    return (x - sx) * dx + (y - sy) * dy


def _r(v: float) -> float:
    return round(v, 2)


def generate_layout(cfg: BaselineConfig, rng: random.Random,
                    name: str = "Baseline-Proc") -> BuildingLayout:
    """Tek bir baseline yerleşimi üretir (parametreleri rng ile örnekler)."""
    t = cfg.wall_thickness
    h = cfg.height

    # --- boyutlandırma ---
    r = [_r(rng.uniform(cfg.room_min, cfg.room_max)) for _ in range(3)]  # oda genişlikleri
    W = _r(sum(r))
    dt = _r(rng.uniform(cfg.room_min, cfg.room_max))                      # üst oda derinliği
    ct = _r(rng.uniform(cfg.corridor_min, cfg.corridor_max))             # koridor kalınlığı
    ds = _r(rng.uniform((cfg.room_min + cfg.room_max) / 2, cfg.room_max))  # salon derinliği (büyükçe)

    if cfg.shape == "square":
        # Footprint kare olsun: D = W olacak şekilde bantları dağıt
        rem = W - ct
        if rem < 2 * cfg.room_min:
            ct = _r(max(0.8, W - 2 * cfg.room_min))
            rem = W - ct
        dt = _r(rem * 0.45)
        ds = _r(rem * 0.55)
    D = _r(dt + ct + ds)

    yb = _r(ds + ct)        # üst odaların alt kenarı (= koridor üstü)
    x0, x1, x2, x3 = 0.0, r[0], _r(r[0] + r[1]), W

    # --- duvarlar ---
    walls = [
        Wall("DIS-Alt",  (0.0, 0.0), (W, 0.0), t, h, True),
        Wall("DIS-Sag",  (W, 0.0),   (W, D),   t, h, True),
        Wall("DIS-Ust",  (W, D),     (0.0, D), t, h, True),
        Wall("DIS-Sol",  (0.0, D),   (0.0, 0.0), t, h, True),
        Wall("KOR-Alt",  (0.0, ds),  (W, ds),  t, h, False),   # salon | koridor
        Wall("KOR-Ust",  (0.0, yb),  (W, yb),  t, h, False),   # koridor | odalar
        Wall("IC-V1",    (x1, yb),   (x1, D),  t, h, False),   # oda1 | oda2
        Wall("IC-V2",    (x2, yb),   (x2, D),  t, h, False),   # oda2 | oda3
    ]
    wmap = {w.name: w for w in walls}

    # --- mekânlar ---
    rooms = [
        Room("Oda1",    (x0, yb), (x1, D)),
        Room("Oda2",    (x1, yb), (x2, D)),
        Room("Oda3",    (x2, yb), (x3, D)),
        Room("Koridor", (0.0, ds), (W, yb)),
        Room("Salon",   (0.0, 0.0), (W, ds)),
    ]

    openings: list[Opening] = []
    occ: dict[str, list[tuple[float, float]]] = {}

    def free_center(wall: Wall, lo: float, hi: float, width: float,
                    margin: float = 0.35) -> Optional[float]:
        half = width / 2 + 0.15
        a, b = min(lo, hi) + half + margin, max(lo, hi) - half - margin
        if b < a:
            return None
        cands = [(a + b) / 2, a + (b - a) * 0.3, a + (b - a) * 0.7, a, b]
        cands += [a + (b - a) * (i / 20.0) for i in range(21)]
        for c in cands:
            lo2, hi2 = c - half, c + half
            if all(hi2 <= oa or lo2 >= ob for oa, ob in occ.get(wall.name, [])):
                occ.setdefault(wall.name, []).append((lo2, hi2))
                return _r(c)
        return None

    def place(wall: Wall, p0, p1, kind: str, width: float, height: float,
              sill: float, name: str) -> bool:
        lo = _dist_along(wall, *p0)
        hi = _dist_along(wall, *p1)
        c = free_center(wall, lo, hi, width)
        if c is None:
            return False
        openings.append(Opening(name, kind, wall.name, distance=c,
                                width=width, height=height, sill=sill))
        return True

    def door_w(wall: Wall) -> float:
        return 1.0 if wall.is_external else 0.9   # R1: dış/giriş ≥1.0, iç ≥0.9

    # Her habitable mekân için: kapı duvarları (sıralı) + pencere duvarı
    yt = D
    specs = {
        # mekân: (kapı_duvarları[(wall, p0, p1)], pencere_duvarı(wall,p0,p1), taban_alanı)
        "Oda1": ([(wmap["KOR-Ust"], (x0, yb), (x1, yb)),
                  (wmap["DIS-Sol"], (0.0, yb), (0.0, yt)),
                  (wmap["IC-V1"],   (x1, yb), (x1, yt))],
                 (wmap["DIS-Ust"], (x0, yt), (x1, yt)), r[0] * dt),
        "Oda2": ([(wmap["KOR-Ust"], (x1, yb), (x2, yb)),
                  (wmap["IC-V1"],   (x1, yb), (x1, yt)),
                  (wmap["IC-V2"],   (x2, yb), (x2, yt))],
                 (wmap["DIS-Ust"], (x1, yt), (x2, yt)), r[1] * dt),
        "Oda3": ([(wmap["KOR-Ust"], (x2, yb), (x3, yb)),
                  (wmap["DIS-Sag"], (W, yb), (W, yt)),
                  (wmap["IC-V2"],   (x2, yb), (x2, yt))],
                 (wmap["DIS-Ust"], (x2, yt), (x3, yt)), r[2] * dt),
        "Salon": ([(wmap["KOR-Alt"], (0.0, ds), (W, ds)),
                   (wmap["DIS-Alt"], (0.0, 0.0), (W, 0.0)),
                   (wmap["DIS-Sol"], (0.0, 0.0), (0.0, ds)),
                   (wmap["DIS-Sag"], (W, 0.0), (W, ds))],
                  (wmap["DIS-Alt"], (0.0, 0.0), (W, 0.0)), W * ds),
    }

    for sp, (door_walls, win_spec, area) in specs.items():
        # kapılar
        placed = 0
        k = 0
        while placed < cfg.doors_per_room and k < cfg.doors_per_room * 3:
            wall, p0, p1 = door_walls[k % len(door_walls)]
            if place(wall, p0, p1, "door", door_w(wall), 2.1, 0.0,
                     f"Kapi-{sp}-{placed+1}"):
                placed += 1
            k += 1
        # pencere (R2: alan ≥ %10 taban)
        ww, wp0, wp1 = win_spec
        win_w = max(0.8, _r(0.105 * area / 1.4))     # yükseklik 1.4 sabit
        if not place(ww, wp0, wp1, "window", win_w, 1.4, 0.9, f"Pencere-{sp}"):
            # olmadıysa küçük bir pencere dene
            place(ww, wp0, wp1, "window", 1.0, 1.4, 0.9, f"Pencere-{sp}")

    params = {
        "kind": "procedural", "shape": cfg.shape,
        "width": W, "depth": D,
        "room_widths": r, "top_depth": dt, "corridor": ct, "salon_depth": ds,
        "height": h, "wall_thickness": t,
        "doors_per_room": cfg.doors_per_room,
        "spaces": ["Oda1", "Oda2", "Oda3", "Koridor", "Salon"],
        "config": asdict(cfg),
    }
    return BuildingLayout(name=name, storey_height=h, walls=walls,
                          openings=openings, rooms=rooms, params=params)


def generate_baselines(cfg: BaselineConfig = BaselineConfig(),
                       out_dir: Optional[Path] = None) -> list[dict]:
    """cfg.n_baselines kadar farklı baseline üretir, her birini IFC + meta olarak yazar.

    Dönüş: [{ "ifc_path": Path, "meta": dict, "layout": BuildingLayout }, ...]
    """
    base_seed = cfg.seed if cfg.seed is not None else random.randrange(1 << 30)
    from datetime import datetime, timezone
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    results = []
    for i in range(cfg.n_baselines):
        rng = random.Random(base_seed + i)
        layout = generate_layout(cfg, rng, name=f"Baseline-Proc-{i+1}")
        layout.params["seed"] = base_seed + i
        fname = f"baseline_proc_{stamp}_{i+1}.ifc"
        _, ifc_path, meta = build_baseline(layout, out_dir=out_dir, filename=fname)
        results.append({"ifc_path": ifc_path, "meta": meta, "layout": layout})
    return results


if __name__ == "__main__":
    res = generate_baselines(BaselineConfig(n_baselines=2, seed=42))
    for r in res:
        print(r["ifc_path"].name, "->", r["meta"]["counts"])
