"""
Sound-type recipe templates.

Each function returns a baseline recipe dict matching the cloud schema in
centrifuge/agents/sound_design.py.  The vocabulary modifiers stack on top.
"""

from __future__ import annotations

from typing import Callable

DEFAULT_WT = "S2 Tables/Default Shapes.wav"


def pad_template() -> dict:
    return {
        "synthesis_approach": "wavetable",
        "character": "pad",
        "oscillators": [
            {"slot": 0, "enabled": True, "volume": 0.85, "octave": 0,
             "unison": 5, "detune": 0.18, "stereo_spread": 0.75,
             "wavetable": DEFAULT_WT, "wavetable_pos": 800.0},
            {"slot": 1, "enabled": True, "volume": 0.55, "octave": 0, "fine": 7.0,
             "unison": 3, "detune": 0.12, "stereo_spread": 0.6,
             "wavetable": DEFAULT_WT, "wavetable_pos": 1024.0},
        ],
        "amp_envelope": {"attack_s": 0.4, "hold_s": 0.0, "decay_s": 0.6,
                         "sustain": 0.85, "release_s": 1.5, "attack_curve": 60},
        "filter_a": {"enabled": True, "type": "L24", "cutoff_normalized": 0.55,
                     "resonance": 8.0, "drive": 0.0, "key_track": 0.0},
        "filter_envelope": {"attack_s": 0.6, "decay_s": 0.8, "sustain": 0.5,
                            "release_s": 1.2, "depth": 30},
        "lfos": [],
        "effects": {
            "reverb": {"wet": 0.35, "size": 0.70, "predelay": 0.03, "width": 1.0},
            "chorus": {"wet": 0.20, "rate": 0.6, "depth": 0.5, "delay": 10.0},
        },
    }


def bass_template() -> dict:
    return {
        "synthesis_approach": "subtractive",
        "character": "bass",
        "oscillators": [
            {"slot": 0, "enabled": True, "volume": 0.95, "octave": -1,
             "unison": 1, "detune": 0.0, "stereo_spread": 0.0,
             "wavetable": DEFAULT_WT, "wavetable_pos": 1024.0},
        ],
        "sub": {"enabled": True, "volume": 0.7, "octave": -2},
        "amp_envelope": {"attack_s": 0.001, "hold_s": 0.0, "decay_s": 0.30,
                         "sustain": 0.85, "release_s": 0.20, "attack_curve": 40},
        "filter_a": {"enabled": True, "type": "L24", "cutoff_normalized": 0.40,
                     "resonance": 15.0, "drive": 10.0, "key_track": 0.3},
        "filter_envelope": {"attack_s": 0.001, "decay_s": 0.20, "sustain": 0.20,
                            "release_s": 0.15, "depth": 50},
        "lfos": [],
        "effects": {},
    }


def lead_template() -> dict:
    return {
        "synthesis_approach": "wavetable",
        "character": "lead",
        "oscillators": [
            {"slot": 0, "enabled": True, "volume": 0.9, "octave": 0,
             "unison": 3, "detune": 0.10, "stereo_spread": 0.5,
             "wavetable": DEFAULT_WT, "wavetable_pos": 1024.0},
        ],
        "amp_envelope": {"attack_s": 0.005, "hold_s": 0.0, "decay_s": 0.30,
                         "sustain": 0.80, "release_s": 0.40, "attack_curve": 50},
        "filter_a": {"enabled": True, "type": "L24", "cutoff_normalized": 0.65,
                     "resonance": 15.0, "drive": 5.0, "key_track": 0.2},
        "filter_envelope": {"attack_s": 0.05, "decay_s": 0.30, "sustain": 0.50,
                            "release_s": 0.30, "depth": 25},
        "lfos": [],
        "effects": {
            "reverb": {"wet": 0.20, "size": 0.50, "predelay": 0.01, "width": 0.9},
            "delay": {"wet": 0.15, "time_l": 0.375, "time_r": 0.5,
                      "feedback": 0.30, "beat_sync": True},
        },
    }


def pluck_template() -> dict:
    return {
        "synthesis_approach": "wavetable",
        "character": "pluck",
        "oscillators": [
            {"slot": 0, "enabled": True, "volume": 0.9, "octave": 0,
             "unison": 1, "detune": 0.0, "stereo_spread": 0.0,
             "wavetable": DEFAULT_WT, "wavetable_pos": 1024.0},
        ],
        "amp_envelope": {"attack_s": 0.001, "hold_s": 0.0, "decay_s": 0.30,
                         "sustain": 0.0, "release_s": 0.25, "attack_curve": 40},
        "filter_a": {"enabled": True, "type": "L24", "cutoff_normalized": 0.55,
                     "resonance": 12.0, "drive": 0.0, "key_track": 0.4},
        "filter_envelope": {"attack_s": 0.001, "decay_s": 0.25, "sustain": 0.0,
                            "release_s": 0.20, "depth": 45},
        "lfos": [],
        "effects": {
            "reverb": {"wet": 0.20, "size": 0.45, "predelay": 0.0, "width": 0.8},
        },
    }


def arp_template() -> dict:
    return {
        "synthesis_approach": "wavetable",
        "character": "arp",
        "oscillators": [
            {"slot": 0, "enabled": True, "volume": 0.85, "octave": 0,
             "unison": 1, "detune": 0.0, "stereo_spread": 0.0,
             "wavetable": DEFAULT_WT, "wavetable_pos": 1024.0},
        ],
        "amp_envelope": {"attack_s": 0.001, "hold_s": 0.0, "decay_s": 0.20,
                         "sustain": 0.0, "release_s": 0.15, "attack_curve": 40},
        "filter_a": {"enabled": True, "type": "L24", "cutoff_normalized": 0.60,
                     "resonance": 10.0, "drive": 0.0, "key_track": 0.3},
        "filter_envelope": {"attack_s": 0.001, "decay_s": 0.15, "sustain": 0.0,
                            "release_s": 0.10, "depth": 35},
        "lfos": [],
        "effects": {
            "delay": {"wet": 0.30, "time_l": 0.375, "time_r": 0.5,
                      "feedback": 0.40, "beat_sync": True},
            "reverb": {"wet": 0.20, "size": 0.50, "predelay": 0.01, "width": 0.8},
        },
    }


def drum_template() -> dict:
    return {
        "synthesis_approach": "subtractive",
        "character": "drum",
        "oscillators": [
            {"slot": 0, "enabled": True, "volume": 0.95, "octave": -1,
             "unison": 1, "detune": 0.0, "stereo_spread": 0.0,
             "wavetable": DEFAULT_WT, "wavetable_pos": 0.0},
        ],
        "noise": {"enabled": True, "volume": 0.4, "color": 0.6},
        "amp_envelope": {"attack_s": 0.0005, "hold_s": 0.0, "decay_s": 0.15,
                         "sustain": 0.0, "release_s": 0.08, "attack_curve": 30},
        "filter_a": {"enabled": True, "type": "L12", "cutoff_normalized": 0.40,
                     "resonance": 5.0, "drive": 0.0, "key_track": 0.0},
        "filter_envelope": {"attack_s": 0.0005, "decay_s": 0.10, "sustain": 0.0,
                            "release_s": 0.05, "depth": 40},
        "lfos": [],
        "effects": {},
    }


def stab_template() -> dict:
    return {
        "synthesis_approach": "wavetable",
        "character": "stab",
        "oscillators": [
            {"slot": 0, "enabled": True, "volume": 0.9, "octave": 0,
             "unison": 3, "detune": 0.12, "stereo_spread": 0.5,
             "wavetable": DEFAULT_WT, "wavetable_pos": 1024.0},
        ],
        "amp_envelope": {"attack_s": 0.001, "hold_s": 0.0, "decay_s": 0.20,
                         "sustain": 0.10, "release_s": 0.25, "attack_curve": 40},
        "filter_a": {"enabled": True, "type": "L24", "cutoff_normalized": 0.55,
                     "resonance": 20.0, "drive": 5.0, "key_track": 0.2},
        "filter_envelope": {"attack_s": 0.001, "decay_s": 0.18, "sustain": 0.05,
                            "release_s": 0.15, "depth": 50},
        "lfos": [],
        "effects": {
            "reverb": {"wet": 0.25, "size": 0.55, "predelay": 0.01, "width": 0.9},
        },
    }


def key_template() -> dict:
    return {
        "synthesis_approach": "wavetable",
        "character": "keys",
        "oscillators": [
            {"slot": 0, "enabled": True, "volume": 0.9, "octave": 0,
             "unison": 1, "detune": 0.0, "stereo_spread": 0.3,
             "wavetable": DEFAULT_WT, "wavetable_pos": 700.0},
        ],
        "amp_envelope": {"attack_s": 0.005, "hold_s": 0.0, "decay_s": 0.40,
                         "sustain": 0.60, "release_s": 0.50, "attack_curve": 50},
        "filter_a": {"enabled": True, "type": "L12", "cutoff_normalized": 0.65,
                     "resonance": 8.0, "drive": 0.0, "key_track": 0.3},
        "filter_envelope": {"attack_s": 0.005, "decay_s": 0.30, "sustain": 0.40,
                            "release_s": 0.30, "depth": 20},
        "lfos": [],
        "effects": {
            "reverb": {"wet": 0.20, "size": 0.50, "predelay": 0.01, "width": 0.85},
            "chorus": {"wet": 0.15, "rate": 0.5, "depth": 0.3, "delay": 8.0},
        },
    }


def fx_template() -> dict:
    return {
        "synthesis_approach": "wavetable",
        "character": "fx",
        "oscillators": [
            {"slot": 0, "enabled": True, "volume": 0.85, "octave": 0,
             "unison": 5, "detune": 0.20, "stereo_spread": 0.85,
             "wavetable": DEFAULT_WT, "wavetable_pos": 1500.0},
        ],
        "noise": {"enabled": True, "volume": 0.3, "color": 0.5},
        "amp_envelope": {"attack_s": 0.6, "hold_s": 0.0, "decay_s": 0.5,
                         "sustain": 0.5, "release_s": 1.0, "attack_curve": 65},
        "filter_a": {"enabled": True, "type": "L24", "cutoff_normalized": 0.50,
                     "resonance": 15.0, "drive": 0.0, "key_track": 0.0},
        "filter_envelope": {"attack_s": 1.0, "decay_s": 0.8, "sustain": 0.6,
                            "release_s": 1.0, "depth": 60},
        "lfos": [
            {"slot": 0, "rate_hz": 0.2, "smooth": 0.9, "destination": "filter cutoff"},
        ],
        "effects": {
            "reverb": {"wet": 0.50, "size": 0.85, "predelay": 0.05, "width": 1.0},
            "delay": {"wet": 0.25, "time_l": 0.5, "time_r": 0.75,
                      "feedback": 0.50, "beat_sync": True},
        },
    }


TEMPLATES: dict[str, Callable[[], dict]] = {
    "pad":   pad_template,
    "bass":  bass_template,
    "lead":  lead_template,
    "pluck": pluck_template,
    "arp":   arp_template,
    "drum":  drum_template,
    "stab":  stab_template,
    "key":   key_template,
    "fx":    fx_template,
}

DEFAULT_TEMPLATE = "lead"
