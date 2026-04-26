# centrifuge

AI-driven Serum 2 preset generator. Describe a sound in plain language (or supply a reference audio file) and get a loadable `.SerumPreset` file back.

Two Claude agents collaborate under the hood:

- **Sound Design Expert** — translates your description into a synthesis recipe (oscillators, filter, envelopes, effects)
- **Serum 2 Expert** — maps that recipe to exact Serum 2 parameter values and writes the preset file iteratively using tool calls

---

## Requirements

- [uv](https://github.com/astral-sh/uv) for Python environment management
- Python 3.11+
- Xfer Records Serum 2 installed (factory presets are used as base templates)
- For LLM-driven generation, **one** of:
  - `ANTHROPIC_API_KEY` env var (default cloud mode), or
  - [Claude Code](https://claude.com/claude-code) CLI on PATH (use `--noapi`)
- For purely offline algorithmic generation: **nothing else** — use `--local`

---

## Installation

```bash
git clone <repo>
cd centrifuge
uv sync
```

This creates a `.venv` and installs all dependencies (`cbor2`, `zstandard`, `anthropic`, `click`, `librosa`, `soundfile`).

Verify the install:

```bash
uv run centrifuge --help
```

---

## Usage

### Three modes

| Mode | Flag | Backend | Requirements |
|------|------|---------|--------------|
| **Cloud** (default) | none | Anthropic API | `ANTHROPIC_API_KEY` |
| **No-API** | `--noapi` | Claude Code subprocess | `claude` CLI on PATH (Pro/Max/Team plan) |
| **Local** | `--local` | Pure algorithmic vocabulary | nothing — fully offline |

`--local` and `--noapi` are mutually exclusive.

### Generate a preset from a description

```bash
uv run centrifuge generate "warm analog pad with slow attack" --output pad.SerumPreset
```

```bash
uv run centrifuge generate "punchy 808 bass with low-pass filter sweep" --output 808.SerumPreset
```

```bash
uv run centrifuge generate "aggressive reese bass, heavy unison" --output reese.SerumPreset
```

### Match a sound from an audio file

```bash
uv run centrifuge generate "match this sound" --audio reference.wav --output matched.SerumPreset
```

The audio file is analysed with librosa (spectral centroid, attack time, pitch, harmonicity, MFCCs) and the extracted features are passed to the Sound Design Expert as context.

### Model selection

Defaults to `claude-opus-4-7`. Override with `--model`:

```bash
uv run centrifuge generate "bright pluck" --output pluck.SerumPreset --model claude-sonnet-4-6
```

### `--noapi` mode (Claude Code, no API key)

Add `--noapi` to drive [Claude Code](https://claude.com/claude-code) as a subprocess instead of calling the Anthropic API. Same LLM-grade intelligence as cloud mode — useful when you have a Claude.ai subscription but no API key.

```bash
uv run centrifuge generate --noapi "warm analog pad" --output pad.SerumPreset
uv run centrifuge generate --noapi "punchy 808 bass" --output 808.SerumPreset
```

**How `--noapi` works:**

1. centrifuge spawns `claude -p "<task>" --output-format json --max-turns 30`
2. Claude Code delegates to two subagents defined in this repo:
   - [`.claude/agents/sound-design-expert.md`](.claude/agents/sound-design-expert.md) — translates the description into a synthesis recipe
   - [`.claude/agents/serum-preset-builder.md`](.claude/agents/serum-preset-builder.md) — uses the `centrifuge` CLI (`init`, `apply`, `show`, …) to construct the `.SerumPreset` step by step
3. The subagent reports the path; centrifuge verifies the file was written

You can also invoke the subagents directly **from inside a Claude Code session**:

```
> use the serum-preset-builder agent to make a deep wobble bass at /tmp/wob.SerumPreset
```

Claude Code will auto-delegate to the subagent based on its description.

**`--audio` works in `--noapi` mode:** the audio file is analysed with librosa in
the centrifuge process (spectral centroid, attack time, harmonicity, MFCCs, …)
and the resulting feature dict is injected as JSON into the subagent's prompt.
The sound-design-expert agent uses these features to refine the recipe.

```bash
uv run centrifuge generate --noapi --audio reference.wav "match this sound" --output matched.SerumPreset
```

**Limits:**
- Requires the `claude` CLI on PATH. If missing, centrifuge tells you where to install it.
- Cannot be combined with `--local` (pick one).
- Default timeout 600 s; override with `--noapi-timeout <seconds>`.

### `--local` mode (no cloud, no LLM)

Add `--local` to use the offline algorithmic pipeline. No model downloads, no network calls, fully deterministic — same description always produces the same preset.

```bash
uv run centrifuge generate --local "warm analog pad with slow attack" --output pad.SerumPreset
uv run centrifuge generate --local "punchy 808 bass" --output 808.SerumPreset
uv run centrifuge generate --local "wobbly acid bass" --output acid.SerumPreset
uv run centrifuge generate --local "bright plucky lead with chorus" --output pluck.SerumPreset
uv run centrifuge generate --local "huge reverb pad with sweep" --output sweep.SerumPreset
```

**How `--local` works:**

1. The description is tokenised against a curated vocabulary of ~120 keywords/phrases covering sound types (pad, bass, lead, pluck, arp, drum, stab, key, fx, 808, acid…), tonal qualities (warm, bright, dark, gritty, fat, lush…), dynamics (punchy, slow attack, long release…), filters (low pass, resonant, moog, formant…), effects (reverb, chorus, delay, distortion, hall…), and modulation (wobble, vibrato, tremolo…).
2. A sound-type keyword (e.g. `pad`, `bass`) selects a baseline recipe template; the remaining keywords deep-merge their modifiers on top.
3. The deterministic translator walks the recipe and writes the matching `kParam*` values to a fresh `.SerumPreset` based on a factory preset.

**Limits:**

- Coverage is bounded by the keyword vocabulary in [centrifuge/local/vocabulary.py](centrifuge/local/vocabulary.py). Add new entries to expand it.
- `--audio` is not supported in `--local` mode (rule-based audio matching is intentionally deferred to Phase 2).
- `--local-models` is reserved for a Phase 2 enhancement that adds optional Hugging Face models (zero-shot text classification, CLAP for audio matching). Not yet implemented.

---

## CLI Reference

All commands output JSON to stdout. Errors write `{"error": "..."}` to stderr and exit with code 1.

### `init` — create a new preset

```bash
uv run centrifuge init my_preset.SerumPreset [--base path/to/factory.SerumPreset] [--name "My Preset"] [--author "me"]
```

Creates a new preset based on a factory preset (defaults to `BA - Analog Classics 1.SerumPreset`). All components start from valid defaults.

### `show` — inspect a preset

```bash
uv run centrifuge show preset.SerumPreset
uv run centrifuge show preset.SerumPreset --section env
uv run centrifuge show preset.SerumPreset --section osc
uv run centrifuge show preset.SerumPreset --meta
```

Sections: `osc`, `env`, `lfo`, `filter`, `fx`, `mod`, `macro`, `global`

### `get` — read a param

```bash
uv run centrifuge get preset.SerumPreset Env0
uv run centrifuge get preset.SerumPreset Env0 kParamAttack
```

### `set` — write a single param

```bash
uv run centrifuge set preset.SerumPreset Env0 kParamAttack 0.5
uv run centrifuge set preset.SerumPreset VoiceFilter0 kParamType LadderMg
uv run centrifuge set preset.SerumPreset Oscillator0 kParamUnison 4
```

The value is parsed as a number when possible, otherwise kept as a string.

### `apply` — batch update

```bash
uv run centrifuge apply preset.SerumPreset changes.json
```

Where `changes.json` is:

```json
{
  "Oscillator0": { "kParamVolume": 0.9, "kParamUnison": 4, "kParamDetune": 0.2 },
  "Env0":        { "kParamAttack": 0.4, "kParamRelease": 1.5 },
  "VoiceFilter0": { "kParamEnable": 1.0, "kParamType": "LadderMg", "kParamFreq": 0.35 }
}
```

Also accepts an inline JSON string instead of a file path.

### `list-params` — parameter reference

```bash
uv run centrifuge list-params
uv run centrifuge list-params --component envelope
uv run centrifuge list-params --component filter
```

---

## Preset Structure Reference

Serum 2 presets are CBOR-encoded, zstd-compressed data with a JSON metadata header. After unpacking, each preset is a dict of named components.

### Components

| Component | Description |
|-----------|-------------|
| `Oscillator0` / `1` / `2` | Wavetable oscillators A, B, C |
| `Oscillator3` | Noise oscillator |
| `Oscillator4` | Sub oscillator |
| `WTOsc0` / `1` / `2` | Wavetable-specific params (nested inside Oscillator) |
| `Env0` | Amplitude envelope |
| `Env1` | Filter envelope |
| `Env2` / `3` | Auxiliary envelopes |
| `LFO0`–`LFO9` | LFOs |
| `VoiceFilter0` / `1` | Filters A and B |
| `FXRack0` / `1` / `2` | Effects chains (Main, Bus 1, Bus 2) |
| `ModSlot0`–`63` | Modulation routing slots |
| `Macro0`–`7` | Macro knobs |
| `Global0` | Global settings (poly, mono, portamento, master volume) |

### Key parameter ranges

| Parameter | Range | Notes |
|-----------|-------|-------|
| `kParamVolume` | 0–1 | Oscillator volume |
| `kParamPan` | –1 to 1 | Oscillator pan |
| `kParamOctave` | –4 to 4 | Integer |
| `kParamFine` | –100 to 100 | Cents |
| `kParamUnison` | 1–16 | Voice count |
| `kParamDetune` | 0–1 | Unison detune spread |
| `kParamAttack` | 0–10 | Seconds |
| `kParamDecay` | 0–10 | Seconds |
| `kParamSustain` | 0–1 | |
| `kParamRelease` | 0–10 | Seconds |
| `kParamCurve1/2/3` | 0–100 | Envelope curve shape; 50 = linear |
| `kParamFreq` (filter) | 0–1 | Normalised; 0.5 ≈ 1 kHz |
| `kParamReso` | 0–100 | Filter resonance |
| `kParamDrive` | 0–100 | Filter / FX drive |
| `kParamWet` (FX) | 0–1 | Effect wet mix |
| `kParamTablePos` | 0–2048 | Wavetable frame position |

### Filter types (common)

| Type | Character |
|------|-----------|
| `L6` `L12` `L18` `L24` | Low-pass (pole count) |
| `H6` `H12` `H24` | High-pass |
| `B12` `B24` | Bandpass |
| `LadderMg` | Moog-style warm low-pass |
| `LadderAcid` | TB-303 acid resonance |
| `LadderEMS` | EMS Synthi-style |
| `FormantONE` `FormantTWO` | Vowel formant filters |
| `FlangeN` `FlangeP` | Flange-style all-pass |
| `CombP` `CombN` | Comb filters |

### Effects (FXRack)

| Class | Type int | Key params |
|-------|----------|------------|
| `FXDistortion` | 0 | `kParamDrive`, `kParamMode`, `kParamWet` |
| `FXFlanger` | 1 | `kParamRate`, `kParamDepth`, `kParamWet` |
| `FXPhaser` | 2 | `kParamRate`, `kParamDepth`, `kParamWet` |
| `FXChorus` | 3 | `kParamRate`, `kParamDepth`, `kParamDelay`, `kParamWet` |
| `FXDelay` | 4 | `kParamTimeL`, `kParamTimeR`, `kParamFeedback`, `kParamWet` |
| `FXComp` | 5 | `kParamThresh`, `kParamRatio`, `kParamAttack`, `kParamWet` |
| `FXReverb` | 6 | `kParamSize`, `kParamPreDelay`, `kParamWidth`, `kParamWet` |
| `FXEQ` | 7 | `kParamFreq1/2`, `kParamGain1/2`, `kParamReso1/2` |
| `FXFilter` | 8 | `kParamFreq`, `kParamReso`, `kParamDrive`, `kParamWet` |
| `FXHyperD` | 9 | `kParamDetune`, `kParamUnison`, `kParamDimEWet`, `kParamWet` |

---

## Programmatic API

You can also use the Python API directly:

```python
from centrifuge.preset import PresetBuilder
from pathlib import Path

builder = PresetBuilder.from_path(Path("factory_base.SerumPreset"))

# Oscillator A — 4-voice unison saw
builder.set_oscillator(0, kParamVolume=0.9, kParamUnison=4, kParamDetune=0.15, kParamUnisonStereo=0.8)
builder.set_wavetable_osc(0, wavetable="S2 Tables/Default Shapes.wav", kParamTablePos=256.0)

# Amp envelope — slow pad shape
builder.set_envelope(0, kParamAttack=0.5, kParamDecay=0.3, kParamSustain=0.85, kParamRelease=1.5)

# LP filter
builder.set_filter(0, filter_type="LadderMg", kParamFreq=0.4, kParamReso=20.0)

# Reverb + chorus
builder.add_fx(0, "FXReverb", kParamWet=0.25, kParamSize=0.6, kParamWidth=0.8)
builder.add_fx(0, "FXChorus", kParamWet=0.15, kParamRate=0.5, kParamDepth=0.3)

builder.save(Path("warm_pad.SerumPreset"), name="Warm Pad", author="me", tags=["Pad", "Poly"])
```

---

## Running Tests

```bash
uv run pytest tests/ -v
```

Tests cover codec round-trips and PresetBuilder operations against the local factory presets.

---

## How It Works

```
User input (text description and/or WAV file)
         │
         ▼
  Sound Design Expert (Claude)
  ● Analyses description + audio features
  ● Outputs structured synthesis recipe JSON
         │
         ▼
  Serum 2 Expert (Claude + tool_use)
  ● Calls preset_init → preset_set → preset_add_fx → preset_show → preset_save
  ● Iterates until the preset is complete
         │
         ▼
  .SerumPreset file  →  load in Serum 2
```

The Serum 2 Expert has six tools: `preset_init`, `preset_set`, `preset_set_wt`, `preset_add_fx`, `preset_show`, and `preset_save`. It can call `preset_show` to verify its work before saving.
