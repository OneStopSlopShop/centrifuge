"""
Local Sound Design Expert — algorithmic recipe generator.

No LLM, no model downloads.  Tokenises a description, picks a sound-type
template, then deep-merges keyword modifiers from VOCAB on top.

Output recipe matches the schema in centrifuge/agents/sound_design.py so the
downstream Serum 2 translator works the same way for cloud and local modes.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from centrifuge.local.templates import DEFAULT_TEMPLATE, TEMPLATES
from centrifuge.local.vocabulary import (
    MULTI_WORD_PHRASES,
    SOUND_TYPE_KEYWORDS,
    VOCAB,
)

_PUNCT_RE = re.compile(r"[^\w\s]")


def tokenise(description: str) -> list[str]:
    """
    Lowercase the description, strip punctuation, then extract tokens.
    Multi-word phrases from VOCAB and SOUND_TYPE_KEYWORDS are matched first
    so they're treated as a single token (e.g. "slow attack" stays together).
    Single words are emitted afterwards in original order.
    """
    text = _PUNCT_RE.sub(" ", description.lower())
    text = re.sub(r"\s+", " ", text).strip()

    tokens: list[str] = []

    # Greedy multi-word matching (longest first)
    remaining = text
    matched_spans: list[tuple[int, int, str]] = []
    for phrase in MULTI_WORD_PHRASES:
        for m in re.finditer(rf"\b{re.escape(phrase)}\b", remaining):
            # Skip if span overlaps an already-matched span
            if any(m.start() < e and m.end() > s for s, e, _ in matched_spans):
                continue
            matched_spans.append((m.start(), m.end(), phrase))

    matched_spans.sort()
    for _, _, phrase in matched_spans:
        tokens.append(phrase)

    # Now grab single words that aren't covered by the matched spans
    cursor = 0
    chunks: list[str] = []
    for s, e, _ in matched_spans:
        if cursor < s:
            chunks.append(remaining[cursor:s])
        cursor = e
    if cursor < len(remaining):
        chunks.append(remaining[cursor:])

    for chunk in chunks:
        for word in chunk.split():
            tokens.append(word)

    # Preserve insertion order, dedupe
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def detect_template(tokens: list[str]) -> str:
    """Pick the sound-type template by scanning tokens for type keywords."""
    for token in tokens:
        if token in SOUND_TYPE_KEYWORDS:
            return SOUND_TYPE_KEYWORDS[token]
    return DEFAULT_TEMPLATE


def deep_merge(base: Any, override: Any) -> Any:
    """
    Merge `override` into `base`.

    - dicts: merged key by key (override wins on scalars)
    - lists of objects with a "slot" key: merged by slot id
    - lists of plain values: override replaces base
    - everything else: override wins
    """
    if isinstance(base, dict) and isinstance(override, dict):
        out = dict(base)
        for k, v in override.items():
            if k in out:
                out[k] = deep_merge(out[k], v)
            else:
                out[k] = copy.deepcopy(v)
        return out

    if isinstance(base, list) and isinstance(override, list):
        # Merge lists of slot-keyed dicts
        if base and override and \
           all(isinstance(x, dict) and "slot" in x for x in base + override):
            by_slot: dict[int, dict] = {x["slot"]: dict(x) for x in base}
            for item in override:
                slot = item["slot"]
                if slot in by_slot:
                    by_slot[slot] = deep_merge(by_slot[slot], item)
                else:
                    by_slot[slot] = copy.deepcopy(item)
            return [by_slot[s] for s in sorted(by_slot)]
        # Otherwise override wins
        return copy.deepcopy(override)

    return copy.deepcopy(override)


def generate_recipe(description: str) -> dict:
    """Produce a synthesis recipe from a text description."""
    tokens = tokenise(description)
    template_name = detect_template(tokens)

    recipe = TEMPLATES[template_name]()

    matched: list[str] = []
    for token in tokens:
        if token in VOCAB:
            recipe = deep_merge(recipe, VOCAB[token])
            matched.append(token)

    recipe["notes"] = (
        f"template={template_name}; tokens={tokens}; matched={matched}"
    )
    if "character" not in recipe or not recipe["character"]:
        recipe["character"] = template_name
    return recipe
