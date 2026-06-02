"""Veri yollarının tek merkezden çözümü.

Tüm dinamik çıktılar repo kökündeki `data/` altına yazılır (bu klasör
`.gitignore` ile push dışıdır). Kod hiçbir yere sabit yol gömmez; hep buradan
okur. Notebook'lar farklı çalışma dizininden başlasa bile yol doğru bulunur.
"""
from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Repo kökünü bul: bu dosya src/ifc_gen/paths.py konumunda."""
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """Dinamik veri klasörü (push edilmez). `IFC_DATA_DIR` ile override edilebilir."""
    env = os.environ.get("IFC_DATA_DIR")
    base = Path(env).expanduser().resolve() if env else repo_root() / "data"
    return base


def _sub(name: str) -> Path:
    p = data_dir() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def baseline_ifc_dir() -> Path:
    return _sub("baseline_ifc")


def violated_ifc_dir() -> Path:
    return _sub("violated_ifc")


def violation_pool_dir() -> Path:
    return _sub("violation_pool")


def logs_dir() -> Path:
    return _sub("logs")
