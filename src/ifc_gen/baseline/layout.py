"""Baseline bina yerleşimi — saf veri (geometri motorundan bağımsız).

Bu modül "tasarım"ı tanımlar: duvar eksen çizgileri, odalar, kapı ve pencereler.
IFC üretmez; sadece kurallara uygun, deterministik bir yerleşim verisi döndürür.
Faz 1.1 motoru (rule_based.py) bu veriyi alıp IFC'ye çevirir.

Birim: metre. Koordinat: plan düzleminde (x, y), kat tabanı z=0.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Wall:
    name: str
    start: tuple[float, float]
    end: tuple[float, float]
    thickness: float = 0.2
    height: float = 3.0
    is_external: bool = True

    @property
    def length(self) -> float:
        (x0, y0), (x1, y1) = self.start, self.end
        return ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5


@dataclass
class Opening:
    """Bir duvardaki kapı veya pencere boşluğu + dolgusu."""
    name: str
    kind: str               # "door" | "window"
    wall_name: str          # hangi duvarda
    distance: float         # duvar başlangıcından (start) eksen boyu mesafe (m)
    width: float
    height: float
    sill: float = 0.0       # alt kot (kapı 0, pencere ~0.9)


@dataclass
class Column:
    name: str
    at: tuple[float, float]     # plan konumu (x, y)
    size: float = 0.3          # kare kesit kenarı (m)
    height: float = 3.0


@dataclass
class Room:
    name: str
    # eksen-hizalı dikdörtgen oda (iç net alan köşeleri)
    min_xy: tuple[float, float]
    max_xy: tuple[float, float]

    @property
    def center(self) -> tuple[float, float]:
        (x0, y0), (x1, y1) = self.min_xy, self.max_xy
        return ((x0 + x1) / 2, (y0 + y1) / 2)


@dataclass
class BuildingLayout:
    name: str
    storey_height: float
    walls: list[Wall] = field(default_factory=list)
    openings: list[Opening] = field(default_factory=list)
    rooms: list[Room] = field(default_factory=list)
    columns: list[Column] = field(default_factory=list)
    params: dict = field(default_factory=dict)


def medium_layout(
    width: float = 12.0,
    depth: float = 8.0,
    height: float = 3.0,
    wall_thickness: float = 0.2,
) -> BuildingLayout:
    """Orta kapsam: 1 kat, 3 oda (2 iç bölme duvarı), giriş + iç kapılar, pencereler.

    Plan (üstten görünüş, x→sağ, y→yukarı):

        (0,depth) +-----+-----+-----+ (width,depth)
                  |  R1 |  R2 |  R3 |   <- her odada üst pencere
                  | door|     |door |   <- iç kapılar (x=a ve x=b duvarında)
        (0,0)     +-----+--D--+-----+ (width,0)
                          giriş kapısı (R2 ön duvarı)
    """
    a = width / 3.0          # ilk iç duvar x'i
    b = 2.0 * width / 3.0    # ikinci iç duvar x'i
    t = wall_thickness

    walls = [
        # Dış kabuk (saat yönü)
        Wall("DIS-Alt",  (0.0, 0.0),     (width, 0.0),     t, height, True),
        Wall("DIS-Sag",  (width, 0.0),   (width, depth),   t, height, True),
        Wall("DIS-Ust",  (width, depth), (0.0, depth),     t, height, True),
        Wall("DIS-Sol",  (0.0, depth),   (0.0, 0.0),       t, height, True),
        # İç bölme duvarları (dikey)
        Wall("IC-1", (a, 0.0), (a, depth), t, height, False),
        Wall("IC-2", (b, 0.0), (b, depth), t, height, False),
    ]

    openings = [
        # Giriş kapısı: R2 ön (alt) duvarında, ortalı
        Opening("Kapi-Giris", "door", "DIS-Alt", distance=(a + b) / 2,
                width=1.0, height=2.1, sill=0.0),
        # İç kapılar (R1<->R2 ve R2<->R3)
        Opening("Kapi-IC1", "door", "IC-1", distance=depth / 2,
                width=0.9, height=2.1, sill=0.0),
        Opening("Kapi-IC2", "door", "IC-2", distance=depth / 2,
                width=0.9, height=2.1, sill=0.0),
        # Üst duvarda her oda için pencere (DIS-Ust start=(width,depth)->(0,depth))
        # distance, start'tan ölçülür: R3 merkezi width - b/2 ...
        # Boyut: oda ~32 m², R2 oranı (≥%10) için pencere ≥ ~3.2 m² (2.4×1.4=3.36)
        Opening("Pencere-R3", "window", "DIS-Ust", distance=width - (b + width) / 2,
                width=2.4, height=1.4, sill=0.9),
        Opening("Pencere-R2", "window", "DIS-Ust", distance=width - (a + b) / 2,
                width=2.4, height=1.4, sill=0.9),
        Opening("Pencere-R1", "window", "DIS-Ust", distance=width - a / 2,
                width=2.4, height=1.4, sill=0.9),
    ]

    rooms = [
        Room("R1", (0.0, 0.0), (a, depth)),
        Room("R2", (a, 0.0),   (b, depth)),
        Room("R3", (b, 0.0),   (width, depth)),
    ]

    return BuildingLayout(
        name="Baseline-Orta",
        storey_height=height,
        walls=walls,
        openings=openings,
        rooms=rooms,
        params={
            "width": width, "depth": depth, "height": height,
            "wall_thickness": wall_thickness, "room_count": len(rooms),
            "kind": "medium",
        },
    )
