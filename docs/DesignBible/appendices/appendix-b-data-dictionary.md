# Appendix B — Data Dictionary

**Status:** Outline. Not yet written. See [the master Table of
Contents](../README.md).

Every important object gets one authoritative entry here, pointing at
its real schema in `backend/app/schemas.py` (the single source of truth
for every wire-format object in this codebase — `frontend/src/types.ts`
mirrors it, never the other way around).

## Objects to document first

- Trade — `PaperTrade`
- Position — `PaperPosition`
- Portfolio — `PaperPortfolio`
- Employee — `AgentProfile` / `AgentState`
- Department — `ExecutiveDepartmentRole`
- Research Project — `ResearchItem` / `AcademyProject`
- Simulation — `WhatIfSimulation` / `ScenarioResult`
- Broker — `PaperBroker` / `PaperOrder`
- Risk Report — `RiskWarning` / `RiskLimits`
- News Event — `NewsItem`
- Knowledge Entry — `AgentKnowledgeState` / the Knowledge Graph's node
  types
- Company Report — `CoachReport` / `ExecutiveReview` / `ReflectionSession`
- Decision Vault Entry — `DecisionVaultEntry`
- War Room Session — `WarRoomSession`
- Portfolio Intelligence — `PortfolioIntelligence`
