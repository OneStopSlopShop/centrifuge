"""
Local Serum 2 Expert — deterministic recipe → .SerumPreset translator.

Pure function. Walks each section of the recipe once and calls the
matching PresetBuilder method. No iteration, no LLM.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from centrifuge._paths import DEFAULT_BASE_PRESET_RELATIVE, factory_preset
from centrifuge.preset import PresetBuilder

DEFAULT_BASE_FACTORY = factory_preset(*DEFAULT_BASE_PRESET_RELATIVE)


# ---------------------------------------------------------------------------
# Section appliers
# ---------------------------------------------------------------------------

def _apply_oscillators(builder: PresetBuilder, oscillators: list[dict]) -> None:
    for osc in oscillators:
        slot = osc.get("slot")
        if slot is None or slot not in (0, 1, 2):
            continue

        # Top-level oscillator params
        top_params: dict[str, Any] = {}
        if "volume" in osc:
            top_params["kParamVolume"] = float(osc["volume"])
        if "pan" in osc:
            top_params["kParamPan"] = float(osc["pan"])
        if "octave" in osc:
            top_params["kParamOctave"] = float(osc["octave"])
        if "fine" in osc:
            top_params["kParamFine"] = float(osc["fine"])
        if "semi" in osc:
            top_params["kParamCoarsePit"] = float(osc["semi"])
        if "unison" in osc:
            top_params["kParamUnison"] = float(osc["unison"])
        if "detune" in osc:
            top_params["kParamDetune"] = float(osc["detune"])
        if "stereo_spread" in osc:
            top_params["kParamUnisonStereo"] = float(osc["stereo_spread"])
        if "enabled" in osc:
            top_params["kParamEnable"] = 1.0 if osc["enabled"] else 0.0
        if top_params:
            builder.set_oscillator(slot, **top_params)

        # Wavetable sub-osc params
        wt_kwargs: dict[str, Any] = {}
        if "wavetable_pos" in osc:
            wt_kwargs["kParamTablePos"] = float(osc["wavetable_pos"])
        if "warp_mode" in osc:
            wt_kwargs["kParamWarpMenu"] = osc["warp_mode"]
        wavetable = osc.get("wavetable")
        if wavetable or wt_kwargs:
            builder.set_wavetable_osc(slot, wavetable=wavetable, **wt_kwargs)


def _apply_noise(builder: PresetBuilder, noise: dict | None) -> None:
    if not noise:
        return
    params: dict[str, Any] = {}
    if "volume" in noise:
        params["kParamVolume"] = float(noise["volume"])
    if "enabled" in noise:
        params["kParamEnable"] = 1.0 if noise["enabled"] else 0.0
    if params:
        builder.set_component("Oscillator3", params)


def _apply_sub(builder: PresetBuilder, sub: dict | None) -> None:
    if not sub:
        return
    params: dict[str, Any] = {}
    if "volume" in sub:
        params["kParamVolume"] = float(sub["volume"])
    if "octave" in sub:
        params["kParamOctave"] = float(sub["octave"])
    if "enabled" in sub:
        params["kParamEnable"] = 1.0 if sub["enabled"] else 0.0
    if params:
        builder.set_component("Oscillator4", params)


def _apply_filter(builder: PresetBuilder, slot: int, flt: dict | None) -> None:
    if not flt or flt.get("enabled") is False:
        return
    params: dict[str, Any] = {}
    if "cutoff_normalized" in flt:
        params["kParamFreq"] = max(0.0, min(1.0, float(flt["cutoff_normalized"])))
    if "resonance" in flt:
        params["kParamReso"] = max(0.0, min(100.0, float(flt["resonance"])))
    if "drive" in flt:
        params["kParamDrive"] = max(0.0, min(100.0, float(flt["drive"])))
    if "key_track" in flt:
        params["kParamKeyTrack"] = float(flt["key_track"])
    builder.set_filter(slot, filter_type=flt.get("type"), **params)


def _apply_envelope(builder: PresetBuilder, slot: int, env: dict | None) -> None:
    if not env:
        return
    params: dict[str, Any] = {}
    if "attack_s" in env:
        params["kParamAttack"] = float(env["attack_s"])
    if "hold_s" in env:
        params["kParamHold"] = float(env["hold_s"])
    if "decay_s" in env:
        params["kParamDecay"] = float(env["decay_s"])
    if "sustain" in env:
        params["kParamSustain"] = float(env["sustain"])
    if "release_s" in env:
        params["kParamRelease"] = float(env["release_s"])
    if "attack_curve" in env:
        params["kParamCurve1"] = max(0.0, min(100.0, float(env["attack_curve"])))
    if params:
        builder.set_envelope(slot, **params)


def _apply_lfos(builder: PresetBuilder, lfos: list[dict]) -> None:
    for lfo in lfos:
        slot = lfo.get("slot")
        if slot is None or not (0 <= slot <= 9):
            continue
        params: dict[str, Any] = {}
        if "rate_hz" in lfo:
            params["kParamRate"] = float(lfo["rate_hz"])
        if "smooth" in lfo:
            params["kParamSmooth"] = float(lfo["smooth"])
        if "beat_sync" in lfo:
            params["kParamBeatSync"] = 1.0 if lfo["beat_sync"] else 0.0
        if "mode" in lfo:
            params["kParamMode"] = lfo["mode"]
        if params:
            builder.set_lfo(slot, **params)


def _apply_effects(builder: PresetBuilder, effects: dict) -> None:
    if not effects:
        return

    # Reverb
    rev = effects.get("reverb")
    if rev and rev.get("wet", 0) > 0:
        kw: dict[str, Any] = {"kParamWet": float(rev["wet"])}
        if "size" in rev:
            kw["kParamSize"] = float(rev["size"])
        if "predelay" in rev:
            kw["kParamPreDelay"] = float(rev["predelay"])
        if "width" in rev:
            kw["kParamWidth"] = float(rev["width"])
        builder.add_fx(0, "FXReverb", **kw)

    # Chorus
    cho = effects.get("chorus")
    if cho and cho.get("wet", 0) > 0:
        kw = {"kParamWet": float(cho["wet"])}
        if "rate" in cho:
            kw["kParamRate"] = float(cho["rate"])
        if "depth" in cho:
            kw["kParamDepth"] = float(cho["depth"])
        if "delay" in cho:
            kw["kParamDelay"] = float(cho["delay"])
        builder.add_fx(0, "FXChorus", **kw)

    # Delay
    dly = effects.get("delay")
    if dly and dly.get("wet", 0) > 0:
        kw = {"kParamWet": float(dly["wet"])}
        if "time_l" in dly:
            kw["kParamTimeL"] = float(dly["time_l"])
        if "time_r" in dly:
            kw["kParamTimeR"] = float(dly["time_r"])
        if "feedback" in dly:
            kw["kParamFeedback"] = float(dly["feedback"])
        if "beat_sync" in dly:
            kw["kParamBeatSync"] = 1.0 if dly["beat_sync"] else 0.0
        builder.add_fx(0, "FXDelay", **kw)

    # Distortion
    dst = effects.get("distortion")
    if dst and dst.get("wet", 0) > 0:
        kw = {"kParamWet": float(dst["wet"])}
        if "drive" in dst:
            kw["kParamDrive"] = float(dst["drive"])
        if "mode" in dst:
            kw["kParamMode"] = dst["mode"]
        builder.add_fx(0, "FXDistortion", **kw)

    # Hyper (HyperD unison fattener)
    hyp = effects.get("hyper")
    if hyp and hyp.get("wet", 0) > 0:
        kw = {"kParamWet": float(hyp["wet"])}
        if "detune" in hyp:
            kw["kParamDetune"] = float(hyp["detune"])
        if "unison" in hyp:
            kw["kParamUnison"] = int(hyp["unison"])
        builder.add_fx(0, "FXHyperD", **kw)


def _infer_tags(recipe: dict) -> list[str]:
    tags: list[str] = []
    char = recipe.get("character", "").lower()
    type_tag = {
        "pad": "Pad", "bass": "Bass", "lead": "Lead", "pluck": "Pluck",
        "arp": "Arp", "drum": "Drum", "stab": "Stab", "keys": "Keys",
        "key": "Keys", "fx": "FX",
    }
    for key, val in type_tag.items():
        if key in char:
            tags.append(val)
            break

    # Polyphony hint
    if any(o.get("unison", 1) > 1 for o in recipe.get("oscillators", [])):
        tags.append("Poly")

    if recipe.get("synthesis_approach") == "wavetable":
        tags.append("Wavetable")

    fx = recipe.get("effects", {})
    if fx.get("reverb", {}).get("wet", 0) > 0.3:
        tags.append("Wet")
    if recipe.get("filter_a", {}).get("type", "").startswith("Ladder"):
        tags.append("Analog")

    return tags or ["Centrifuge"]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_preset(
    recipe: dict,
    output_path: Path,
    base_factory: Path | None = None,
) -> Path:
    """Translate a recipe dict into a .SerumPreset file."""
    base = base_factory or DEFAULT_BASE_FACTORY
    builder = PresetBuilder.from_path(base)

    _apply_oscillators(builder, recipe.get("oscillators", []))
    _apply_noise(builder, recipe.get("noise"))
    _apply_sub(builder, recipe.get("sub"))
    _apply_filter(builder, 0, recipe.get("filter_a"))
    _apply_envelope(builder, 0, recipe.get("amp_envelope"))
    _apply_envelope(builder, 1, recipe.get("filter_envelope"))
    _apply_lfos(builder, recipe.get("lfos", []))

    # Clear factory FX before applying recipe effects so the recipe is canonical
    builder.clear_fx(0)
    _apply_effects(builder, recipe.get("effects", {}))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    builder.save(
        output_path,
        name=output_path.stem,
        author="centrifuge --local",
        description=recipe.get("character", ""),
        tags=_infer_tags(recipe),
    )
    return output_path
