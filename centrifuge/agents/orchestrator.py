"""
Top-level pipeline: text description (+ optional audio) → .SerumPreset file.

1. Sound Design Expert analyses the description and produces a synthesis recipe.
2. Serum 2 Expert takes the recipe and builds the preset using tool calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from centrifuge.agents.serum_expert import run_serum_expert
from centrifuge.agents.sound_design import run_sound_design_expert
from centrifuge.progress import null_progress


async def generate_preset(
    description: str,
    output_path: Path,
    audio_path: Path | None = None,
    base_factory: Path | None = None,
    model: str = "claude-opus-4-7",
    progress: Any = None,
) -> Path:
    """
    Generate a Serum 2 preset from a text description (and optionally an audio file).

    Returns the output_path on success.
    """
    progress = progress or null_progress()

    audio_features: dict[str, Any] | None = None
    if audio_path is not None:
        progress.step("Extract audio features (librosa)")
        from centrifuge.audio import extract_features
        audio_features = extract_features(audio_path)
        progress.update(f"{len(audio_features)} features")
        progress.log(
            f"centroid={audio_features.get('spectral_centroid_hz', '?')}Hz "
            f"attack={audio_features.get('attack_time_ms', '?')}ms "
            f"harmonicity={audio_features.get('harmonicity', '?')}"
        )

    progress.step("Sound Design Expert")
    recipe = await run_sound_design_expert(
        description=description,
        audio_features=audio_features,
        model=model,
        progress=progress,
    )

    progress.step("Serum 2 Expert")
    result = await run_serum_expert(
        recipe=recipe,
        output_path=output_path,
        base_factory=base_factory,
        model=model,
        progress=progress,
    )

    progress.done()
    return result
