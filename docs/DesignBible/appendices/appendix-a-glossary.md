# Appendix A — Glossary

**Status:** Outline. Not yet written. See [the master Table of
Contents](../README.md).

Every important company term gets exactly one definition here. When
written, each entry should cite the real schema/field that backs it —
never a term with no real data behind it.

## Terms to define first (already real, already load-bearing)

- Evidence Score — `backend/app/decision_vault.py`'s
  `compute_evidence_score()`.
- Confidence Score — `backend/app/confidence.py`'s `DecisionConfidence`.
- Expected Value — `backend/app/war_room.py`'s `ExpectedValueAnalysis`.
- Probability of Profit — `backend/app/whatif.py`'s
  `ScenarioResult.probabilityOfProfitPct`.
- Trade Quality / Decision Grade — `backend/app/executive.py`'s
  `compute_decision_grade()`.
- Risk Budget — `backend/app/risk_engine.py`'s `RiskLimits`.
- Capital Efficiency — `backend/app/portfolio_intelligence.py`'s
  `CapitalEfficiency`.
- Opportunity Cost — `backend/app/portfolio_intelligence.py`'s
  `_opportunity_cost()`.
- Institutional Memory — the Decision Vault's Similarity Engine and the
  Company Knowledge Graph, together.
- Company DNA — `backend/app/company_dna.py`.
- Portfolio Heat — `backend/app/portfolio_intelligence.py`'s
  `PortfolioHeat`.
- Decision Score — `backend/app/war_room.py`'s `DecisionScoreBreakdown`.
