"""Tests for the SerumPreset codec — pack/unpack round-trip."""

import json
import tempfile
from pathlib import Path

import pytest

from centrifuge._paths import factory_preset
from centrifuge.codec import pack, unpack

FACTORY_PRESET = factory_preset("Bass", "Acid", "BA - Standard Acid.SerumPreset")


@pytest.mark.skipif(not FACTORY_PRESET.exists(), reason="Factory presets not present")
def test_unpack_returns_metadata_and_data():
    result = unpack(FACTORY_PRESET)
    assert "metadata" in result
    assert "data" in result
    meta = result["metadata"]
    assert meta["fileType"] == "SerumPreset"
    assert meta["product"] == "Serum2"
    assert "presetName" in meta


@pytest.mark.skipif(not FACTORY_PRESET.exists(), reason="Factory presets not present")
def test_unpack_data_has_expected_components():
    data = unpack(FACTORY_PRESET)["data"]
    # All presets should have these component keys
    for key in ["Env0", "Env1", "LFO0", "FXRack0"]:
        assert key in data, f"Missing component: {key}"


@pytest.mark.skipif(not FACTORY_PRESET.exists(), reason="Factory presets not present")
def test_pack_roundtrip():
    """Unpack then repack — the result should unpack to the same data."""
    original = unpack(FACTORY_PRESET)

    with tempfile.NamedTemporaryFile(suffix=".SerumPreset", delete=False) as f:
        tmp_path = Path(f.name)

    try:
        pack(original, tmp_path)
        repacked = unpack(tmp_path)

        # Metadata should be equivalent (hash may differ due to re-serialisation)
        for key in ("fileType", "product", "presetName", "vendor"):
            assert original["metadata"][key] == repacked["metadata"][key]

        # Data should be identical
        orig_json = json.dumps(original["data"], sort_keys=True, default=str)
        rep_json = json.dumps(repacked["data"], sort_keys=True, default=str)
        assert orig_json == rep_json
    finally:
        tmp_path.unlink(missing_ok=True)


def test_pack_requires_metadata_and_data():
    with tempfile.NamedTemporaryFile(suffix=".SerumPreset", delete=False) as f:
        tmp_path = Path(f.name)
    try:
        with pytest.raises(Exception):
            pack({}, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
