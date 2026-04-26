"""
Serum 2 Preset Expert agent.

Takes a synthesis recipe (from the Sound Design Expert) and iteratively
builds a .SerumPreset file by calling preset tool functions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anthropic

from centrifuge._paths import DEFAULT_BASE_PRESET_RELATIVE, factory_preset
from centrifuge.codec import unpack
from centrifuge.preset import FX_TYPES, FILTER_TYPES, PresetBuilder

# ---------------------------------------------------------------------------
# Tool implementations (called by the agent)
# ---------------------------------------------------------------------------

_active_builders: dict[str, PresetBuilder] = {}


def _preset_init(output_path: str, base_preset_path: str | None = None) -> dict:
    """Create a new preset builder, optionally based on a factory preset."""
    base = (
        Path(base_preset_path) if base_preset_path
        else factory_preset(*DEFAULT_BASE_PRESET_RELATIVE)
    )
    if not base.exists():
        return {"error": f"Base preset not found: {base}"}
    try:
        builder = PresetBuilder.from_path(base)
        _active_builders[output_path] = builder
        return {"ok": True, "output_path": output_path, "base": str(base)}
    except Exception as e:
        return {"error": str(e)}


def _preset_get(output_path: str, component: str, key: str | None = None) -> dict:
    """Get a component or param value from the in-progress preset."""
    builder = _active_builders.get(output_path)
    if builder is None:
        return {"error": f"Preset not initialised: {output_path}. Call preset_init first."}
    comp = builder.get_component(component)
    if comp is None:
        return {"error": f"Component '{component}' not found"}
    if key is None:
        return {component: comp}
    pp = comp.get("plainParams", {}) if isinstance(comp, dict) else {}
    if isinstance(pp, dict) and key in pp:
        return {"component": component, "key": key, "value": pp[key]}
    return {"error": f"Key '{key}' not found in {component}.plainParams"}


def _preset_set(output_path: str, changes: dict[str, dict[str, Any]]) -> dict:
    """
    Apply a batch of param changes.

    changes: {"Oscillator0": {"kParamVolume": 0.8}, "Env0": {"kParamAttack": 0.1}}
    """
    builder = _active_builders.get(output_path)
    if builder is None:
        return {"error": f"Preset not initialised: {output_path}. Call preset_init first."}
    try:
        for component, params in changes.items():
            builder.set_component(component, params)
        return {"ok": True, "applied": list(changes.keys())}
    except Exception as e:
        return {"error": str(e)}


def _preset_set_wt(output_path: str, slot: int, wavetable: str | None = None, **params) -> dict:
    """Set WTOsc params for an oscillator slot."""
    builder = _active_builders.get(output_path)
    if builder is None:
        return {"error": f"Preset not initialised: {output_path}"}
    try:
        builder.set_wavetable_osc(slot, wavetable, **params)
        return {"ok": True, "slot": slot, "wavetable": wavetable, "params": params}
    except Exception as e:
        return {"error": str(e)}


def _preset_add_fx(output_path: str, rack: int, fx_class: str, **params) -> dict:
    """Add an effect to an FX rack."""
    builder = _active_builders.get(output_path)
    if builder is None:
        return {"error": f"Preset not initialised: {output_path}"}
    try:
        builder.add_fx(rack, fx_class, **params)
        return {"ok": True, "rack": rack, "fx_class": fx_class, "params": params}
    except Exception as e:
        return {"error": str(e)}


def _preset_show(output_path: str, section: str | None = None) -> dict:
    """Show the current state of the preset (optionally filtered)."""
    builder = _active_builders.get(output_path)
    if builder is None:
        return {"error": f"Preset not initialised: {output_path}"}

    _SECTIONS = {
        "osc": ["Oscillator", "WTOsc", "GranularOsc", "NoiseOsc", "SubOsc"],
        "env": ["Env"],
        "lfo": ["LFO"],
        "filter": ["VoiceFilter", "Filter"],
        "fx": ["FXRack"],
        "mod": ["ModSlot"],
        "macro": ["Macro"],
        "global": ["Global"],
    }
    data = builder.all_params()
    if section and section in _SECTIONS:
        prefixes = _SECTIONS[section]
        data = {k: v for k, v in data.items() if any(k.startswith(p) for p in prefixes)}
    return data


def _preset_save(output_path: str, name: str | None = None, author: str = "centrifuge", description: str = "", tags: list | None = None) -> dict:
    """Finalise and write the preset file."""
    builder = _active_builders.get(output_path)
    if builder is None:
        return {"error": f"Preset not initialised: {output_path}"}
    try:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        builder.save(p, name=name or p.stem, author=author, description=description, tags=tags or [])
        del _active_builders[output_path]
        return {"ok": True, "path": output_path}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Tool schemas for the Claude API
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "preset_init",
        "description": "Initialise a new preset builder, optionally loading a factory preset as the base. Must be called before any other preset tool.",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_path": {"type": "string", "description": "File path for the output .SerumPreset"},
                "base_preset_path": {"type": "string", "description": "Optional path to a factory preset to use as the base. If omitted, uses a neutral analog preset."},
            },
            "required": ["output_path"],
        },
    },
    {
        "name": "preset_set",
        "description": (
            "Apply a batch of parameter changes to the preset. "
            "The changes object maps component names to param dicts. "
            "Component names: Oscillator0-4, WTOsc0-2 (inside Oscillator), "
            "Env0-3 (0=Amp, 1=Filter, 2-3=Aux), LFO0-9, VoiceFilter0-1, "
            "FXRack0-2, Macro0-7, ModSlot0-63, Global0. "
            "Special: for WTOsc params, use set_wavetable_osc instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "output_path": {"type": "string"},
                "changes": {
                    "type": "object",
                    "description": "Map of component name → {kParam* → value}",
                    "additionalProperties": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                },
            },
            "required": ["output_path", "changes"],
        },
    },
    {
        "name": "preset_set_wt",
        "description": (
            "Set wavetable oscillator params for Oscillator slot 0/1/2. "
            "Use this to set the wavetable file, table position, warp mode, etc. "
            "Common wavetables: 'S2 Tables/Default Shapes.wav', 'S2 Tables/Analog.wav', "
            "'S2 Tables/Digital.wav', 'S2 Tables/FM.wav', 'S2 Tables/Noise.wav', "
            "'S2 Tables/Spectral.wav', 'S2 Tables/Voice.wav'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "output_path": {"type": "string"},
                "slot": {"type": "integer", "enum": [0, 1, 2]},
                "wavetable": {"type": "string", "description": "Relative path to wavetable .wav file (optional)"},
                "kParamTablePos": {"type": "number", "description": "Wavetable position 0-2048"},
                "kParamWarpMenu": {"type": "string", "description": "Warp mode string, e.g. 'kPD_FILT1'"},
                "kParamWarp": {"type": "number"},
                "kParamWarp2": {"type": "number"},
                "kParamRandomPhase": {"type": "number"},
            },
            "required": ["output_path", "slot"],
        },
    },
    {
        "name": "preset_add_fx",
        "description": (
            "Append an effect to FXRack0/1/2. "
            "fx_class must be one of: FXDistortion, FXFlanger, FXPhaser, FXChorus, "
            "FXDelay, FXComp, FXReverb, FXEQ, FXFilter, FXHyperD, FXBode, FXConv, FXUtils. "
            "Set kParamWet (0-1) to control mix. "
            "FXReverb: kParamWet, kParamSize (0-1), kParamPreDelay, kParamWidth. "
            "FXChorus: kParamWet, kParamRate, kParamDepth, kParamDelay. "
            "FXDelay: kParamWet, kParamTimeL, kParamTimeR, kParamFeedback, kParamBeatSync. "
            "FXDistortion: kParamWet, kParamDrive (0-100), kParamMode (e.g. 'kSoftClip'). "
            "FXHyperD: kParamWet, kParamDetune, kParamUnison (int), kParamDimEWet, kParamDimESize."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "output_path": {"type": "string"},
                "rack": {"type": "integer", "enum": [0, 1, 2], "description": "FX rack 0/1/2"},
                "fx_class": {"type": "string"},
                "kParamWet": {"type": "number"},
                "kParamSize": {"type": "number"},
                "kParamDrive": {"type": "number"},
                "kParamRate": {"type": "number"},
                "kParamDepth": {"type": "number"},
                "kParamFeedback": {"type": "number"},
                "kParamTimeL": {"type": "number"},
                "kParamTimeR": {"type": "number"},
                "kParamPreDelay": {"type": "number"},
                "kParamWidth": {"type": "number"},
                "kParamMode": {"type": "string"},
                "kParamDetune": {"type": "number"},
                "kParamUnison": {"type": "integer"},
                "kParamDimEWet": {"type": "number"},
                "kParamDimESize": {"type": "number"},
            },
            "required": ["output_path", "rack", "fx_class"],
        },
    },
    {
        "name": "preset_show",
        "description": "Show the current state of the in-progress preset to verify your work.",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_path": {"type": "string"},
                "section": {
                    "type": "string",
                    "enum": ["osc", "env", "lfo", "filter", "fx", "mod", "macro", "global"],
                    "description": "Optional section to show (omit for all)",
                },
            },
            "required": ["output_path"],
        },
    },
    {
        "name": "preset_save",
        "description": "Finalise and write the preset file. Call this last.",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_path": {"type": "string"},
                "name": {"type": "string", "description": "Preset display name"},
                "author": {"type": "string"},
                "description": {"type": "string"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags like ['Pad', 'Poly', 'Wavetable']",
                },
            },
            "required": ["output_path"],
        },
    },
]

_TOOL_DISPATCH = {
    "preset_init": lambda args: _preset_init(**args),
    "preset_set": lambda args: _preset_set(args["output_path"], args["changes"]),
    "preset_set_wt": lambda args: _preset_set_wt(
        args["output_path"], args["slot"],
        wavetable=args.get("wavetable"),
        **{k: v for k, v in args.items() if k not in ("output_path", "slot", "wavetable")},
    ),
    "preset_add_fx": lambda args: _preset_add_fx(
        args["output_path"], args["rack"], args["fx_class"],
        **{k: v for k, v in args.items() if k not in ("output_path", "rack", "fx_class")},
    ),
    "preset_show": lambda args: _preset_show(args["output_path"], args.get("section")),
    "preset_save": lambda args: _preset_save(
        args["output_path"],
        name=args.get("name"),
        author=args.get("author", "centrifuge"),
        description=args.get("description", ""),
        tags=args.get("tags"),
    ),
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a Serum 2 Preset Expert — a master of Xfer Records' Serum 2 synthesizer.

Your job: given a synthesis recipe (JSON describing how a sound should be constructed),
use the provided tools to build a valid .SerumPreset file that implements it.

## Serum 2 Architecture

**Oscillators** (Oscillator0=A, Oscillator1=B, Oscillator2=C, Oscillator3=Noise, Oscillator4=Sub)
- Top-level (Oscillator0.plainParams): kParamVolume (0-1), kParamPan (-1 to 1), kParamOctave (-4 to 4),
  kParamFine (-100 to 100 cents), kParamUnison (1-16), kParamDetune (0-1), kParamDetuneWid (0-1),
  kParamUnisonStereo (0-1), kParamEnable (0/1), kParamCoarsePit, kParamType
- WTOsc sub-object (use preset_set_wt): kParamTablePos (0-2048), kParamWarpMenu, kParamWarp/Warp2

**Envelopes** (Env0=Amp, Env1=Filter, Env2-3=Auxiliary)
- kParamAttack (seconds), kParamHold (seconds), kParamDecay (seconds),
  kParamSustain (0-1), kParamRelease (seconds)
- kParamCurve1 (attack curve shape 0-100), kParamCurve2 (decay/sustain), kParamCurve3 (release)
- Typical values: Curves 50=linear, <50=convex (slow start), >50=concave (fast start)

**Filters** (VoiceFilter0=Filter A, VoiceFilter1=Filter B)
- kParamEnable (1.0), kParamType (string), kParamFreq (0-1 normalised, 0.5≈1kHz),
  kParamReso (0-100), kParamDrive (0-100), kParamVar (0-100), kParamKeyTrack (0-1)
- Common filter types: "L24" (LP 24dB), "L12" (LP 12dB), "H24" (HP 24dB),
  "LadderMg" (Moog ladder), "LadderAcid" (303-style acid), "B12" (bandpass),
  "FlangeN", "FormantONE", "FormantTWO"

**LFOs** (LFO0-9)
- kParamRate (Hz), kParamSmooth (0-1), kParamRise (seconds), kParamDelay (seconds)
- kParamMode: "Free" (free-running), "Envelope" (one-shot), "Trigger" (retrig)
- kParamBeatSync (0/1), kParamMono (0/1=same for all voices), kParamPhase (0-1)
- kParamType: omit for standard waveform LFO; "RandomSH", "Lorenz", "Rossler" for special types

**FX Racks** (FXRack0=Main, FXRack1/2=Bus)
- Use preset_add_fx to append effects. They run in order.
- kParamWet (0-1) controls wet/dry mix for all effects.

**Modulation** (ModSlot0-63)
- Modulation slots wire a source to a destination parameter.
- For modulation, use preset_set directly with the ModSlot structure.

## Workflow

1. Call preset_init to load the base preset
2. Clear or configure oscillators as needed
3. Set envelope parameters (Env0 is always the Amp envelope)
4. Configure filters if needed
5. Add LFO modulation if needed
6. Add effects (reverb, chorus, delay, etc.)
7. Call preset_show to verify key sections look correct
8. Call preset_save to write the file

## Important Notes

- All `plainParams` values are floats unless noted otherwise (filter/LFO types are strings)
- kParamFreq for filters is 0-1 normalised: ~0.15 ≈ 200Hz, ~0.35 ≈ 800Hz, ~0.5 ≈ 1kHz, ~0.7 ≈ 4kHz
- Attack/decay/release times are in seconds (e.g. 0.01 = 10ms, 0.5 = 500ms, 2.0 = 2s)
- Unison: 1 = no unison, 2-16 = stacked voices
- For a pad: slow attack (0.3-1s), long release (1-3s), some unison detune
- For a bass: fast attack (<0.01s), short decay, filter with envelope modulation
- For a lead: medium attack, bright filter, light reverb

Start by calling preset_init, then systematically build the sound layer by layer.
"""


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

async def run_serum_expert(
    recipe: dict,
    output_path: Path,
    base_factory: Path | None = None,
    model: str = "claude-opus-4-7",
    progress=None,
) -> Path:
    """
    Run the Serum 2 Expert agentic loop to produce a .SerumPreset file.

    recipe: synthesis recipe from the Sound Design Expert
    output_path: where to write the .SerumPreset
    """
    from centrifuge.progress import null_progress
    progress = progress or null_progress()

    client = anthropic.Anthropic()
    output_str = str(output_path)

    messages = [
        {
            "role": "user",
            "content": (
                f"Please create a Serum 2 preset at path: {output_str}\n\n"
                f"Base factory preset (if you want to use one): {str(base_factory) if base_factory else 'use default'}\n\n"
                f"Synthesis recipe:\n{json.dumps(recipe, indent=2)}\n\n"
                "Build the preset step by step using the available tools. "
                "After setting all parameters, call preset_show to verify, then preset_save to finalise."
            ),
        }
    ]

    tool_call_count = 0

    while True:
        progress.update(f"{tool_call_count} tool calls" if tool_call_count else "")
        response = client.messages.create(
            model=model,
            max_tokens=8192,
            system=_SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            progress.log(
                f"response: {usage.output_tokens} tokens out, stop={response.stop_reason}"
            )

        # Append assistant response
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_call_count += 1
                    progress.log(f"tool: {tool_name}({_summarise_args(tool_input)})")
                    handler = _TOOL_DISPATCH.get(tool_name)
                    if handler:
                        result = handler(tool_input)
                    else:
                        result = {"error": f"Unknown tool: {tool_name}"}
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            break  # unexpected stop reason

    # If preset was never saved (agent forgot), save it now
    if output_str in _active_builders:
        _preset_save(output_str, name=output_path.stem)

    progress.update(f"{tool_call_count} tool calls")
    return output_path


def _summarise_args(args: dict) -> str:
    """Compact one-line summary of tool args for the progress log."""
    parts = []
    for k, v in args.items():
        if k == "output_path":
            continue
        if isinstance(v, dict):
            parts.append(f"{k}={{{','.join(v.keys())}}}")
        elif isinstance(v, list):
            parts.append(f"{k}=[{len(v)}]")
        else:
            s = str(v)
            parts.append(f"{k}={s[:30]}")
    return ", ".join(parts)
