"""Tests for PresetBuilder."""

import tempfile
from pathlib import Path

import pytest

from centrifuge._paths import factory_preset
from centrifuge.codec import unpack
from centrifuge.preset import PresetBuilder

FACTORY_PRESET = factory_preset("Bass", "Acid", "BA - Standard Acid.SerumPreset")


@pytest.fixture
def builder():
    pytest.importorskip("cbor2")
    if not FACTORY_PRESET.exists():
        pytest.skip("Factory presets not present")
    return PresetBuilder.from_path(FACTORY_PRESET)


def test_set_component_creates_params(builder):
    builder.set_component("Env0", {"kParamAttack": 0.5})
    comp = builder.get_component("Env0")
    assert comp["plainParams"]["kParamAttack"] == 0.5


def test_set_component_merges(builder):
    builder.set_component("Env0", {"kParamAttack": 0.1})
    builder.set_component("Env0", {"kParamRelease": 1.0})
    comp = builder.get_component("Env0")
    assert comp["plainParams"]["kParamAttack"] == 0.1
    assert comp["plainParams"]["kParamRelease"] == 1.0


def test_set_oscillator(builder):
    builder.set_oscillator(0, kParamVolume=0.8, kParamUnison=4)
    comp = builder.get_component("Oscillator0")
    assert comp["plainParams"]["kParamVolume"] == 0.8
    assert comp["plainParams"]["kParamUnison"] == 4


def test_set_envelope(builder):
    builder.set_envelope(0, kParamAttack=0.3, kParamSustain=0.7, kParamRelease=1.5)
    comp = builder.get_component("Env0")
    pp = comp["plainParams"]
    assert pp["kParamAttack"] == 0.3
    assert pp["kParamSustain"] == 0.7
    assert pp["kParamRelease"] == 1.5


def test_set_filter(builder):
    builder.set_filter(0, filter_type="LadderMg", kParamFreq=0.4, kParamReso=30.0)
    comp = builder.get_component("VoiceFilter0")
    pp = comp["plainParams"]
    assert pp["kParamType"] == "LadderMg"
    assert pp["kParamFreq"] == 0.4
    assert pp["kParamEnable"] == 1.0


def test_add_fx(builder):
    builder.clear_fx(0)
    builder.add_fx(0, "FXReverb", kParamWet=0.3, kParamSize=0.6)
    rack = builder.get_component("FXRack0")
    assert len(rack["FX"]) == 1
    fx = rack["FX"][0]
    assert fx["type"] == 6  # FXReverb
    assert "FXReverb" in fx
    assert fx["FXReverb"]["plainParams"]["kParamWet"] == 0.3


def test_add_fx_invalid_class(builder):
    with pytest.raises(ValueError, match="Unknown FX class"):
        builder.add_fx(0, "FXSuperDuper")


def test_set_macro(builder):
    builder.set_macro(0, 75.0, name="FILTER")
    macro = builder.get_component("Macro0")
    assert macro["plainParams"]["kParamValue"] == 75.0
    assert macro["name"] == "FILTER"


def test_save_roundtrip(builder, tmp_path):
    builder.set_envelope(0, kParamAttack=0.25)
    out = tmp_path / "test.SerumPreset"
    builder.save(out, name="Test Preset", author="test")
    loaded = unpack(out)
    assert loaded["metadata"]["presetName"] == "Test Preset"
    assert loaded["metadata"]["presetAuthor"] == "test"
    pp = loaded["data"]["Env0"]["plainParams"]
    assert pp["kParamAttack"] == 0.25
