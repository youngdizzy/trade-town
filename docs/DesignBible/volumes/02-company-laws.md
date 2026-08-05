# Volume 2 — Company Laws

**Status:** Outline. Not yet written. See [the master Table of
Contents](../../README.md).

Company Laws are permanent. No employee — human or AI — may violate
them, and every future feature must comply with them. Unlike Company
Principles (which belong to individual departments, see Volume 9's
per-chapter template), a Company Law applies company-wide.

## Working list of laws to formalize here

- Probability over Prediction
- Evidence over Confidence
- Capital Preservation before Profit
- Patience before Action
- Risk has Final Veto Authority
- Research Never Stops
- No Trade is Mandatory
- Every Decision Must Be Explainable
- Every Mistake Becomes Company Knowledge
- Protect the Company before Growing the Company

## Where the real content lives today

Several of these already exist as real, enforced code — not aspiration:

- "Risk has Final Veto Authority" — `backend/app/gatekeeper.py`'s Trade
  Gatekeeper, which can veto even the CEO's own call.
- "No Trade is Mandatory" — the Gatekeeper and Devil's Advocate systems;
  a proposal can always resolve to "wait."
- "Every Decision Must Be Explainable" — every `TradeDecision` carries a
  full `DecisionConfidence` factor breakdown, never a bare score.
- "Every Mistake Becomes Company Knowledge" — `backend/app/mistakes.py`'s
  Library of Mistakes and `backend/app/decision_vault.py`'s Decision
  Vault.
- "Capital Preservation before Profit" — `docs/DEVELOPMENT_RULES.md`'s
  Company Capital Priorities ordering (Capital Preservation ranks first).

When this volume is written, each law should cite the real code that
enforces it — a law with no enforcement is aspiration, not a law.
