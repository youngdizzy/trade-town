# Chapter 61 — Institutional Knowledge Graph & Company Memory Engine

**Status:** Substantially implemented. The Knowledge Graph extension
(`app/knowledge_graph.py`, three new node types), the Pattern
Detection Sensitivity CEO controls (`RiskLimits.minSimilarMatches`/
`mistakeWarningSharePct`), both slices of Knowledge Retention Rules
(`RiskLimits.maxDecisionVaultEntries`/`maxMemoryRecords`), and the
Knowledge Quality Score (`GET /api/decision-vault/quality-score`) are
all real, backend and frontend where a real UI surface applies (the
Knowledge Graph's existing `KnowledgeGraphView.tsx` renders it
unchanged, since the graph shape was already generic; the Knowledge
Quality Score has a new card in `DecisionVaultPanel.tsx`). Five CEO
Controls rows remain honestly out of scope — Archive Policies, Memory
Weighting, and Knowledge Validation Rules each require inventing a new
subsystem this codebase has no real signal to back (see CEO Controls
below for exactly why each one specifically can't be closed the same
"promote a constant" way the others were); Learning Sensitivity and
Historical Search Depth are both genuine, buildable future slices in
that same pattern, just not attempted in this pass. See
[Volume 9's chapter template](README.md) for what every section below
must contain, and the Implementation Notes at the bottom of this
chapter for exactly what's real today.

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

**Built** — `app/decision_vault.py`'s `compute_knowledge_quality_score()`,
exposed via `GET /api/decision-vault/quality-score`. A real, three-part
composite, computed fresh per request (never persisted, matching the
Knowledge Graph's own "no second driftable copy" convention), over
`DecisionVaultEntry`. Deliberately does NOT attempt the brief's
Accuracy/Usefulness/Validation dimensions — no signal anywhere in this
codebase measures any of those:

- **Historical Success** — the real win rate of every other Vault entry
  sharing this entry's own symbol/marketRegime/confidenceTier profile,
  reusing the exact same three-tier Similarity Engine bucket match the
  War Room already uses.
- **Pattern Frequency** — how many other Vault entries share that same
  profile. An honest proxy for "how often has this kind of situation
  recurred," explicitly NOT a literal usage counter — nothing in this
  codebase tracks how many times a specific entry was actually shown to
  the CEO in a real War Room session (`SimilarTradesSummary` is computed
  fresh per request, never logged).
- **Relevance** — how recent this entry is relative to the Vault's own
  real age span (its oldest entry's simDay to the current sim day), not
  an arbitrary fixed decay window.

`overallScore` averages whichever of the three are real; when no
comparable entry exists at all, Historical Success is honestly `None`
and the score falls back to Relevance alone rather than letting an
empty cohort look like poor quality. Surfaced in
`DecisionVaultPanel.tsx` as a new card alongside the existing Trade
Report Card and Similarity Engine reads.

## CEO Controls

| Control | Status |
|---|---|
| Knowledge Retention Rules | **Built** — both slices are real CEO-configurable fields, each defaulting to the exact prior fixed constant. `RiskLimits.maxDecisionVaultEntries` (default 200, matching `MAX_DECISION_VAULT_ENTRIES`) is threaded through `record_vault_entry()`. `RiskLimits.maxMemoryRecords` (default 200, matching `MAX_MEMORY_RECORDS`) is threaded through `app/memory.py`'s `record()` and every one of `app/scribe.py`'s 18 wrapper functions. |
| Archive Policies | **Not built** — evicted entries are simply dropped, never archived to a second, longer-term store. |
| Learning Sensitivity | **Not built** — `app/wisdom.py`'s reflection cadence (weekly/monthly) is fixed. |
| Memory Weighting | **Not built** — no signal is weighted differently by recency or importance anywhere in Company Memory. |
| Historical Search Depth | **Not built** — the Similarity Engine always searches the full capped Vault; no configurable lookback window. |
| Pattern Detection Sensitivity | **Built** — `RiskLimits.minSimilarMatches`/`mistakeWarningSharePct` are now real CEO-configurable fields, both defaulting to the exact prior fixed constants so existing behavior is unchanged until the CEO adjusts them. |
| Knowledge Validation Rules | **Not built** — no entry is ever marked "validated" vs. "unvalidated." |
| Research Priority | **Overlaps** with `app/research.py`'s existing `ResearchItem.priority` field — already real, not a new control this chapter would add. |

Every remaining "Not built" row above names the exact same kind of
fixed constant Chapters 57–59 already promoted to real `RiskLimits`
fields, and Pattern Detection Sensitivity's own two constants and both
Knowledge Retention Rules slices already were, above — the same
closeable pattern, not yet applied to the rest.

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

**What was actually built (Knowledge Graph extension — backend + frontend):**
the single largest real, closeable piece of work this chapter named —
`app/knowledge_graph.py`'s `build_knowledge_graph()` gained three new
node types, each backed by an already-real, already-persisted object:
`trade` (`DecisionVaultEntry`), `case_study` (`CaseStudy` — mistakes and
successes alike), and `strategy` (`Strategy`, excluding those still in
the raw `idea` stage, mirroring the existing "only completed research
becomes a node" filter). Four new, honestly-labeled edge relations:
`documented_by` (a trade's own real `caseStudyId` link), `same_symbol`
(a trade and completed research sharing a real symbol — descriptive,
never claimed as causal, since no field anywhere links a specific
ResearchItem to a specific trade), `same_category` (a Strategy and
completed research sharing a real `focusCategory`/`category`, same
non-causal honesty boundary), and `created` (a Strategy's own real
`createdBy` agent — a literal fact, not an inference). `KnowledgeGraphView.tsx`
needed no structural change (the graph shape was already generic) — only
its `TYPE_COLORS`/`TYPE_LABELS`/`NODE_RADIUS` maps and `types.ts`'s
mirrored `KnowledgeNodeType`/`KnowledgeEdgeRelation` unions gained the
three new node types and four new relations. Verified: 8 new backend
unit tests (`tests/test_knowledge_graph.py`'s
`TestKnowledgeGraphChapter61Extension`), `mypy`/`ruff` clean, full
backend suite 1002/1002 passing, `tsc`/`eslint`/`vite build` clean, and
a live 400-tick simulation (Executive mode, to force real trades to
close) confirming all three new node types and all four new edge
relations appear with real data via a direct `GET /api/knowledge-graph`
call against the running dev server, plus the existing Knowledge Graph
Playwright test passing unchanged against the updated backend.

**What was actually built (Pattern Detection Sensitivity CEO
controls):** two new `RiskLimits` fields, `minSimilarMatches` (default
3) and `mistakeWarningSharePct` (default 30.0), each defaulting to the
exact prior fixed constant so existing behavior is unchanged until the
CEO adjusts them. `app/decision_vault.py`'s `find_similar_vault_entries()`
and `summarize_similarity()` both gained an optional parameter
(`min_matches`, `mistake_warning_share`) defaulting to the module
constant — every other caller keeps today's exact behavior.
`app/war_room.py`'s `build_war_room_session()` gained a required
`risk_limits` parameter threading the CEO's real, current values through
to both calls — the same real, single call site (`app/nexus.py`) already
had `effective_risk_limits` in scope for the Opportunity Gatekeeper call
immediately after, so no new plumbing was needed there. `POST
/api/risk-limits` extended with both fields, validated (`minSimilarMatches`
≥ 1; `mistakeWarningSharePct` in `(0, 100]`, since 0% would fire a
warning on zero real mistakes). Verified: 4 new backend tests for the
Similarity Engine's own tiering/threshold behavior
(`tests/test_decision_vault.py`), 5 new tests for the CEO write path
(`tests/test_state.py`), `mypy`/`ruff` clean, full backend suite
1010/1010 passing, and a live simulation confirming the CEO-configured
values flow through to real `WarRoomSession.similarTrades` reads
without error.

**What was actually built (Knowledge Retention Rules — Decision Vault
slice):** one new `RiskLimits` field, `maxDecisionVaultEntries` (default
200), matching the exact prior fixed constant so existing behavior is
unchanged until the CEO adjusts it. `app/decision_vault.py`'s
`record_vault_entry()` gained an optional `max_entries` parameter
defaulting to the module constant `MAX_DECISION_VAULT_ENTRIES` — its one
real call site (`app/nexus.py`, immediately after a trade closes) now
passes `effective_risk_limits.max_decision_vault_entries`, the same
`effective_risk_limits` already in scope at that point in the tick for
the Opportunity Gatekeeper call right after it, so no new plumbing was
needed. `POST /api/risk-limits` extended with the field, validated
(`maxDecisionVaultEntries` ≥ 1). Verified: 2 new backend tests for the
lower/higher CEO-configured ceiling (`tests/test_decision_vault.py`), 2
new tests for the CEO write path (`tests/test_state.py`), `mypy`/`ruff`
clean, full backend suite 1014/1014 passing, and a live
`POST /api/risk-limits` call against the running dev server confirming
both the accepted value (`maxDecisionVaultEntries: 50` echoed back in
the response) and the rejected one (`0` → "Maximum Decision Vault
Entries must be at least 1.").

**What was actually built (Knowledge Retention Rules — Company Memory
slice):** the change flagged above as "larger, riskier" and deferred —
done in a separate, careful pass. One new `RiskLimits` field,
`maxMemoryRecords` (default 200), matching the exact prior fixed
constant `MAX_MEMORY_RECORDS` (`app/memory.py`) so existing behavior is
unchanged until the CEO adjusts it. `app/memory.py`'s `record()` gained
an optional `max_records` parameter defaulting to the module constant.
Every one of `app/scribe.py`'s 18 wrapper functions (the real "one
writer gateway" callers — see that module's own docstring) gained the
same optional `max_records` parameter, passed straight through to every
internal `record()` call. Two of `app/nexus.py`'s tick helpers
(`_maybe_call_meeting`, `_apply_operating_mode`) needed the value
threaded one level in, since they run outside `tick()`'s own scope
where `effective_risk_limits` lives; every other of the 20 real call
sites inside `tick()` itself already had it in scope. `POST
/api/risk-limits` extended with the field, validated
(`maxMemoryRecords` ≥ 1). Verified: 3 new tests for `record()`'s own
capping behavior at a CEO-lowered/raised ceiling
(`tests/test_memory.py` — a new file, since none existed for
`app/memory.py` before this pass), 2 new tests confirming a
representative `app/scribe.py` wrapper (`record_scanner_alert`) passes
its `max_records` straight through rather than silently keeping the
default (`tests/test_scribe.py` — also new), 2 new tests for the CEO
write path (`tests/test_state.py`), `mypy`/`ruff` clean, full backend
suite 1021/1021 passing, and a live 48-simulated-hour `POST
/api/time/advance` run against the running dev server (CEO
`maxMemoryRecords` set to 20 beforehand) confirming the memory log
capped at exactly 20 real entries across research, discovery,
future-trade, meeting, discussion, mentorship, academy, alert, and
simulation record paths, with no errors in the server log.

**What was actually built (Knowledge Quality Score — backend +
frontend):** `app/decision_vault.py`'s `compute_knowledge_quality_score()`,
computed fresh per request from the Similarity Engine's own three-tier
bucket match — see the Knowledge Quality Score section above for the
exact Historical Success/Pattern Frequency/Relevance composite and its
honesty boundary. Exposed via `GET /api/decision-vault/quality-score`
(mirroring the existing `report-card`/`similar` read-only convention in
`app/routers/decision_vault.py`), honoring the CEO's
`RiskLimits.minSimilarMatches` the way the standalone `/similar`
endpoint does not (a pre-existing gap in that older endpoint, left
as-is since it's unreachable dead code on the frontend today — see
Known Issues below). `types.ts`/`net/api.ts` gained the mirrored type
and client call; `DecisionVaultPanel.tsx` gained a new card rendered
alongside the existing Trade Report Card and Similarity Engine reads.
Verified: 6 new backend tests covering the no-comparable-entry
fallback, the full composite's exact arithmetic, the entry excluding
itself from its own comparison, the Pattern Frequency cap staying
bounded while the raw count stays honest, and CEO-lowered
`minSimilarMatches` changing which tier wins
(`tests/test_decision_vault.py`), `mypy`/`ruff` clean, full backend
suite 1026/1026 passing, `tsc`/`eslint`/`vite build` clean, and a live
simulation (Executive mode, 120 simulated hours) confirming the
endpoint returns real, internally-consistent numbers for both an old
and a newly-closed Vault entry, and a clean 404 for an unknown id.

**Known Issues found and fixed along the way (bugs, not scope):**
`frontend/src/types.ts`'s `RiskLimits` interface was missing all four
fields Chapter 61's own earlier passes added to the backend
(`minSimilarMatches`, `mistakeWarningSharePct`, `maxDecisionVaultEntries`,
`maxMemoryRecords`) — a real gap, now fixed. Discovered because fixing
it surfaced a second, older, unrelated bug: `NexusManager.ts`'s and
`gameStore.ts`'s static default `RiskLimits` objects were already
missing two Chapter 59 fields (`minPriorityScore`, `capitalReservePct`)
before this pass ever touched the file — a real pre-existing TypeScript
error that `npx tsc --noEmit` alone did not catch (only the full `npm
run build`'s `tsc -b --noEmit` project-reference build check does).
Both defaults now include every real `RiskLimits` field with its actual
backend default value.

**What's explicitly not yet built:** five CEO Controls rows — Archive
Policies, Learning Sensitivity, Memory Weighting, Historical Search
Depth, and Knowledge Validation Rules (see CEO Controls above for which
of those are genuinely buildable in a future pass versus which would
require inventing a signal this codebase doesn't have). True
vector/semantic search or natural-language queries stay out of scope
entirely (no embedding/LLM dependency exists in this codebase — see
Future Expansion above); Duplicate Knowledge Reduction as a KPI (no
dedup logic exists to measure against); a proposal-time Cross-Reference
search over research/simulations (today's Similarity Engine only looks
backward over closed trades).

**Before implementation begins:** per Appendix G's Permanent Development
Policy, this chapter is the required design-first step, satisfied before
this pass began. The remaining CEO controls are a
well-scoped, separate follow-up.

## Addendum — Institutional Memory 2.0 (CEO directive "Features 26-30: Agent Intelligence, Learning & Institutional Memory System," Feature 26)

**Research finding, documented before code was written:** this chapter's
own existing infrastructure — `app/scribe.py`'s `MemoryRecord` (a flat,
append-only company-history log) and `app/decision_vault.py`'s
`KnowledgeQualityScore` (a fresh-computed relevance/pattern-frequency/
historical-success composite over one record type, `DecisionVaultEntry`)
— covers logging and single-record scoring, but neither promotes real
evidence from *multiple* record types (a filed case study, a failed
strategy, a Hall of Fame induction, a Model Validation finding, a
critical risk warning, a market regime shift) into one queryable,
contradiction-aware, confidence-scored store of reusable lessons. That
gap is what this addendum closes — `app/institutional_memory.py`, a
promotion layer sitting on top of the six sources above, not a second
event log and not a second Knowledge Graph (`app/knowledge_graph.py`'s
own non-causal-edge graph is untouched).

**Design, reusing this codebase's own established formulas rather than
inventing new math:**
- **Observation / interpretation / lesson**, kept as three separate,
  honestly-nullable fields per entry — an `InstitutionalMemoryEntry`
  never states an interpretation as proven fact, matching the Knowledge
  Graph's own "never `caused`" edge-labeling discipline above. A source
  record with nothing to interpret (a routine risk warning) leaves
  `interpretation`/`lesson` `null` rather than padding out invented
  text.
- **Confidence** — a real corroboration count (how many other active
  entries share this entry's source, and its market regime when both
  have one) normalized against a cap, the exact shape this chapter's own
  `PATTERN_FREQUENCY_CAP` already established for Pattern Frequency
  above, applied to institutional memory's own real match key.
- **Relevance** — `compute_knowledge_quality_score()`'s exact recency-
  decay formula, verbatim: `1 - age/span` over the memory list's own
  real age span. Recomputed fresh at read time (`retrieve_relevant_memory()`),
  never trusted from what was stamped at write time — the same
  "computed fresh per request, never a second driftable copy"
  discipline this chapter's Knowledge Quality Score section already
  states for its own three signals.
- **Contradiction / update handling** — `find_related_memory()` reuses
  `app/constitution.py`'s exact significant-word-overlap check
  (`_founder_verdict()`'s own redundancy detector) to surface candidate
  related entries; it never decides on its own whether a match is an
  update, a contradiction, or mere corroboration, since no signal in
  this codebase can make that semantic call automatically. Making the
  call explicit is `supersede_memory()`'s job: the old entry's `status`
  flips to `"superseded"`/`"contradicted"` and links to the new entry
  that replaced it — the old row stays on file permanently, never
  deleted, preserving history exactly as the directive requires.
- **Insufficient evidence** — `retrieve_relevant_memory()` returns
  `None`, never a forced weak answer, when nothing on file matches the
  query, or when the single best match's freshly recomputed relevance
  has decayed below a disclosed threshold (`MIN_RELEVANCE_FOR_RETRIEVAL`,
  a configurable research assumption this module's own choice, not
  presented as established fact — the same provenance discipline
  `app/model_validation.py`'s own threshold table uses).

**Wiring — real event points only, no synthetic triggers:**
`app/nexus.py`'s tick promotes a case study (mistake or success side)
the moment `app/mistakes.py`/`app/successes.py` file one, a critical
risk warning the moment it's genuinely new (the same gate the existing
Article I/VII citation already uses), and a market regime shift the
moment `app/market_environment.py` detects a real regime change.
`app/state.py`'s `request_strategy_company_review()` promotes a non-
`"approved"` `ModelValidationReport` (an `"approved"` verdict is the
expected outcome of Meridian's process working normally, not a
finding); `retire_strategy()` promotes whichever of the real
`StrategyHallOfFameEntry`/`FailedStrategyArchiveEntry` was filed.
Persisted under `knowledge_archive` in `app/save_modules.py` (alongside
`case_studies`/`decision_vault`), broadcast via `app/ws_manager.py`'s
`institutionalMemory` field, and readable through a new
`GET /api/institutional-memory/retrieve` endpoint (mirroring this
chapter's own `routers/decision_vault.py` read-only convention) for the
one genuinely new query the full-state broadcast can't offer: "what's
the single most relevant thing we know" for a given source/regime.

**Explicit staging note:** `InstitutionalMemorySource` is deliberately
scoped to the seven sources this codebase can honestly back today.
`"prediction"` (Feature 29), `"agent_debate"`/`"performance_review"`
(Features 30/27) are intentionally not added yet — each is deferred
until its own feature is actually built and can honestly promote into
this sink, per the CEO's own 26→27→28→29→30 pipeline order. This is a
disclosed staging decision, not a silent gap.

**Frontend:** extends this chapter's own `KnowledgeBasePanel.tsx`
(Feature 47's "everything the company has learned" surface, OPS tab)
with a second card, "Institutional Memory — promoted lessons," rather
than a new dashboard page — source-filterable, showing confidence/
relevance/status per entry and dimming (not hiding) a superseded/
contradicted row. No new top-level Command Center tab was added.

**Verified:** 30 new backend tests (`tests/test_institutional_memory.py`)
covering every `promote_*()` function's real-field sourcing, confidence
corroboration, relevance decay recomputed fresh at read time, cap
behavior, `find_related_memory()`'s real-overlap-vs-unrelated-text/
cross-source cases, `supersede_memory()`'s never-deletes-history
behavior (including the already-superseded-can't-be-superseded-again
case), and `retrieve_relevant_memory()`'s honest `None` behavior on no
match and on decayed relevance; full backend suite (1822 tests), `mypy`,
`ruff` all clean; `tsc -b --noEmit`, `eslint`, `vite build` all clean;
live Playwright verification against the running dev stack confirmed a
real `market_regime_shift` entry generated by the live simulation,
returned correctly by `GET /api/institutional-memory/retrieve`, and
rendered in the OPS tab's new card.
