"""
Sound Design Expert agent.

Translates a text description (and optionally audio features) into a structured
synthesis recipe that the Serum 2 Expert can execute.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic

# ---------------------------------------------------------------------------
# Tool: submit_recipe
# ---------------------------------------------------------------------------

_RECIPE_TOOL = {
    "name": "submit_recipe",
    "description": (
        "Submit the finalised synthesis recipe. "
        "Call this exactly once when you are confident in the recipe."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "synthesis_approach": {
                "type": "string",
                "enum": ["subtractive", "fm", "wavetable", "granular", "additive", "spectral", "multisample", "hybrid"],
                "description": "Primary synthesis method",
            },
            "character": {
                "type": "string",
                "description": "Brief tonal character description (e.g. 'warm, slightly detuned, slow attack')",
            },
            "oscillators": {
                "type": "array",
                "description": "Oscillator configurations for slots 0-2 (A, B, C)",
                "items": {
                    "type": "object",
                    "properties": {
                        "slot": {"type": "integer", "enum": [0, 1, 2]},
                        "enabled": {"type": "boolean"},
                        "volume": {"type": "number", "description": "0-1"},
                        "pan": {"type": "number", "description": "-1 to 1"},
                        "octave": {"type": "integer", "description": "-4 to 4"},
                        "semi": {"type": "number", "description": "coarse pitch semitones"},
                        "fine": {"type": "number", "description": "-100 to 100 cents"},
                        "unison": {"type": "integer", "description": "1-16 voices"},
                        "detune": {"type": "number", "description": "0-1 unison detune spread"},
                        "stereo_spread": {"type": "number", "description": "0-1 stereo width"},
                        "wavetable": {"type": "string", "description": "relative wavetable path, e.g. 'S2 Tables/Default Shapes.wav'"},
                        "wavetable_pos": {"type": "number", "description": "wavetable position 0-2048"},
                        "warp_mode": {"type": "string", "description": "e.g. 'kPD_FILT1' for wavetable warp"},
                    },
                    "required": ["slot"],
                },
            },
            "noise": {
                "type": "object",
                "description": "Oscillator3 (Noise) config",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "volume": {"type": "number"},
                    "color": {"type": "number", "description": "noise colour tilt"},
                },
            },
            "sub": {
                "type": "object",
                "description": "Oscillator4 (Sub oscillator) config",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "volume": {"type": "number"},
                    "octave": {"type": "integer"},
                },
            },
            "filter_a": {
                "type": "object",
                "description": "VoiceFilter0 configuration",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "type": {"type": "string", "description": "Serum 2 filter type string, e.g. 'L24', 'LadderMg', 'LadderAcid', 'FormantONE'"},
                    "cutoff_normalized": {"type": "number", "description": "0-1, where 0.5 ≈ 1kHz"},
                    "resonance": {"type": "number", "description": "0-100"},
                    "drive": {"type": "number", "description": "0-100"},
                    "key_track": {"type": "number", "description": "0-1"},
                },
            },
            "amp_envelope": {
                "type": "object",
                "description": "Env0 — amplitude envelope",
                "properties": {
                    "attack_s": {"type": "number", "description": "Attack time in seconds"},
                    "hold_s": {"type": "number"},
                    "decay_s": {"type": "number"},
                    "sustain": {"type": "number", "description": "0-1"},
                    "release_s": {"type": "number"},
                    "attack_curve": {"type": "number", "description": "0-100, 50=linear"},
                },
            },
            "filter_envelope": {
                "type": "object",
                "description": "Env1 — filter envelope (useful for filter sweeps)",
                "properties": {
                    "attack_s": {"type": "number"},
                    "decay_s": {"type": "number"},
                    "sustain": {"type": "number"},
                    "release_s": {"type": "number"},
                    "depth": {"type": "number", "description": "Modulation amount -100 to 100 (applied via ModSlot)"},
                },
            },
            "lfos": {
                "type": "array",
                "description": "LFO configurations",
                "items": {
                    "type": "object",
                    "properties": {
                        "slot": {"type": "integer", "description": "0-9"},
                        "rate_hz": {"type": "number"},
                        "mode": {"type": "string", "enum": ["Free", "Envelope", "Trigger"]},
                        "beat_sync": {"type": "boolean"},
                        "smooth": {"type": "number", "description": "0-1"},
                        "destination": {"type": "string", "description": "What this LFO modulates, e.g. 'filter cutoff'"},
                    },
                },
            },
            "effects": {
                "type": "object",
                "description": "Effects to add to FXRack0",
                "properties": {
                    "reverb": {
                        "type": "object",
                        "properties": {
                            "wet": {"type": "number", "description": "0-1"},
                            "size": {"type": "number", "description": "0-1"},
                            "predelay": {"type": "number"},
                            "width": {"type": "number"},
                        },
                    },
                    "chorus": {
                        "type": "object",
                        "properties": {
                            "wet": {"type": "number"},
                            "rate": {"type": "number"},
                            "depth": {"type": "number"},
                            "delay": {"type": "number"},
                        },
                    },
                    "delay": {
                        "type": "object",
                        "properties": {
                            "wet": {"type": "number"},
                            "time_l": {"type": "number"},
                            "time_r": {"type": "number"},
                            "feedback": {"type": "number"},
                            "beat_sync": {"type": "boolean"},
                        },
                    },
                    "distortion": {
                        "type": "object",
                        "properties": {
                            "wet": {"type": "number"},
                            "drive": {"type": "number"},
                            "mode": {"type": "string"},
                        },
                    },
                    "hyper": {
                        "type": "object",
                        "description": "HyperD — unison fattening effect",
                        "properties": {
                            "wet": {"type": "number"},
                            "detune": {"type": "number"},
                            "unison": {"type": "integer"},
                        },
                    },
                },
            },
            "notes": {
                "type": "string",
                "description": "Brief explanation of the sound design choices",
            },
        },
        "required": ["synthesis_approach", "character", "oscillators", "amp_envelope"],
    },
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a Sound Design Expert with deep knowledge of synthesis, acoustics, and music production.

Your task: analyse the given sound description (and optionally audio features) and produce a detailed
synthesis recipe that tells a Serum 2 synthesizer exactly how to recreate the sound.

## Serum 2 capabilities you should know:

**Oscillators:**
- 3 main wavetable oscillators (A/B/C), 1 noise oscillator, 1 sub oscillator
- Wavetables: "S2 Tables/Default Shapes.wav" (sine→saw→square), "S2 Tables/Analog.wav",
  "S2 Tables/Digital.wav", "S2 Tables/FM.wav", "S2 Tables/Voice.wav", "S2 Tables/Spectral.wav"
- Unison: 1-16 voices with detune spread

**Filters:**
- Common types: "L24" (LP 4-pole), "L12" (LP 2-pole), "H24" (HP 4-pole),
  "LadderMg" (Moog-style warmth), "LadderAcid" (TB-303 acid resonance),
  "B12" (bandpass), "FormantONE"/"FormantTWO" (vowel formants)

**Envelopes:**
- Env0 = Amp (controls volume shape)
- Env1 = Filter (usually for filter cutoff sweeps)
- Times in seconds: fast attack = 0.001-0.01, slow attack = 0.3-2.0

**Effects:**
- Reverb: adds space (wet 0.1-0.4 for subtle)
- Chorus: subtle detuning/movement
- HyperD: extreme fattening with many unison voices
- Delay: echo effect

## How to reason about sounds:

1. **Pads**: slow attack (0.3-1s), long release (1-3s), unison on oscillators,
   LP filter with gentle sweep, reverb + chorus
2. **Basses**: fast attack (<0.01s), short decay, low octave, LP filter with
   filter envelope for punch (Acid/Ladder filter for 303 style)
3. **Leads**: medium attack, bright cutoff, some drive/distortion, light reverb
4. **Plucks**: very fast attack, short decay, moderate sustain, pluck-like filter envelope
5. **Arps**: short notes, often sawtooth oscillators, with pattern/rhythm
6. **Drums**: very fast attack, very short decay, percussive envelope

When given audio features:
- High spectral centroid (>3kHz) → bright sound, high filter cutoff or no filter
- Low spectral centroid (<1kHz) → dark/warm, LP filter with low cutoff
- High harmonicity → tonal, use pitched oscillators
- Low harmonicity / is_percussive → noise-heavy, use noise oscillator
- Fast attack (<20ms) → punchy, fast amp envelope
- Slow attack (>100ms) → pad-like, slow amp envelope
- High ZCR → noisy/harsh, consider distortion or noise oscillator

Provide a complete and specific recipe. Be precise with numbers.
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

async def run_sound_design_expert(
    description: str,
    audio_features: dict[str, Any] | None = None,
    model: str = "claude-opus-4-7",
    progress: Any = None,
) -> dict:
    """
    Run the Sound Design Expert to produce a synthesis recipe.

    Returns the recipe dict, or raises on failure.
    """
    from centrifuge.progress import null_progress
    progress = progress or null_progress()

    client = anthropic.Anthropic()

    content_parts = [f"Sound description: {description}"]
    if audio_features:
        content_parts.append(
            f"\nAudio features:\n{json.dumps(audio_features, indent=2)}"
        )
    content_parts.append(
        "\nPlease analyse this sound and call submit_recipe with a detailed synthesis recipe."
    )

    messages = [{"role": "user", "content": "\n".join(content_parts)}]

    while True:
        progress.update()
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            tools=[_RECIPE_TOOL],
            messages=messages,
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            progress.update(f"in={usage.input_tokens} out={usage.output_tokens}")
            progress.log(
                f"response: {usage.output_tokens} tokens out, stop={response.stop_reason}"
            )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "tool_use":
            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_recipe":
                    progress.log(
                        f"recipe: approach={block.input.get('synthesis_approach')} "
                        f"oscs={len(block.input.get('oscillators', []))} "
                        f"lfos={len(block.input.get('lfos', []))} "
                        f"effects={list(block.input.get('effects', {}).keys())}"
                    )
                    return block.input  # the recipe dict

            # Tool use but no submit_recipe — add dummy result and continue
            tool_results = [
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "ok",
                }
                for block in response.content
                if hasattr(block, "id")
            ]
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            raise ValueError("Sound Design Expert did not call submit_recipe")
        else:
            raise ValueError(f"Unexpected stop reason: {response.stop_reason}")
