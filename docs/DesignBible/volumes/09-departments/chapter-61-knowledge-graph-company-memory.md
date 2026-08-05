# Chapter 61 — Institutional Knowledge Graph & Company Memory Engine

**Status:** Target design. Not yet implemented. See [Volume 9's chapter
template](README.md) for what every section below must contain, and the
Implementation Notes at the bottom of this chapter for exactly what's
real today versus new here.

## Executive Summary

"TradeTown should never repeat mistakes because it forgot them." This
codebase already has an unusually large amount of real institutional
memory — it just isn't unified. **Researched first, and the finding is
the opposite of Chapters 59/60's own gaps**: almost every capability
this brief describes already exists as a real, separate system, several
of them for a long time. The genuine job for this chapter is honest
consolidation and two specific, real extensions — not a from-scratch
build.

## Mission

One clear purpose: give every already-real piece of company knowledge —
trades, research, decisions, mistakes, successes, simulations — a
permanent home, real connections to each other, and a way for any future
decision to honestly ask "have we seen this before?"

## Philosophy

Knowledge compounds, but only if it's kept. This codebase's own existing
convention already lives this principle: `MAX_MEMORY_RECORDS`,
`MAX_DECISION_VAULT_ENTRIES`, and every other capped list in this
codebase evict the *oldest* entry, never a *validated* one — nothing
here is deleted for convenience. "Nothing is wasted" is checked against
real code, not aspiration: a losing trade already becomes a `CaseStudy`
(`app/mistakes.py`) rather than being silently dropped; a winning one
already becomes the mirror-image `CaseStudy` (`app/successes.py`).

## Responsibilities

**Owns:** unifying the real knowledge stores below into one browsable
graph and one honest quality/retention model; extending the existing
Knowledge Graph's node types to cover the brief's own worked example.

**Does NOT own:** Trade Execution, Risk Approval, Portfolio Management,
Broker Communication — unchanged, matching every other chapter in this
volume.

## Ownership

Every one of these already exists and is already real:

| System | Module | What it really does |
|---|---|---|
| Company Memory | `app/memory.py` | `record()`/`search()` over `MemoryRecord`, 20 real `MemoryCategory` values (research, meeting, whiteboard, event, discussion, discovery, lesson, mistake, strategy, coach_review, simulation, paper_trade, alert, vote, decision, order, academy, mentorship, ...). Capped at `MAX_MEMORY_RECORDS = 200`. |
| Knowledge Base derivation | `app/knowledge.py` | Turns a closed `PaperTrade` into a distilled "lesson" or "mistake" `MemoryRecord` (v0.5 Feature 9) — pure text derivation; `app/scribe.py` remains the one real writer. |
| Knowledge Graph | `app/knowledge_graph.py` | A real node-edge graph, computed fresh per request (`GET /api/knowledge-graph`, `app/routers/knowledge_graph.py`) — never a second persisted, driftable copy. Today's nodes: `agent`, `branch`, `research`, `academy_project`, `executive_review`, `coach_report`, `hall_of_fame`. Today's edges: `researched`, `completed`, `has_branch`, `builds_on`, `featured_in`, `ranked_top_agent`, `achieved` — every edge traces to one real, checkable shared attribute (e.g., two research items sharing a real `category`), never an invented connection. |
| Decision Vault | `app/decision_vault.py` | A permanent `DecisionVaultEntry` per closed trade, joining Decision Grade, Discipline/Patience score, Evidence/Confidence, linked mistake `CaseStudy`, `PaperTrade.lessonsLearned`, Executive notes, and the Company DNA change it triggered — into one addressable record. Capped at `MAX_DECISION_VAULT_ENTRIES = 200`. |
| Cross-Reference / Similarity Engine | `app/decision_vault.py`'s `find_similar_vault_entries()` | Real, rule-based bucket matching over closed trades — three tiers (symbol+regime+tier, then regime+tier, then tier alone), falling back to a broader tier only when the narrower one has fewer than `MIN_SIMILAR_MATCHES = 3` real matches. `summarize_similarity()` returns real win rate, avg/worst P&L, best/worst regime, and a Mistake Prevention warning when one mistake category accounts for ≥ `MISTAKE_WARNING_SHARE = 0.3` of the matched trades. |
| Trade Report Card | `app/decision_vault.py`'s `compute_trade_report_card()` | Pure relabeling of a `DecisionVaultEntry`'s own fields into `wouldTakeAgain` (a real, checkable rule: cleared the B- decision-grade bar AND no mistake case study filed) and a plain-text recommendation. |
| Pattern Recognition — mistakes | `app/mistakes.py` | Six real, checkable process-failure categories (overconfidence, incomplete research, unchallenged assumptions, acted too quickly, ...), filed only when a closed loss's own `DisciplineReview` shows the specific real gap. |
| Pattern Recognition — successes | `app/successes.py` | The mirror image: three real process-strength categories for closed wins. |
| Institutional Learning | `app/wisdom.py` | Real weekly/monthly `ReflectionSession` + Company Wisdom Score, built entirely from already-real signals (`DisciplineReview`, `CaseStudy`, `ReasoningChallenge`, `ResearchItem`, `GatekeeperRejection`, `PaperTrade`, `MemoryRecord`). |
| Company DNA (behavioral learning) | `app/company_dna.py` | Five real behavioral traits derived from historical decision/trade record, updated via `nudge_legacy()` — the real "should company rules/character change?" loop this brief's Learning System section asks for. |
| Frontend | `KnowledgeGraphView.tsx`, `KnowledgeBasePanel.tsx` | Already shipped — a real node-edge network viewer with working filters/search, and a Company Knowledge Library view, both in the Command Center's KNOWLEDGE tab. |

## Inputs

Every input the brief names is already real and already flows into one
of the systems above: trades (`PaperTrade`/`DecisionVaultEntry`),
research (`ResearchItem`), simulations (`SimulationResult`), risk
reports (`RiskWarning`), CEO decisions (`CeoDecisionRecord`), company
meetings (`MeetingMinutes`/`ExecutiveMeetingLogEntry`), rejected trades
(`GatekeeperRejection`, `OpportunityRejection`), and Company DNA updates
(`nudge_legacy()`). **Not yet a real input:** Capital Rotation Reports —
Chapter 60 (Portfolio Rebalancing) is itself still target-design, not
implemented, so there is nothing real to ingest from it yet.

## Knowledge Ingestion Workflow

The brief's own workflow — Categorize → Tag → Connect → Store →
Cross-Reference → Learn → Make Available Company-Wide — is, in this
order, already the real code path for a closed trade:
`app/journal.py` stamps the trade → `app/mistakes.py`/`successes.py`
categorize it into a `CaseStudy` → `app/decision_vault.py` builds and
tags the `DecisionVaultEntry` → `record_vault_entry()` stores it →
`find_similar_vault_entries()` cross-references it against history →
`app/wisdom.py`/`app/company_dna.py` learn from it → the Command
Center's VAULT/DISCIPLINE/KNOWLEDGE tabs make it available. What's
**not** yet wired into this exact pipeline: research, simulations, and
strategies don't flow through an equivalent categorize-tag-connect-store
sequence — they're each stored in their own real place
(`app/research.py`, `app/simulation.py`, `app/sandbox.py`) but never
joined the way a closed trade is.

## Knowledge Graph

**The real, closeable gap.** The brief's own worked example — NVDA → AI
Sector → Technology → Strong Earnings → Previous Trade → Historical
Success → Current Opportunity → Risk Factors → Employee Research →
Simulation Results — names exactly the node types today's
`app/knowledge_graph.py` does **not** yet have: trades, decisions, case
studies (mistakes and successes), strategies, and simulation results are
none of them graph nodes today, only `agent`/`branch`/`research`/
`academy_project`/`executive_review`/`coach_report`/`hall_of_fame` are.
Every one of the missing node types is already a real, well-defined
object (`DecisionVaultEntry`, `CaseStudy`, `Strategy`,
`SimulationResult`) — extending `build_knowledge_graph()` to include them,
connected by real shared attributes it already has a precedent for
(same `symbol`, same `category`, `caseStudyId` already stored directly on
`DecisionVaultEntry`), is genuinely new, additive work, not a rebuild.

## Company Memory

Already fully real (`app/memory.py`, above) — this chapter reuses it as
the underlying store, rather than inventing a second one under a new
name.

## Pattern Recognition

Already fully real for the trade/decision population
(`app/mistakes.py`, `app/successes.py`, `app/wisdom.py`'s
most-common-category read, above). **Deferred, not built here** (see
`app/decision_vault.py`'s own module docstring, which already flagged
this): a real frequency/*trend* signal for recurring mistakes (today's
wisdom.py reports only a plain most-common count, not whether a category
is getting more or less frequent over time) — a genuine, scoped future
slice, not fabricated here.

## Knowledge Tagging

Already real and pervasive: `MemoryCategory` (20 values), `CaseStudyCategory`
(9 values across mistakes/successes), `ConfidenceTier`,
`MarketIntelligenceRegime`, `ResearchCategory` — every entry in every
system above already carries real, structured tags, not free text.

## Cross-Reference Engine

Already fully real **for closed trades specifically**
(`find_similar_vault_entries()`, above). **Not yet real** for the
brief's broader ask — "Related research," "Past simulations,"
"Comparable market environments" as an automatic search triggered when
*analyzing a new (not-yet-closed) trade* has no equivalent today; the
Similarity Engine only ever looks backward over already-closed trades in
the Vault, never forward at proposal time. Extending the search to run
at proposal-creation time (reusing the exact same three-tier bucket
logic) is a real, scoped candidate for a future implementation slice.

## Knowledge Quality Score

**Not built.** No `MemoryRecord`, `KnowledgeNode`, or `DecisionVaultEntry`
carries anything like the brief's Accuracy/Usefulness/Validation/
Historical Success/Relevance/Frequency-of-Use composite today. A
"quality score" over already-real signals (a `DecisionVaultEntry`'s own
real win rate when matched by the Similarity Engine could stand in for
"Historical Success"; how often a given entry appears in a
`SimilarTradesSummary.examples` list could stand in for "Frequency of
Use") is a real, honest design direction — not invented here, since it
would need its own scoping pass the way Chapter 59's Priority Score did.

## CEO Controls

| Control | Status |
|---|---|
| Knowledge Retention Rules | **Not built** — `MAX_MEMORY_RECORDS`/`MAX_DECISION_VAULT_ENTRIES` are fixed constants (200 each), not CEO-configurable. |
| Archive Policies | **Not built** — evicted entries are simply dropped, never archived to a second, longer-term store. |
| Learning Sensitivity | **Not built** — `app/wisdom.py`'s reflection cadence (weekly/monthly) is fixed. |
| Memory Weighting | **Not built** — no signal is weighted differently by recency or importance anywhere in Company Memory. |
| Historical Search Depth | **Not built** — the Similarity Engine always searches the full capped Vault; no configurable lookback window. |
| Pattern Detection Sensitivity | **Not built** — `MIN_SIMILAR_MATCHES`/`MISTAKE_WARNING_SHARE` are fixed constants. |
| Knowledge Validation Rules | **Not built** — no entry is ever marked "validated" vs. "unvalidated." |
| Research Priority | **Overlaps** with `app/research.py`'s existing `ResearchItem.priority` field — already real, not a new control this chapter would add. |

Every "Not built" row above names the exact same kind of fixed constant
Chapters 57–59 already promoted to real `RiskLimits` fields — the same
closeable pattern, not yet applied here.

## KPIs

Real and computable once the graph extension above exists: Knowledge
Growth (`len(memory)`/`len(vault)` over time, already trivially real);
Pattern Recognition Accuracy (the Similarity Engine's own real win-rate
read, already computed); Institutional Learning Rate (Company Wisdom
Score's own real trend, already computed). **Not honestly computable
without fabrication:** "Duplicate Knowledge Reduction" (no dedup logic
exists to measure a reduction against), "Knowledge Retrieval Speed" (a
backend performance metric, not a company-intelligence one), "Research
Reuse Rate" (nothing today tracks whether a piece of research was ever
actually consulted a second time).

## Reports

Already real, thin reads over the systems above, not fabricated: the
VAULT tab's own view is already a Historical Similarity Report; the
DISCIPLINE tab's Library of Mistakes is already a Repeated Mistakes
Report; `app/wisdom.py`'s `ReflectionSession` is already an Institutional
Learning Report. **Not yet built:** a single unified "Executive
Knowledge Summary" pulling all of the above into one view — every
underlying number is real, only the unified page is missing.

## Learning System

Already real, per closed trade: `app/wisdom.py`'s reflection questions
already ask "what happened, why, what can be learned" against real
signals; `app/company_dna.py`'s `nudge_legacy()` already answers "should
company rules change?" with a real trait nudge. What's not yet
real: an equivalent learning loop for research and simulations that
never became a trade at all — today's learning system only fires off
the trade-closing pipeline.

## Safety Systems

Already real: nothing here overwrites a capped-list entry in place
(every list only ever appends and evicts the oldest); `CaseStudy`/
`DecisionVaultEntry`/`MemoryRecord` are immutable once created (no
`update` mutation exists on any of them). **Not built:** explicit
CEO-approval-gated deletion (nothing is ever deleted at all today, so
there's no delete path to gate); a version history for a modified entry
(nothing is ever modified, so nothing needs versioning yet — a
consequence of the current append-only design, not a gap in it).

## Department Cooperation

**Receives from:** every department, already true today — every module
in the Ownership table above already reads from Research, Risk
(Sentinel/Guardian warnings), the Executive pipeline, and Portfolio
Intelligence. **Provides knowledge to:** Market Intelligence (regime
labels already flow into `DecisionVaultEntry.marketRegime`), the
Opportunity Gatekeeper and Capital Priority Engine (Chapters 58/59,
which already read `DecisionScoreBreakdown`/`ExpectedValueAnalysis` —
the same real signals this chapter's Vault also stores), Position Sizing
(Chapter 57). **Not yet provided:** a direct API from this chapter's
Knowledge Graph *into* those engines' own decision logic — today they
each read their own upstream signals directly, not through a Knowledge
Graph query.

## Dependencies

Chapter 54 (Decision Memory System — real backend + frontend shipped,
chapter itself not yet written, per this volume's own README), Chapter
55 (Executive Decision Simulator — same), Chapter 56 (Enterprise
Portfolio Intelligence — same), Chapter 57 (Position Sizing), Chapter 58
(Opportunity Gatekeeper), Chapter 59 (Capital Priority Engine — fully
implemented). Chapter 60 (Portfolio Rebalancing) is cited by the brief
but is itself still target-design only. **A note on the brief's other
named dependency:** "Chapter 53 — Probabilistic Trading Philosophy" does
not exist anywhere in this codebase or Design Bible under that number or
title — the same non-existent reference already checked and flagged in
Chapters 58 and 59's own Dependencies sections.

## Connected Features

Chapter 62 (Innovation Lab & Continuous Improvement Engine, the natural
next chapter — its own "Knowledge Integration" section explicitly
depends on this chapter's Knowledge Graph existing first). Chapter 60
(Portfolio Rebalancing) would become a real new input source once
implemented.

## Future Expansion

Vector Search, Semantic Search, AI Memory Compression, and Natural
Language Queries all require a real embedding/LLM dependency this
codebase does not have (confirmed directly — no `openai`/`anthropic`/
equivalent HTTP client dependency exists in `backend/requirements.txt`,
the same check `app/decision_vault.py`'s own module docstring already
performed and documented). Building a fake "understands your question"
layer out of keyword matching would be exactly the fabrication this
project's discipline exists to prevent — the honest substitute, already
real, is structured filters (symbol/regime/tier/category/date range).

## Company Principle

Trades create experience. Experience creates knowledge. TradeTown's
greatest competitive advantage is not faster trading — it is remembering
more than everyone else, and never repeating a mistake it already has a
real, checkable record of.

## Implementation Notes

**What's real today:** the overwhelming majority of this chapter —
Company Memory (`app/memory.py`), the Decision Vault, Trade Report Card,
and Similarity Engine (`app/decision_vault.py`), Pattern Recognition for
both mistakes and successes (`app/mistakes.py`, `app/successes.py`),
Institutional Learning (`app/wisdom.py`), Company DNA's behavioral
learning loop (`app/company_dna.py`), and a real, already-shipped
Knowledge Graph with working frontend (`app/knowledge_graph.py`,
`KnowledgeGraphView.tsx`, `KnowledgeBasePanel.tsx`). This is the
opposite research outcome from most prior chapters in this volume: the
brief describes a system that is already, in large part, built.

**What's genuinely new in this chapter:** extending the Knowledge
Graph's node/edge types to include trades, decisions, case studies, and
strategies — the exact gap the brief's own worked example names, and the
single largest real, closeable piece of work here; promoting the
handful of fixed constants named under CEO Controls to real,
CEO-configurable `RiskLimits`-style fields, the same pattern Chapters
57–59 already established; and a real Knowledge Quality Score, scoped
from already-real signals rather than fabricated.

**What's explicitly out of scope until named gaps close:** true
vector/semantic search or natural-language queries (no embedding/LLM
dependency exists in this codebase — see Future Expansion above);
Duplicate Knowledge Reduction as a KPI (no dedup logic exists to measure
against); a proposal-time Cross-Reference search over research/
simulations (today's Similarity Engine only looks backward over closed
trades).

**Before implementation begins:** per Appendix G's Permanent Development
Policy, this chapter is the required design-first step. Given how much
is already real, implementation should be scoped narrowly to the three
genuinely-new items above — the Knowledge Graph extension, the CEO
controls, and the Quality Score — rather than re-touching any of the
already-working systems this chapter documents.
