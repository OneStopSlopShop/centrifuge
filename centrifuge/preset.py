"""
PresetBuilder — high-level API for constructing Serum 2 presets.

Always start from a factory preset as the base so all components have valid
defaults, then patch only what you need.  Use the raw set_component/get_component
methods for anything not covered by the high-level helpers.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

from centrifuge.codec import pack, unpack


# FX type integer → class name inside the FX dict
FX_TYPES: dict[str, int] = {
    "FXDistortion": 0,
    "FXFlanger": 1,
    "FXPhaser": 2,
    "FXChorus": 3,
    "FXDelay": 4,
    "FXComp": 5,
    "FXReverb": 6,
    "FXEQ": 7,
    "FXFilter": 8,
    "FXHyperD": 9,
    "FXBode": 10,
    "FXConv": 11,
    "FXUtils": 12,
}

# Canonical filter type strings accepted by VoiceFilter.kParamType
FILTER_TYPES = [
    "L6", "L12", "L18", "L24",
    "H6", "H12", "H18", "H24",
    "B12", "B24", "BN12", "BPN12",
    "LH12", "LBH12", "LBH24", "LNH24",
    "LPH24", "HEQ12", "HN12", "PP12",
    "LadderMg", "LadderAcid", "LadderEMS",
    "MgL6", "MgL18", "MgL24", "DirtyMg",
    "CombP", "CombN", "CombH6N", "CombHL6N", "Comb2",
    "FlangeP", "FlangeN", "FlangeL6P",
    "Phase24P", "Phase24N", "Phase48HL6P",
    "FormantONE", "FormantTWO",
    "Allpasses", "Diffuser", "Exp", "ExpBPF",
    "BandReject", "RM", "Scream", "DJMixer",
    "Reverb1", "Wsp",
    "DistComb1LP", "DistComb1BP", "DistComb2LP",
]

# Modulation source type indices (first element of the source array)
MOD_SOURCES = {
    "env1": [0, 0], "env2": [0, 1], "env3": [0, 2], "env4": [0, 3],
    "lfo1": [1, 0], "lfo2": [1, 1], "lfo3": [1, 2], "lfo4": [1, 3],
    "lfo5": [1, 4], "lfo6": [1, 5], "lfo7": [1, 6], "lfo8": [1, 7],
    "macro1": [2, 0], "macro2": [2, 1], "macro3": [2, 2], "macro4": [2, 3],
    "macro5": [2, 4], "macro6": [2, 5], "macro7": [2, 6], "macro8": [2, 7],
    "velocity": [3, 16], "note": [3, 0], "modwheel": [3, 25],
    "aftertouch": [3, 26], "pitchbend": [3, 27],
    "amp_env": [0, 0],
    "filter_env": [0, 1],
}


class PresetBuilder:
    """Build a Serum 2 preset by patching a loaded base preset."""

    def __init__(self, data: dict) -> None:
        self._preset = copy.deepcopy(data)

    # ------------------------------------------------------------------
    # Factory constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_path(cls, path: Path) -> PresetBuilder:
        """Load an existing .SerumPreset as the base."""
        return cls(unpack(path))

    # ------------------------------------------------------------------
    # Raw component access
    # ------------------------------------------------------------------

    def get_component(self, name: str) -> Any:
        """Return a component dict (or None)."""
        return self._preset["data"].get(name)

    def set_component(self, name: str, params: dict) -> PresetBuilder:
        """Merge params into a component's plainParams dict."""
        comp = self._preset["data"].setdefault(name, {"plainParams": {}})
        if not isinstance(comp, dict):
            return self
        pp = comp.get("plainParams")
        if pp == "default" or pp is None:
            comp["plainParams"] = {}
        comp["plainParams"].update(params)
        return self

    def all_params(self) -> dict:
        """Return the full decoded data dict (live reference)."""
        return self._preset["data"]

    # ------------------------------------------------------------------
    # Oscillators
    # ------------------------------------------------------------------

    def set_oscillator(self, slot: int, **params) -> PresetBuilder:
        """
        Set top-level oscillator params for slot 0/1/2/3/4.

        Common params: kParamVolume, kParamPan, kParamOctave, kParamFine,
        kParamUnison, kParamDetune, kParamDetuneWid, kParamUnisonStereo,
        kParamEnable, kParamType
        """
        return self.set_component(f"Oscillator{slot}", params)

    def set_wavetable_osc(self, slot: int, wavetable: str | None = None, **params) -> PresetBuilder:
        """
        Configure the WTOsc sub-oscillator for the given Oscillator slot.

        wavetable: relative path inside Serum 2 Tables dir, e.g. "S2 Tables/Default Shapes.wav"
        Common params: kParamTablePos (0-2048), kParamWarpMenu, kParamWarp, kParamWarp2,
        kParamRandomPhase, kParamInitialPhase
        """
        key = f"WTOsc{slot}"
        osc = self._preset["data"].get(f"Oscillator{slot}", {})
        wt = osc.get(key, {})
        if not isinstance(wt, dict):
            wt = {}
        if wavetable:
            wt["relativePathToWT"] = wavetable
        pp = wt.get("plainParams")
        if pp == "default" or pp is None:
            wt["plainParams"] = {}
        wt["plainParams"].update(params)
        osc[key] = wt
        self._preset["data"][f"Oscillator{slot}"] = osc
        return self

    # ------------------------------------------------------------------
    # Envelopes
    # ------------------------------------------------------------------

    def set_envelope(self, slot: int, **params) -> PresetBuilder:
        """
        Set envelope params. slot 0=Amp, 1=Filter, 2-3=Auxiliary.

        Params: kParamAttack, kParamHold, kParamDecay, kParamSustain,
        kParamRelease, kParamCurve1 (attack curve 0-100),
        kParamCurve2 (decay curve 0-100), kParamCurve3 (release curve 0-100),
        kParamStart
        """
        return self.set_component(f"Env{slot}", params)

    # ------------------------------------------------------------------
    # LFOs
    # ------------------------------------------------------------------

    def set_lfo(self, slot: int, **params) -> PresetBuilder:
        """
        Set LFO params. slot 0-9.

        Params: kParamRate (Hz), kParamSmooth, kParamRise, kParamDelay,
        kParamBeatSync (0/1), kParamMode ("Free" | "Envelope" | "Trigger"),
        kParamType ("RandomSH" | "Lorenz" | "Rossler" | "Path"),
        kParamMono, kParamPhase, kParamAnchored
        """
        return self.set_component(f"LFO{slot}", params)

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------

    def set_filter(self, slot: int, filter_type: str | None = None, **params) -> PresetBuilder:
        """
        Configure a voice filter. slot 0 or 1.

        filter_type: one of FILTER_TYPES (e.g. "L24", "LadderMg", "LadderAcid")
        Params: kParamFreq (0-1 normalized), kParamReso (0-100),
        kParamDrive (0-100), kParamVar, kParamEnable (0/1),
        kParamKeyTrack, kParamStereo, kParamWet, kParamLevelOut
        """
        if filter_type:
            params["kParamType"] = filter_type
        params.setdefault("kParamEnable", 1.0)
        return self.set_component(f"VoiceFilter{slot}", params)

    # ------------------------------------------------------------------
    # Effects
    # ------------------------------------------------------------------

    def add_fx(self, rack: int, fx_class: str, **params) -> PresetBuilder:
        """
        Append an effect to FXRack0/1/2.

        fx_class: e.g. "FXReverb", "FXChorus", "FXDistortion" (see FX_TYPES)
        params: effect-specific kParam* values (e.g. kParamWet, kParamSize)
        """
        if fx_class not in FX_TYPES:
            raise ValueError(f"Unknown FX class '{fx_class}'. Valid: {list(FX_TYPES)}")

        rack_key = f"FXRack{rack}"
        rack_obj = self._preset["data"].setdefault(rack_key, {"FX": [], "displayName": "", "plainParams": "default"})
        if not isinstance(rack_obj, dict):
            rack_obj = {"FX": [], "displayName": "", "plainParams": "default"}
            self._preset["data"][rack_key] = rack_obj
        fx_list = rack_obj.setdefault("FX", [])

        fx_entry = {
            fx_class: {"plainParams": params},
            "flex": [{}, {}],
            "kUIParamMixOrGain": 0.0,
            "type": FX_TYPES[fx_class],
        }
        fx_list.append(fx_entry)
        return self

    def clear_fx(self, rack: int) -> PresetBuilder:
        """Remove all effects from a rack."""
        rack_obj = self._preset["data"].get(f"FXRack{rack}", {})
        if isinstance(rack_obj, dict):
            rack_obj["FX"] = []
        return self

    # ------------------------------------------------------------------
    # Macros
    # ------------------------------------------------------------------

    def set_macro(self, slot: int, value: float, name: str = "") -> PresetBuilder:
        """Set Macro slot 0-7 value (0-100) and optional label."""
        macro = self._preset["data"].setdefault(f"Macro{slot}", {})
        if not isinstance(macro, dict):
            macro = {}
            self._preset["data"][f"Macro{slot}"] = macro
        pp = macro.get("plainParams")
        if pp == "default" or pp is None:
            macro["plainParams"] = {}
        macro["plainParams"]["kParamValue"] = float(value)
        if name:
            macro["name"] = name
        return self

    # ------------------------------------------------------------------
    # Modulation routing
    # ------------------------------------------------------------------

    def add_mod(
        self,
        source: str | list,
        dest_module_type: str,
        dest_module_id: int,
        dest_param_name: str,
        dest_param_id: int,
        amount: float,
        bipolar: bool = True,
    ) -> PresetBuilder:
        """
        Wire a modulation slot.

        source: either a key from MOD_SOURCES (e.g. "lfo1", "macro1", "velocity")
                or a raw [type_id, slot_id] list
        dest_module_type: e.g. "VoiceFilter", "Oscillator", "WTOsc"
        dest_module_id: 0-4 for oscillators, 0-1 for filters, etc.
        dest_param_name: kParam* string
        dest_param_id: integer param index (look up from existing presets)
        amount: modulation amount
        """
        src = MOD_SOURCES[source] if isinstance(source, str) else list(source)

        # find the first empty mod slot
        data = self._preset["data"]
        slot_idx = 0
        while f"ModSlot{slot_idx}" in data and data[f"ModSlot{slot_idx}"].get("source") is not None:
            slot_idx += 1
            if slot_idx >= 64:
                raise ValueError("All 64 mod slots are in use")

        data[f"ModSlot{slot_idx}"] = {
            "destModuleID": dest_module_id,
            "destModuleParamID": dest_param_id,
            "destModuleParamName": dest_param_name,
            "destModuleTypeString": dest_module_type,
            "plainParams": {
                "kParamAmount": float(amount),
                "kParamBipolar": 1.0 if bipolar else 0.0,
            },
            "source": src,
        }
        return self

    # ------------------------------------------------------------------
    # Global settings
    # ------------------------------------------------------------------

    def set_global(self, **params) -> PresetBuilder:
        """
        Set Global0 params.

        Common: kParamMasterVolume (0-1), kParamPolyCount (1-16),
        kParamMonoToggle (0/1), kParamPortamentoTime, kParamTranspose,
        kParamOversampling (0-4), kParamBendRangeUp, kParamBendRangeDn
        """
        return self.set_component("Global0", params)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, path: Path, name: str | None = None, author: str = "", description: str = "", tags: list[str] | None = None) -> None:
        """Write the preset to a .SerumPreset file."""
        meta = dict(self._preset.get("metadata", {}))
        meta.setdefault("fileType", "SerumPreset")
        meta.setdefault("product", "Serum2")
        meta.setdefault("vendor", "Xfer Records")
        meta.setdefault("version", 4.0)
        meta.setdefault("url", "https://xferrecords.com/")
        if name:
            meta["presetName"] = name
        if author:
            meta["presetAuthor"] = author
        if description:
            meta["presetDescription"] = description
        if tags is not None:
            meta["tags"] = tags

        pack({"metadata": meta, "data": self._preset["data"]}, path)
