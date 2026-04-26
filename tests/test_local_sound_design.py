"""Tests for the local algorithmic Sound Design Expert."""

from centrifuge.local.sound_design import (
    deep_merge,
    detect_template,
    generate_recipe,
    tokenise,
)


# ---------------------------------------------------------------------------
# tokenise
# ---------------------------------------------------------------------------

def test_tokenise_lowercases_and_splits():
    tokens = tokenise("Warm Pad")
    assert "warm" in tokens
    assert "pad" in tokens


def test_tokenise_strips_punctuation():
    tokens = tokenise("warm, analog pad!")
    assert "warm" in tokens
    assert "analog" in tokens
    assert "pad" in tokens


def test_tokenise_matches_multi_word_phrases():
    tokens = tokenise("a sound with slow attack and long release")
    assert "slow attack" in tokens
    assert "long release" in tokens


def test_tokenise_dedupes():
    tokens = tokenise("warm warm warm")
    assert tokens.count("warm") == 1


# ---------------------------------------------------------------------------
# detect_template
# ---------------------------------------------------------------------------

def test_detect_template_pad():
    assert detect_template(["warm", "pad"]) == "pad"


def test_detect_template_bass():
    assert detect_template(["punchy", "808"]) == "bass"


def test_detect_template_drum():
    assert detect_template(["snare", "hit"]) == "drum"


def test_detect_template_default_lead():
    # No type keyword → falls back to lead
    assert detect_template(["bright", "shiny"]) == "lead"


# ---------------------------------------------------------------------------
# deep_merge
# ---------------------------------------------------------------------------

def test_deep_merge_dicts():
    base = {"a": 1, "b": {"x": 1, "y": 2}}
    over = {"b": {"y": 99, "z": 3}, "c": 4}
    merged = deep_merge(base, over)
    assert merged == {"a": 1, "b": {"x": 1, "y": 99, "z": 3}, "c": 4}


def test_deep_merge_oscillators_by_slot():
    base = [{"slot": 0, "volume": 0.5, "unison": 1}]
    over = [{"slot": 0, "unison": 5, "detune": 0.2}]
    merged = deep_merge(base, over)
    assert len(merged) == 1
    assert merged[0] == {"slot": 0, "volume": 0.5, "unison": 5, "detune": 0.2}


def test_deep_merge_multiple_slots():
    base = [{"slot": 0, "volume": 0.5}]
    over = [{"slot": 1, "volume": 0.7}]
    merged = deep_merge(base, over)
    by_slot = {x["slot"]: x for x in merged}
    assert 0 in by_slot and 1 in by_slot


# ---------------------------------------------------------------------------
# generate_recipe
# ---------------------------------------------------------------------------

def test_warm_pad_recipe():
    r = generate_recipe("warm analog pad with slow attack")
    assert r["character"] == "pad"
    # warm sets a Moog-style filter
    assert r["filter_a"]["type"] == "LadderMg"
    # slow attack overrides the template default
    assert r["amp_envelope"]["attack_s"] >= 0.5
    # pad template includes reverb
    assert r["effects"]["reverb"]["wet"] > 0


def test_punchy_808_bass_recipe():
    r = generate_recipe("punchy 808 bass")
    assert r["character"] == "bass"
    assert r["amp_envelope"]["attack_s"] < 0.01
    # bass template enables sub
    assert r["sub"]["enabled"] is True


def test_acid_bass_recipe():
    r = generate_recipe("wobbly acid bass")
    assert r["character"] == "bass"
    assert r["filter_a"]["type"] == "LadderAcid"
    # wobble adds an LFO
    assert len(r["lfos"]) > 0
    assert r["lfos"][0]["destination"] == "filter cutoff"


def test_pluck_recipe():
    r = generate_recipe("bright plucky lead")
    # "pluck" / "plucky" should win over "lead" since plucky also resolves to pluck
    # but the test also exercises the case where multiple type keywords appear
    assert r["character"] in ("pluck", "lead")
    # bright lifts the cutoff
    assert r["filter_a"]["cutoff_normalized"] > 0.6


def test_huge_reverb_pad():
    r = generate_recipe("huge reverb pad")
    assert r["effects"]["reverb"]["wet"] > 0.5
    assert r["effects"]["reverb"]["size"] > 0.8


def test_empty_description_uses_default_template():
    r = generate_recipe("")
    # No tokens → default lead template, but without modifiers
    assert "amp_envelope" in r
    assert "filter_a" in r


def test_recipe_includes_notes():
    r = generate_recipe("warm pad")
    assert "notes" in r
    assert "warm" in r["notes"]
    assert "pad" in r["notes"]
