"""Local pipeline: text description → synthesis recipe → .SerumPreset."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from centrifuge.local.serum_expert import build_preset
from centrifuge.local.sound_design import generate_recipe
from centrifuge.progress import null_progress


def generate_preset_local(
    description: str,
    output_path: Path,
    base_factory: Path | None = None,
    progress: Any = None,
) -> Path:
    """Run the local algorithmic pipeline. Returns the output path on success."""
    progress = progress or null_progress()

    progress.step("Generate recipe (algorithmic)")
    recipe = generate_recipe(description)
    progress.update(f"template={recipe.get('character', '?')}")
    progress.log(f"matched tokens: {recipe.get('notes', '')}")

    progress.step("Build .SerumPreset")
    result = build_preset(recipe, output_path, base_factory)
    progress.update(f"wrote {result.name}")

    progress.done()
    return result
