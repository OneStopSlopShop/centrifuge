"""
Curated keyword → recipe-modifier vocabulary.

Each entry maps a lowercase keyword (or multi-word phrase) to a partial
recipe dict. The local Sound Design Expert deep-merges these modifiers
on top of a sound-type template to build the final recipe.

Recipe schema mirrors centrifuge/agents/sound_design.py _RECIPE_TOOL.input_schema.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Sound type detection — these keywords pick the base template
# ---------------------------------------------------------------------------

SOUND_TYPE_KEYWORDS: dict[str, str] = {
    "pad": "pad", "pads": "pad",
    "bass": "bass", "808": "bass", "sub bass": "bass", "reese": "bass", "wub": "bass", "wobble bass": "bass",
    "lead": "lead", "leads": "lead",
    "pluck": "pluck", "plucks": "pluck", "plucky": "pluck",
    "arp": "arp", "arpeggio": "arp", "arpeggiator": "arp",
    "drum": "drum", "drums": "drum", "kick": "drum", "snare": "drum", "hat": "drum", "hihat": "drum", "perc": "drum",
    "stab": "stab", "stabs": "stab",
    "key": "key", "keys": "key", "piano": "key", "rhodes": "key", "wurli": "key", "organ": "key",
    "fx": "fx", "riser": "fx", "drop": "fx", "impact": "fx", "sweep fx": "fx",
}


# ---------------------------------------------------------------------------
# Modifier vocabulary — applied on top of the chosen template
# ---------------------------------------------------------------------------

# IMPORTANT: oscillator entries always use a list with a "slot" key so deep_merge
# can stack them by slot id.

VOCAB: dict[str, dict] = {
    # ─── tonal qualities (filter / oscillator) ──────────────────────────────
    "warm":          {"filter_a": {"enabled": True, "type": "LadderMg", "cutoff_normalized": 0.40, "resonance": 12}},
    "warmth":        {"filter_a": {"enabled": True, "type": "LadderMg", "cutoff_normalized": 0.42}},
    "analog":        {"filter_a": {"enabled": True, "type": "LadderMg"},
                      "oscillators": [{"slot": 0, "unison": 3, "detune": 0.12}]},
    "vintage":       {"filter_a": {"enabled": True, "type": "LadderMg", "drive": 18}},
    "bright":        {"filter_a": {"enabled": True, "cutoff_normalized": 0.78}},
    "brilliant":     {"filter_a": {"enabled": True, "cutoff_normalized": 0.85}},
    "dark":          {"filter_a": {"enabled": True, "type": "L24", "cutoff_normalized": 0.20}},
    "muffled":       {"filter_a": {"enabled": True, "type": "L24", "cutoff_normalized": 0.15}},
    "dull":          {"filter_a": {"enabled": True, "type": "L24", "cutoff_normalized": 0.25}},
    "gritty":        {"effects": {"distortion": {"wet": 0.30, "drive": 35, "mode": "kSoftClip"}}},
    "dirty":         {"effects": {"distortion": {"wet": 0.35, "drive": 45, "mode": "kSoftClip"}}},
    "harsh":         {"effects": {"distortion": {"wet": 0.45, "drive": 60, "mode": "kSoftClip"}}},
    "smooth":        {"filter_a": {"enabled": True, "resonance": 5}, "amp_envelope": {"attack_curve": 60}},
    "rich":          {"oscillators": [{"slot": 0, "unison": 5, "detune": 0.18, "stereo_spread": 0.7}]},
    "fat":           {"oscillators": [{"slot": 0, "unison": 7, "detune": 0.22, "stereo_spread": 0.85}]},
    "huge":          {"oscillators": [{"slot": 0, "unison": 9, "detune": 0.25, "stereo_spread": 1.0}],
                      "effects": {"reverb": {"wet": 0.35, "size": 0.7}}},
    "thin":          {"oscillators": [{"slot": 0, "unison": 1, "detune": 0.0}]},
    "hollow":        {"filter_a": {"enabled": True, "type": "B12", "cutoff_normalized": 0.45, "resonance": 30}},
    "metallic":      {"filter_a": {"enabled": True, "type": "CombP", "resonance": 50}},
    "wooden":        {"filter_a": {"enabled": True, "type": "FormantONE", "cutoff_normalized": 0.5}},
    "vocal":         {"filter_a": {"enabled": True, "type": "FormantTWO", "cutoff_normalized": 0.55}},
    "glassy":        {"filter_a": {"enabled": True, "cutoff_normalized": 0.85},
                      "effects": {"chorus": {"wet": 0.2, "rate": 0.6, "depth": 0.4}}},
    "icy":           {"filter_a": {"enabled": True, "type": "H12", "cutoff_normalized": 0.70},
                      "effects": {"reverb": {"wet": 0.4, "size": 0.85}}},
    "lush":          {"oscillators": [{"slot": 0, "unison": 5, "detune": 0.15, "stereo_spread": 0.75}],
                      "effects": {"reverb": {"wet": 0.35, "size": 0.7},
                                  "chorus": {"wet": 0.25, "rate": 0.6, "depth": 0.5}}},
    "clean":         {"effects": {"distortion": {"wet": 0.0}}},
    "saturated":     {"effects": {"distortion": {"wet": 0.20, "drive": 25, "mode": "kSoftClip"}}},

    # ─── dynamics / envelope ────────────────────────────────────────────────
    "punchy":        {"amp_envelope": {"attack_s": 0.001, "decay_s": 0.15, "sustain": 0.5}},
    "snappy":        {"amp_envelope": {"attack_s": 0.001, "decay_s": 0.10}},
    "soft":          {"amp_envelope": {"attack_s": 0.05, "release_s": 0.6}},
    "gentle":        {"amp_envelope": {"attack_s": 0.08, "release_s": 0.8}},
    "slow":          {"amp_envelope": {"attack_s": 0.4, "release_s": 1.5}},
    "slow attack":   {"amp_envelope": {"attack_s": 0.6}},
    "fast attack":   {"amp_envelope": {"attack_s": 0.001}},
    "long release":  {"amp_envelope": {"release_s": 2.5}},
    "short release": {"amp_envelope": {"release_s": 0.15}},
    "long":          {"amp_envelope": {"release_s": 2.0, "sustain": 0.85}},
    "short":         {"amp_envelope": {"release_s": 0.2, "decay_s": 0.15}},
    "sustained":     {"amp_envelope": {"sustain": 0.95, "release_s": 1.0}},
    "staccato":      {"amp_envelope": {"attack_s": 0.001, "decay_s": 0.08, "sustain": 0.0, "release_s": 0.1}},
    "swell":         {"amp_envelope": {"attack_s": 1.2, "release_s": 1.5, "attack_curve": 65}},
    "evolving":      {"lfos": [{"slot": 0, "rate_hz": 0.15, "smooth": 0.9, "destination": "filter cutoff"}]},

    # ─── filter character ───────────────────────────────────────────────────
    "low pass":      {"filter_a": {"enabled": True, "type": "L24"}},
    "lowpass":       {"filter_a": {"enabled": True, "type": "L24"}},
    "high pass":     {"filter_a": {"enabled": True, "type": "H24", "cutoff_normalized": 0.30}},
    "highpass":      {"filter_a": {"enabled": True, "type": "H24", "cutoff_normalized": 0.30}},
    "band pass":     {"filter_a": {"enabled": True, "type": "B12", "cutoff_normalized": 0.45}},
    "bandpass":      {"filter_a": {"enabled": True, "type": "B12", "cutoff_normalized": 0.45}},
    "resonant":      {"filter_a": {"enabled": True, "resonance": 55}},
    "screaming":     {"filter_a": {"enabled": True, "resonance": 80, "drive": 40}},
    "acid":          {"filter_a": {"enabled": True, "type": "LadderAcid", "resonance": 65, "drive": 30, "cutoff_normalized": 0.45},
                      "filter_envelope": {"attack_s": 0.001, "decay_s": 0.30, "sustain": 0.0, "release_s": 0.15, "depth": 70}},
    "moog":          {"filter_a": {"enabled": True, "type": "LadderMg", "resonance": 25}},
    "ladder":        {"filter_a": {"enabled": True, "type": "LadderMg"}},
    "303":           {"filter_a": {"enabled": True, "type": "LadderAcid", "resonance": 70, "cutoff_normalized": 0.40}},
    "formant":       {"filter_a": {"enabled": True, "type": "FormantONE"}},
    "comb":          {"filter_a": {"enabled": True, "type": "CombP", "resonance": 40}},
    "sweep":         {"filter_envelope": {"attack_s": 0.6, "decay_s": 0.8, "sustain": 0.4, "release_s": 1.2, "depth": 60}},
    "modulated":     {"lfos": [{"slot": 0, "rate_hz": 1.5, "smooth": 0.5, "destination": "filter cutoff"}]},
    "open":          {"filter_a": {"enabled": True, "cutoff_normalized": 0.85}},
    "closed":        {"filter_a": {"enabled": True, "cutoff_normalized": 0.20}},

    # ─── effects ────────────────────────────────────────────────────────────
    "reverb":        {"effects": {"reverb": {"wet": 0.30, "size": 0.6, "predelay": 0.02, "width": 1.0}}},
    "huge reverb":   {"effects": {"reverb": {"wet": 0.55, "size": 0.90, "predelay": 0.05, "width": 1.0}}},
    "small reverb":  {"effects": {"reverb": {"wet": 0.18, "size": 0.30, "predelay": 0.0, "width": 0.6}}},
    "hall":          {"effects": {"reverb": {"wet": 0.40, "size": 0.85, "predelay": 0.04, "width": 1.0}}},
    "room":          {"effects": {"reverb": {"wet": 0.22, "size": 0.40, "predelay": 0.01, "width": 0.7}}},
    "plate":         {"effects": {"reverb": {"wet": 0.30, "size": 0.55, "predelay": 0.0, "width": 0.9}}},
    "spacy":         {"effects": {"reverb": {"wet": 0.50, "size": 0.85, "width": 1.0},
                                  "delay": {"wet": 0.20, "time_l": 0.375, "time_r": 0.5, "feedback": 0.45}}},
    "ambient":       {"effects": {"reverb": {"wet": 0.55, "size": 0.90, "width": 1.0}},
                      "amp_envelope": {"attack_s": 0.6, "release_s": 2.5}},
    "delay":         {"effects": {"delay": {"wet": 0.25, "time_l": 0.375, "time_r": 0.5, "feedback": 0.40, "beat_sync": True}}},
    "echo":          {"effects": {"delay": {"wet": 0.28, "time_l": 0.5, "time_r": 0.5, "feedback": 0.50, "beat_sync": True}}},
    "ping pong":     {"effects": {"delay": {"wet": 0.30, "time_l": 0.375, "time_r": 0.75, "feedback": 0.50, "beat_sync": True}}},
    "chorus":        {"effects": {"chorus": {"wet": 0.30, "rate": 0.8, "depth": 0.5, "delay": 8.0}}},
    "ensemble":      {"effects": {"chorus": {"wet": 0.45, "rate": 1.2, "depth": 0.7, "delay": 12.0}}},
    "distortion":    {"effects": {"distortion": {"wet": 0.40, "drive": 50, "mode": "kSoftClip"}}},
    "fuzz":          {"effects": {"distortion": {"wet": 0.55, "drive": 75, "mode": "kHardClip"}}},
    "overdrive":     {"effects": {"distortion": {"wet": 0.30, "drive": 40, "mode": "kSoftClip"}}},
    "wide":          {"oscillators": [{"slot": 0, "stereo_spread": 1.0}],
                      "effects": {"chorus": {"wet": 0.20, "rate": 0.5, "depth": 0.4}}},
    "stereo":        {"oscillators": [{"slot": 0, "stereo_spread": 0.85}]},
    "mono":          {"oscillators": [{"slot": 0, "stereo_spread": 0.0, "unison": 1}]},
    "compressed":    {"effects": {"hyper": {"wet": 0.0}}},
    "supersaw":      {"oscillators": [{"slot": 0, "wavetable": "S2 Tables/Default Shapes.wav",
                                       "wavetable_pos": 256.0, "unison": 7, "detune": 0.20, "stereo_spread": 0.85}],
                      "effects": {"hyper": {"wet": 0.6, "detune": 0.25, "unison": 7}}},

    # ─── modulation ─────────────────────────────────────────────────────────
    "wobble":        {"lfos": [{"slot": 0, "rate_hz": 4.0, "beat_sync": True, "smooth": 0.3, "destination": "filter cutoff"}],
                      "filter_a": {"enabled": True, "resonance": 50}},
    "wobbly":        {"lfos": [{"slot": 0, "rate_hz": 3.0, "beat_sync": True, "smooth": 0.4, "destination": "filter cutoff"}]},
    "vibrato":       {"lfos": [{"slot": 0, "rate_hz": 5.5, "smooth": 0.4, "destination": "pitch"}]},
    "tremolo":       {"lfos": [{"slot": 0, "rate_hz": 6.0, "smooth": 0.2, "destination": "amp"}]},
    "pulsing":       {"lfos": [{"slot": 0, "rate_hz": 2.0, "beat_sync": True, "smooth": 0.5, "destination": "amp"}]},
    "rhythmic":      {"lfos": [{"slot": 0, "rate_hz": 4.0, "beat_sync": True, "destination": "amp"}]},
    "random":        {"lfos": [{"slot": 0, "rate_hz": 3.0, "mode": "Free", "destination": "filter cutoff"}]},

    # ─── pitch / range ──────────────────────────────────────────────────────
    "low":           {"oscillators": [{"slot": 0, "octave": -1}]},
    "deep":          {"oscillators": [{"slot": 0, "octave": -2}]},
    "high":          {"oscillators": [{"slot": 0, "octave": 1}]},
    "ethereal":      {"oscillators": [{"slot": 0, "octave": 1}],
                      "effects": {"reverb": {"wet": 0.5, "size": 0.85}}},
    "sub":           {"sub": {"enabled": True, "volume": 0.7, "octave": -2}},
    "octave up":     {"oscillators": [{"slot": 0, "octave": 1}]},
    "octave down":   {"oscillators": [{"slot": 0, "octave": -1}]},
    "detuned":       {"oscillators": [{"slot": 0, "fine": 8.0, "unison": 3, "detune": 0.15}]},
    "in tune":       {"oscillators": [{"slot": 0, "fine": 0.0, "detune": 0.0}]},

    # ─── synthesis approach ─────────────────────────────────────────────────
    "fm":            {"synthesis_approach": "fm",
                      "oscillators": [{"slot": 0, "wavetable": "S2 Tables/FM.wav"}]},
    "wavetable":     {"synthesis_approach": "wavetable"},
    "granular":      {"synthesis_approach": "granular"},
    "additive":      {"synthesis_approach": "additive"},
    "spectral":      {"synthesis_approach": "spectral"},
    "noise":         {"noise": {"enabled": True, "volume": 0.5, "color": 0.5}},
    "noisy":         {"noise": {"enabled": True, "volume": 0.6, "color": 0.7}},
    "sawtooth":      {"oscillators": [{"slot": 0, "wavetable": "S2 Tables/Default Shapes.wav", "wavetable_pos": 1024.0}]},
    "saw":           {"oscillators": [{"slot": 0, "wavetable": "S2 Tables/Default Shapes.wav", "wavetable_pos": 1024.0}]},
    "square":        {"oscillators": [{"slot": 0, "wavetable": "S2 Tables/Default Shapes.wav", "wavetable_pos": 1500.0}]},
    "sine":          {"oscillators": [{"slot": 0, "wavetable": "S2 Tables/Default Shapes.wav", "wavetable_pos": 0.0}]},
    "triangle":      {"oscillators": [{"slot": 0, "wavetable": "S2 Tables/Default Shapes.wav", "wavetable_pos": 512.0}]},
}


# ---------------------------------------------------------------------------
# Multi-word phrase index — phrases must be matched before single words
# ---------------------------------------------------------------------------

MULTI_WORD_PHRASES: list[str] = sorted(
    [k for k in {**VOCAB, **SOUND_TYPE_KEYWORDS} if " " in k],
    key=lambda s: -len(s),  # longest phrases first
)
