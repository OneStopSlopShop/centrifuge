"""
Agent-friendly CLI for centrifuge.

All commands write JSON to stdout.  Errors write {"error": "..."} to stderr
and exit with code 1.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from centrifuge._paths import DEFAULT_BASE_PRESET_RELATIVE, factory_preset
from centrifuge.codec import pack, unpack
from centrifuge.preset import FILTER_TYPES, FX_TYPES, PresetBuilder

# Default base preset shipped with Serum 2 factory content.
# The agent / user can override this with --base, or relocate the factory
# directory entirely with the SERUM2_FACTORY_DIR env var.
_DEFAULT_BASE = factory_preset(*DEFAULT_BASE_PRESET_RELATIVE)

_SECTION_PREFIXES: dict[str, list[str]] = {
    "osc": ["Oscillator", "WTOsc", "GranularOsc", "NoiseOsc", "SubOsc", "SampleOsc", "SpectralOsc", "MultiSampleOsc"],
    "env": ["Env"],
    "lfo": ["LFO"],
    "filter": ["VoiceFilter", "Filter"],
    "fx": ["FXRack"],
    "mod": ["ModSlot"],
    "macro": ["Macro"],
    "global": ["Global"],
}


def _out(obj) -> None:
    click.echo(json.dumps(obj, indent=2, default=str))


def _err(msg: str) -> None:
    click.echo(json.dumps({"error": msg}), err=True)
    sys.exit(1)


def _load(preset: str) -> dict:
    p = Path(preset)
    if not p.exists():
        _err(f"File not found: {preset}")
    try:
        return unpack(p)
    except Exception as e:
        _err(f"Failed to read preset: {e}")


@click.group()
def cli():
    """Centrifuge — AI-driven Serum 2 preset generator."""


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("output")
@click.option("--base", default=None, help="Factory preset to base on (default: Analog Classics 1)")
@click.option("--name", default=None, help="Preset name")
@click.option("--author", default="centrifuge", help="Preset author")
def init(output: str, base: str | None, name: str | None, author: str) -> None:
    """Create a new preset (optionally based on a factory preset)."""
    base_path = Path(base) if base else _DEFAULT_BASE
    if not base_path.exists():
        _err(f"Base preset not found: {base_path}")
    try:
        builder = PresetBuilder.from_path(base_path)
        preset_name = name or Path(output).stem
        builder.save(Path(output), name=preset_name, author=author)
        _out({"ok": True, "path": output, "name": preset_name, "base": str(base_path)})
    except Exception as e:
        _err(str(e))


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("preset")
@click.option("--section", default=None,
              type=click.Choice(list(_SECTION_PREFIXES.keys())),
              help="Return only a section of the preset")
@click.option("--meta", is_flag=True, help="Show metadata only")
def show(preset: str, section: str | None, meta: bool) -> None:
    """Dump a preset as JSON (optionally filtered to a section)."""
    data = _load(preset)
    if meta:
        _out(data["metadata"])
        return
    if section:
        prefixes = _SECTION_PREFIXES[section]
        filtered = {k: v for k, v in data["data"].items()
                    if any(k.startswith(p) for p in prefixes)}
        _out(filtered)
    else:
        _out(data)


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("preset")
@click.argument("component")
@click.argument("key", required=False)
def get(preset: str, component: str, key: str | None) -> None:
    """Get a component or a single param from a preset."""
    data = _load(preset)
    comp = data["data"].get(component)
    if comp is None:
        _err(f"Component '{component}' not found in preset")
    if key is None:
        _out({component: comp})
        return
    pp = comp.get("plainParams", {}) if isinstance(comp, dict) else {}
    if isinstance(pp, dict) and key in pp:
        _out({"component": component, "key": key, "value": pp[key]})
    else:
        _err(f"Key '{key}' not found in {component}.plainParams")


# ---------------------------------------------------------------------------
# set
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("preset")
@click.argument("component")
@click.argument("key")
@click.argument("value")
def set(preset: str, component: str, key: str, value: str) -> None:
    """Set a single param on a component and save the preset in-place."""
    data = _load(preset)
    builder = PresetBuilder(data)

    # Try to parse the value as a number; keep as string if that fails
    parsed: str | float
    try:
        parsed = float(value)
        if parsed == int(parsed):
            parsed = int(parsed)
    except ValueError:
        parsed = value

    builder.set_component(component, {key: parsed})
    builder.save(Path(preset))
    _out({"ok": True, "component": component, "key": key, "value": parsed})


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("preset")
@click.argument("changes_json")
def apply(preset: str, changes_json: str) -> None:
    """
    Apply a batch of changes from a JSON string or file path.

    CHANGES_JSON format:
      {"Oscillator0": {"kParamVolume": 0.8}, "Env0": {"kParamAttack": 0.1}}
    """
    # Accept either a JSON string or a file path
    if Path(changes_json).exists():
        try:
            changes = json.loads(Path(changes_json).read_text())
        except Exception as e:
            _err(f"Failed to parse changes file: {e}")
    else:
        try:
            changes = json.loads(changes_json)
        except json.JSONDecodeError as e:
            _err(f"Invalid JSON: {e}")

    if not isinstance(changes, dict):
        _err("Changes must be a JSON object mapping component → params")

    data = _load(preset)
    builder = PresetBuilder(data)
    for comp, params in changes.items():
        if not isinstance(params, dict):
            _err(f"Params for '{comp}' must be an object")
        builder.set_component(comp, params)

    builder.save(Path(preset))
    _out({"ok": True, "applied": list(changes.keys())})


# ---------------------------------------------------------------------------
# list-params
# ---------------------------------------------------------------------------

@cli.command("list-params")
@click.option("--component", default=None, help="Filter to a specific component type")
def list_params(component: str | None) -> None:
    """List known component types, their param keys, and FX/filter types."""
    schema = {
        "oscillator_params": [
            "kParamVolume", "kParamPan", "kParamOctave", "kParamFine",
            "kParamUnison", "kParamDetune", "kParamDetuneWid", "kParamUnisonStereo",
            "kParamUnisonRange", "kParamUnisonStack", "kParamEnable",
            "kParamCoarsePit", "kParamType", "kParamPitch", "kParamPitchMode",
        ],
        "wtosc_params": [
            "kParamTablePos", "kParamWarpMenu", "kParamWarp", "kParamWarp2",
            "kParamRandomPhase", "kParamInitialPhase", "kParamPhaseMemory",
        ],
        "envelope_params": [
            "kParamAttack", "kParamHold", "kParamDecay", "kParamSustain",
            "kParamRelease", "kParamCurve1", "kParamCurve2", "kParamCurve3",
            "kParamStart",
        ],
        "lfo_params": [
            "kParamRate", "kParamSmooth", "kParamRise", "kParamDelay",
            "kParamBeatSync", "kParamMode", "kParamType", "kParamMono",
            "kParamPhase", "kParamAnchored", "kParamDirection",
        ],
        "filter_params": [
            "kParamEnable", "kParamFreq", "kParamReso", "kParamDrive",
            "kParamVar", "kParamKeyTrack", "kParamStereo", "kParamWet",
            "kParamLevelOut", "kParamPad",
        ],
        "filter_types": FILTER_TYPES,
        "fx_classes": {v: k for k, v in FX_TYPES.items()},
        "fx_reverb_params": [
            "kParamWet", "kParamSize", "kParamPreDelay", "kParamFeedback",
            "kParamFreq", "kParamFreqB", "kParamWidth", "kParamMode",
        ],
        "fx_distortion_params": [
            "kParamWet", "kParamDrive", "kParamMode", "kParamFreq",
            "kParamBW", "kParamPrePost", "kParamLevelOut",
        ],
        "fx_chorus_params": [
            "kParamWet", "kParamRate", "kParamDepth", "kParamDelay",
            "kParamDelay2", "kParamFeedback",
        ],
        "fx_delay_params": [
            "kParamWet", "kParamTimeL", "kParamTimeR", "kParamFeedback",
            "kParamBeatSync", "kParamMode", "kParamBW",
        ],
        "fx_compressor_params": [
            "kParamWet", "kParamThresh", "kParamRatio", "kParamAttack",
            "kParamRelease", "kParamMakeup", "kParamMultiband",
        ],
        "fx_hyperD_params": [
            "kParamWet", "kParamDetune", "kParamUnison", "kParamRate",
            "kParamDimEWet", "kParamDimESize",
        ],
        "global_params": [
            "kParamMasterVolume", "kParamPolyCount", "kParamMonoToggle",
            "kParamPortamentoTime", "kParamPortaAlways", "kParamTranspose",
            "kParamOversampling", "kParamBendRangeUp", "kParamBendRangeDn",
            "kParamSwing", "kParamModWheel",
        ],
    }
    if component:
        key = f"{component}_params"
        if key in schema:
            _out({key: schema[key]})
        else:
            _err(f"Unknown component type '{component}'")
    else:
        _out(schema)


# ---------------------------------------------------------------------------
# generate (wired in orchestrator.py)
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("description")
@click.option("--audio", default=None, help="Path to WAV/audio file for sound matching")
@click.option("--output", required=True, help="Output .SerumPreset path")
@click.option("--base", default=None, help="Base factory preset path")
@click.option("--model", default="claude-opus-4-7", help="Claude model to use")
@click.option("--local", is_flag=True, help="Use local algorithmic mode (no cloud API)")
@click.option("--local-models", is_flag=True,
              help="Phase 2: enable optional HF models in --local mode (not yet implemented)")
@click.option("--noapi", is_flag=True,
              help="Use Claude Code (subprocess) instead of the Anthropic API. "
                   "No API key needed; requires the `claude` CLI on PATH.")
@click.option("--noapi-timeout", default=600, type=int,
              help="Timeout (seconds) for the Claude Code subprocess in --noapi mode")
@click.option("--noapi-max-turns", default=None, type=int,
              help="Cap on Claude Code conversation turns in --noapi mode "
                   "(default: 8). A well-behaved run finishes in 3–5 turns; "
                   "raise this if you hit the cap with a complex description.")
@click.option("-v", "--verbose", is_flag=True,
              help="Show details from each step (agent responses, tool calls)")
@click.option("-q", "--quiet", is_flag=True,
              help="Suppress all progress output (only the final JSON result)")
def generate(description: str, audio: str | None, output: str, base: str | None, model: str,
             local: bool, local_models: bool, noapi: bool, noapi_timeout: int,
             noapi_max_turns: int | None, verbose: bool, quiet: bool) -> None:
    """Generate a Serum 2 preset from a text description (and optionally an audio file)."""
    if local and noapi:
        _err("--local and --noapi are mutually exclusive. Pick one.")
    if verbose and quiet:
        _err("-v and -q are mutually exclusive.")

    base_path = Path(base) if base else None

    from centrifuge.progress import progress_reporter

    # ------------------------------------------------------------------
    # --local: pure algorithmic, no LLM
    # ------------------------------------------------------------------
    if local:
        if local_models:
            _err("--local-models is Phase 2 and not yet implemented. "
                 "Drop --local-models to use the pure algorithmic local mode.")
        if audio:
            _err("--audio in --local mode requires --local-models (Phase 2). "
                 "Drop --audio or use the cloud mode (without --local).")

        from centrifuge.local.orchestrator import generate_preset_local
        try:
            with progress_reporter(enabled=not quiet, verbose=verbose, total_steps=2) as prog:
                result = generate_preset_local(
                    description=description,
                    output_path=Path(output),
                    base_factory=base_path,
                    progress=prog,
                )
            _out({"ok": True, "path": str(result), "mode": "local"})
        except Exception as e:
            _err(str(e))
        return

    # ------------------------------------------------------------------
    # --noapi: drive Claude Code as a subprocess (no API key required)
    # ------------------------------------------------------------------
    if noapi:
        from centrifuge.agents.noapi import DEFAULT_MAX_TURNS, generate_preset_noapi
        audio_path = Path(audio) if audio else None
        total = 2 if audio_path else 1
        try:
            with progress_reporter(enabled=not quiet, verbose=verbose, total_steps=total) as prog:
                result = generate_preset_noapi(
                    description=description,
                    output_path=Path(output),
                    audio_path=audio_path,
                    base_factory=base_path,
                    max_turns=noapi_max_turns if noapi_max_turns is not None else DEFAULT_MAX_TURNS,
                    timeout_s=noapi_timeout,
                    progress=prog,
                )
            _out({"ok": True, "path": str(result), "mode": "noapi"})
        except Exception as e:
            _err(str(e))
        return

    # ------------------------------------------------------------------
    # default: cloud path (Anthropic API)
    # ------------------------------------------------------------------
    import asyncio
    from centrifuge.agents.orchestrator import generate_preset

    audio_path = Path(audio) if audio else None
    total = 3 if audio_path else 2
    try:
        with progress_reporter(enabled=not quiet, verbose=verbose, total_steps=total) as prog:
            result = asyncio.run(
                generate_preset(
                    description=description,
                    audio_path=audio_path,
                    output_path=Path(output),
                    base_factory=base_path,
                    model=model,
                    progress=prog,
                )
            )
        _out({"ok": True, "path": str(result), "mode": "cloud"})
    except Exception as e:
        _err(str(e))
