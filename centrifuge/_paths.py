"""
Resolve the Serum 2 factory preset directory.

Override the location with the ``SERUM2_FACTORY_DIR`` environment variable.
Otherwise we assume the default install layout under the user's Documents
folder, which matches Xfer's installer on Windows and macOS.
"""

from __future__ import annotations

import os
from pathlib import Path


def factory_dir() -> Path:
    env = os.environ.get("SERUM2_FACTORY_DIR")
    if env:
        return Path(env)
    return Path.home() / "Documents" / "Xfer" / "Serum 2 Presets" / "Presets" / "Factory"


def factory_preset(*relative: str) -> Path:
    return factory_dir().joinpath(*relative)


DEFAULT_BASE_PRESET_RELATIVE: tuple[str, ...] = (
    "Bass", "Retro Analog", "BA - Analog Classics 1.SerumPreset",
)
