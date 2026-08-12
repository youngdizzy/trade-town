"""Probability-first language audit — Trading Psychology & Discipline,
Piece E. This codebase has no LLM anywhere (confirmed: no such
dependency in requirements.txt) — every player-facing string is
deterministic f-string/template generation, never freeform prose. A
manual audit of every real text-generation module (the Decision
Confidence Engine, the Discipline Chamber, the Library of Mistakes/
Successes, the AI Debate, Academy lessons, and every other player-facing
generator) found zero genuine violations of probability-first framing —
`app/confidence.py`'s own module docstring already states the design
principle this codebase was built under: "Never predicts whether a
trade will win. It scores the quality of the evidence behind the
current setup." The only "certainty" language anywhere in generated
text is either (a) explicit negation — "an estimate, not a guarantee"
(`app/calendar.py`), "a probable zone is not a guarantee price ever
reaches it" (`app/market_debate.py`) — or (b) intentional wrong-answer
quiz distractors in `app/education.py`/`app/foundational_mentors.py`
that exist specifically to be marked incorrect, teaching against
overconfidence rather than modeling it.

This module turns that one-time audit finding into a permanent,
enforced guarantee rather than a report that goes stale. `BANNED_
CERTAINTY_PHRASES` bans phrase-level assertions of certainty
("is guaranteed to", "sure thing", "always wins") — never bare words
like "guarantee" — specifically because this codebase's own correct
usage already includes the word inside negated, hedged sentences
("not a guarantee"); a bare-word ban would flag exactly the
probability-first language this module exists to protect.
`find_certainty_violations()` and `audit_model()` are the reusable
checkers `tests/test_probability_language_audit.py` runs against real
generated output from `app/discipline.py`, `app/mistakes.py`,
`app/successes.py`, and `app/debate.py` — the codebase's own
regression guard against a future template drifting into
certainty-of-outcome language.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel

# Phrase-level, not word-level — see the module docstring for why a bare
# "guarantee"/"certain"/"sure" ban would false-positive on this
# codebase's own correct, hedged usage ("not a guarantee", "no one is
# certain").
BANNED_CERTAINTY_PHRASES: tuple[str, ...] = (
    "is guaranteed to",
    "guaranteed profit",
    "guaranteed win",
    "guaranteed to win",
    "guaranteed to happen",
    "guaranteed return",
    "sure thing",
    "surefire",
    "sure-fire",
    "slam dunk",
    "can't lose",
    "cannot lose",
    "can't fail",
    "cannot fail",
    "can't miss",
    "cannot miss",
    "never loses",
    "never fails",
    "always wins",
    "always profitable",
    "100% certain",
    "100% sure",
    "no doubt it will",
    "without a doubt it will",
    "will definitely",
    "definitely going to",
    "impossible to lose",
    "risk-free",
)


def find_certainty_violations(text: str) -> list[str]:
    """Returns every banned phrase (if any) present in `text`, case-
    insensitive. Empty list means the text is clean."""
    lowered = text.lower()
    return [phrase for phrase in BANNED_CERTAINTY_PHRASES if phrase in lowered]


def _iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _iter_strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _iter_strings(v)


def audit_model(model: BaseModel) -> dict[str, list[str]]:
    """Walks every string field (including nested models/lists) of a
    real generated schema object and reports any that contain banned
    certainty language. Returns `{offending_text: [banned_phrases]}` —
    empty dict means the whole object is clean. Generic over any
    pydantic model so the same function audits a DisciplineReview, a
    CaseStudy, a Debate, or anything else this codebase generates,
    without per-type field enumeration."""
    violations: dict[str, list[str]] = {}
    for text in _iter_strings(model.model_dump()):
        hits = find_certainty_violations(text)
        if hits:
            violations[text] = hits
    return violations
