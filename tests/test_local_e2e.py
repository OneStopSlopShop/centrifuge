"""End-to-end tests for the local pipeline (description → .SerumPreset)."""

from pathlib import Path

import pytest

from centrifuge.codec import unpack
from centrifuge.local.orchestrator import generate_preset_local
from centrifuge.local.serum_expert import DEFAULT_BASE_FACTORY


@pytest.fixture(autouse=True)
def _skip_if_no_factory():
    if not DEFAULT_BASE_FACTORY.exists():
        pytest.skip("Default factory base preset not present")


def test_warm_pad_e2e(tmp_path):
    out = generate_preset_local("warm analog pad with slow attack", tmp_path / "pad.SerumPreset")
    data = unpack(out)
    # Pad → slow attack
    assert data["data"]["Env0"]["plainParams"]["kParamAttack"] >= 0.5
    # warm → LadderMg
    assert data["data"]["VoiceFilter0"]["plainParams"]["kParamType"] == "LadderMg"
    # Pad template includes reverb
    fx_classes = [list(fx.keys() - {"flex", "kUIParamMixOrGain", "type"})[0]
                  for fx in data["data"]["FXRack0"]["FX"]]
    assert "FXReverb" in fx_classes


def test_punchy_808_bass_e2e(tmp_path):
    out = generate_preset_local("punchy 808 bass", tmp_path / "808.SerumPreset")
    data = unpack(out)
    # Bass → fast attack
    assert data["data"]["Env0"]["plainParams"]["kParamAttack"] < 0.01
    # Bass template enables Sub
    sub = data["data"]["Oscillator4"]["plainParams"]
    assert sub.get("kParamEnable") == 1.0


def test_acid_bass_e2e(tmp_path):
    out = generate_preset_local("wobbly acid bass", tmp_path / "acid.SerumPreset")
    data = unpack(out)
    flt = data["data"]["VoiceFilter0"]["plainParams"]
    assert flt["kParamType"] == "LadderAcid"
    # Wobble adds an LFO
    lfo = data["data"]["LFO0"]["plainParams"]
    assert "kParamRate" in lfo


def test_huge_reverb_pad_e2e(tmp_path):
    out = generate_preset_local("huge reverb pad", tmp_path / "spacey.SerumPreset")
    data = unpack(out)
    fx = data["data"]["FXRack0"]["FX"]
    reverb = next((f for f in fx if "FXReverb" in f), None)
    assert reverb is not None
    assert reverb["FXReverb"]["plainParams"]["kParamWet"] > 0.5


def test_bright_pluck_chorus_e2e(tmp_path):
    out = generate_preset_local("bright plucky lead with chorus", tmp_path / "pluck.SerumPreset")
    data = unpack(out)
    flt = data["data"]["VoiceFilter0"]["plainParams"]
    assert flt["kParamFreq"] > 0.6
    fx_classes = [list(fx.keys() - {"flex", "kUIParamMixOrGain", "type"})[0]
                  for fx in data["data"]["FXRack0"]["FX"]]
    assert "FXChorus" in fx_classes
