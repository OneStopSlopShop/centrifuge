"""Tests for the local Serum 2 Expert (deterministic recipe → preset)."""

from pathlib import Path

import pytest

from centrifuge.codec import unpack
from centrifuge.local.serum_expert import DEFAULT_BASE_FACTORY, build_preset


@pytest.fixture(autouse=True)
def _skip_if_no_factory():
    if not DEFAULT_BASE_FACTORY.exists():
        pytest.skip("Default factory base preset not present")


def test_build_minimal_recipe(tmp_path):
    recipe = {
        "character": "test",
        "oscillators": [{"slot": 0, "volume": 0.7, "octave": -1}],
        "amp_envelope": {"attack_s": 0.005, "release_s": 0.5},
        "filter_a": {"enabled": True, "type": "L24", "cutoff_normalized": 0.5,
                     "resonance": 20.0},
    }
    out = tmp_path / "minimal.SerumPreset"
    build_preset(recipe, out)
    assert out.exists()

    data = unpack(out)["data"]
    osc0 = data["Oscillator0"]["plainParams"]
    assert osc0["kParamVolume"] == 0.7
    assert osc0["kParamOctave"] == -1.0

    env0 = data["Env0"]["plainParams"]
    assert env0["kParamAttack"] == 0.005
    assert env0["kParamRelease"] == 0.5

    flt = data["VoiceFilter0"]["plainParams"]
    assert flt["kParamType"] == "L24"
    assert flt["kParamFreq"] == 0.5
    assert flt["kParamReso"] == 20.0


def test_build_recipe_with_effects(tmp_path):
    recipe = {
        "character": "wet test",
        "oscillators": [{"slot": 0, "volume": 0.8}],
        "amp_envelope": {"attack_s": 0.01},
        "effects": {
            "reverb": {"wet": 0.4, "size": 0.7},
            "chorus": {"wet": 0.25, "rate": 0.5, "depth": 0.5},
            "delay": {"wet": 0.3, "time_l": 0.375, "time_r": 0.5,
                      "feedback": 0.4, "beat_sync": True},
        },
    }
    out = tmp_path / "fx.SerumPreset"
    build_preset(recipe, out)

    fx_list = unpack(out)["data"]["FXRack0"]["FX"]
    classes = [list(fx.keys() - {"flex", "kUIParamMixOrGain", "type"})[0] for fx in fx_list]
    assert "FXReverb" in classes
    assert "FXChorus" in classes
    assert "FXDelay" in classes


def test_build_recipe_with_lfo(tmp_path):
    recipe = {
        "character": "modulated",
        "oscillators": [{"slot": 0, "volume": 0.8}],
        "amp_envelope": {"attack_s": 0.01},
        "lfos": [{"slot": 0, "rate_hz": 4.0, "beat_sync": True, "smooth": 0.3,
                  "destination": "filter cutoff"}],
    }
    out = tmp_path / "lfo.SerumPreset"
    build_preset(recipe, out)

    lfo0 = unpack(out)["data"]["LFO0"]["plainParams"]
    assert lfo0["kParamRate"] == 4.0
    assert lfo0["kParamBeatSync"] == 1.0
    assert lfo0["kParamSmooth"] == 0.3


def test_metadata_set_correctly(tmp_path):
    recipe = {
        "character": "warm pad",
        "oscillators": [{"slot": 0, "unison": 5}],
        "amp_envelope": {"attack_s": 0.4},
    }
    out = tmp_path / "tagged.SerumPreset"
    build_preset(recipe, out)

    meta = unpack(out)["metadata"]
    assert meta["presetName"] == "tagged"
    assert meta["presetAuthor"] == "centrifuge --local"
    assert "Poly" in meta["tags"]


def test_disabled_filter_is_skipped(tmp_path):
    """If filter_a.enabled is False, the recipe should not enable the filter."""
    recipe = {
        "character": "no filter",
        "oscillators": [{"slot": 0, "volume": 0.8}],
        "amp_envelope": {"attack_s": 0.01},
        "filter_a": {"enabled": False, "type": "L24", "cutoff_normalized": 0.1},
    }
    out = tmp_path / "nofilt.SerumPreset"
    build_preset(recipe, out)
    flt = unpack(out)["data"]["VoiceFilter0"]["plainParams"]
    # Should retain the base preset's setting (not 0.1)
    assert flt.get("kParamFreq") != 0.1
