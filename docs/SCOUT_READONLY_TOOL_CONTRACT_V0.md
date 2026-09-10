# TradeTown Scout Read-Only Tool Contract — v0

**Milestone 1 deliverable. Specification only. No implementation.**

---

## 1. Status

| Field | Value |
|---|---|
| Contract name | TradeTown Scout Read-Only Tool Contract |
| Version | `v0` |
| Status | **DRAFT — authored, not implemented, not ratified** |
| Authored | 2026-09-05 |
| Repository state at authoring | branch `claude/tradetown-v0-1-build-dn1ufw`, HEAD `39bfe9e` |
| Implements | nothing |
| Blocks | Milestone 2 (TradeTown MCP server, read-only implementation) |

This document defines the boundary between a **future** external reasoning agent
(working name `tt-scout`, hosted on an OpenClaw runtime) and TradeTown. It
creates no code, no endpoints, no credentials, and no network exposure. Nothing
described here exists yet unless explicitly marked `[V]`.

Read §17 (Non-goals) before assuming any capability is being built.

---

## 2. Scope

**In scope:** the specification of five read-only tools, the mission object they
depend on, the future `ScoutFinding` submission shape, and the authentication,
audit, failure, rate-limit, and security rules that govern the boundary.

**Out of scope:** everything else. See §17.

The five tools:

1. `tt_get_mission`
2. `tt_read_market_data`
3. `tt_search_approved_research`
4. `tt_read_institutional_memory`
5. `tt_list_prior_findings`

---

## 3. Evidence classification

Every claim in this document carries one of four markers. **No marker is ever
silently upgraded.**

| Marker | Meaning |
|---|---|
| `[V]` | Verified directly in this repository at HEAD `39bfe9e`, with file and line |
| `[D]` | Documented external behavior (OpenClaw docs, cited by path) |
| `[U]` | User-supplied, not verified in this repository |
| `[P]` | Proposed future architecture — does not exist |

Where a tool requires a capability TradeTown does not have, this document says
**NOT CURRENTLY IMPLEMENTED** in bold and does not describe it as existing.

---

## 4. Existing architecture dependencies

### 4.1 What was verified

| Area | Finding | Evidence |
|---|---|---|
| Backend stack | FastAPI, Python, SQLAlchemy, SQLite (`sqlite:///./data/tradetown.db`) | `[V]` `backend/app/main.py:57`, `db.py:15`, `config.py:17` |
| Wire format | All JSON camelCase via Pydantic `CamelModel` with `populate_by_name=True`; snake_case internally | `[V]` `docs/API.md:5-9` |
| Error convention | FastAPI `HTTPException(status_code=…, detail="…")`; `400` for unsupported timeframe / invalid ISO-8601 | `[V]` `routers/market.py:72,78,82` |
| **Inbound authentication** | **NONE. "There is no authentication — the app is single-tenant (one company, one save slot) by design."** Only CORS middleware. | `[V]` `docs/API.md:4-6`, `main.py:59-65` |
| Outbound credentials | Two, both env-only: `TRADETOWN_AI_PROVIDER_API_KEY`, `EXTERNAL_MARKET_DATA_API_KEY` | `[V]` `ai_provider.py:44`, `market_data.py:712` |
| Market data (default) | **Simulated.** Process-wide singleton is `MockMarketDataProvider`; `_select_provider()` returns mock for every value of `MARKET_DATA_PROVIDER` | `[V]` `market_data.py:572-577` |
| Market data (external) | `ExternalMarketDataProvider` exists as a **standalone, opt-in, never-auto-substituted** class; raises `ExternalMarketDataProviderUnavailable` rather than falling back | `[V]` `market_data.py:679-700` |
| Broker | `PaperBroker`, 100% simulated. "one broker … no credentials of any kind" | `[V]` `audit_log.py:5-10` |
| Live trading | **No live-trading flag, mode, or switch exists anywhere.** Grep for `live_trading`/`is_live`/`real_money`/`broker_live` returns zero hits | `[V]` repo-wide grep |
| Time model | Dual: simulated (`sim_day`, `*_sim_minutes`) and real ISO-8601 wall-clock. Deliberately distinct concepts | `[V]` `schemas.py:664,806,903`; `market_data.py:85-94` |
| AI provider abstraction | One real minimal abstraction; returns `UnavailableAIProvider` unless `TRADETOWN_AI_PROVIDER_API_KEY` is set; never fabricates success | `[V]` `ai_provider.py:1-27,177-181` |
| Persistence for new records | SQLAlchemy models + SQLite; save-slot/run isolation via `persistence.py` | `[V]` `db.py`, `persistence.py`, `main.py:24-45` |

### 4.2 Existing records this contract depends on

| Record | Purpose | Evidence |
|---|---|---|
| `AIEvidencePacket` | The one bounded, snapshotted context an AI call may see. Carries `knowledge_cutoff_sim_minutes` (hard anti-lookahead boundary), `known_limitations`, `context_builder_version`. Built once, never mutated, never re-derived at replay time | `[V]` `schemas.py:13645-13672` |
| `AIEvidenceItem` | One citable evidence item. Its `id` is **"the ONLY handle the model may cite back"**; `as_of_sim_minutes` may never exceed the packet's cutoff | `[V]` `schemas.py:13629-13643` |
| `AIReasoningResult` | The persisted, validated, structured result of one reasoning call — or an honest failure. Every result traces to exactly one packet by id. Never persists secrets or chain-of-thought | `[V]` `schemas.py:13674-13710` |
| Citation validation | Real and enforced: unknown cited ids are collected into `invalidCitations` and `citationValidationPassed` is set false | `[V]` `ai_reasoning.py:283,335-336` |
| `InstitutionalMemoryEntry` | Durable lesson store; separates `observation` / `interpretation` / `lesson`; `provenance` + `event_ref` trace to the source record; supersession chain never overwrites history | `[V]` `schemas.py:9384-9430` |
| `ResearchCouncilFinding` / `ResearchCouncilReport` | Per-role finding with `evidence_references` and `confidence` ∈ {high, medium, low}; report is **advisory only, never wired into** candidacy/Champion-Challenger/Certification | `[V]` `schemas.py:15110-15134` |
| `DepartmentOpinion` | Role, stance, summary, `confidence_pct`, plus structured `evidence`/`concerns`/`benefits`/`alternative` | `[V]` `schemas.py:3650-3668` |
| `AuditEntry` | Game-world audit event: category, severity, department, summary, detail, `related_id`, `sim_day` | `[V]` `schemas.py:10843-10858` |
| `Candle` / `Quote` | OHLCV bar (`data_status`) and quote (`price`, `change_pct`, `volume`) | `[V]` `market_data.py:74-102`, `schemas.py:496` |
| `DataProvenanceReport` | Whole-codebase audit classifying each subsystem REAL / SYNTHETIC / SIMULATED / USER_PROVIDED / UNAVAILABLE | `[V]` `schemas.py:1394-1406` |
| `ResearchBudgetStatus` | Real research-experiment budget with `MAX_ITERATIONS_PER_FAMILY = 20`, `MAX_MUTATIONS_PER_PARENT = 5` | `[V]` `schemas.py:14685-14699`, `research_loop.py:146-147` |

### 4.3 Enumerations that constrain this contract

```
AgentId              = Literal["scout", "atlas", "echo", "nova", "scribe",
                               "coach", "sentinel", "pulse", "guardian",
                               "cio", "sage", "keystone", ...]      [V] schemas.py:75
AIReasoningRole      = Literal["researcher", "devils_advocate",
                               "sniper_analyst"]                     [V] schemas.py:13600
AIReasoningStatus    = Literal["completed", "provider_unavailable",
                               "provider_timeout", "provider_error",
                               "invalid_output"]                     [V] schemas.py:13605
AIEvidenceKind       = Literal["fact", "historical", "knowledge",
                               "unknown"]                            [V] schemas.py:13613
AIRecommendation     = Literal["buy", "sell", "wait", "research_more",
                               "reject_thesis"]                      [V] schemas.py:13620
ResearchCouncilRole  = Literal["researcher", "quant", "risk_manager",
                               "adversarial_researcher",
                               "regime_analyst", "statistician",
                               "reviewer"]                           [V] schemas.py:15106
```

### 4.4 Capabilities that DO NOT exist

**NOT CURRENTLY IMPLEMENTED — every item below must be built before or during
Milestone 2. None of these may be described as existing.**

1. **Any inbound authentication or authorization.** No API keys, no bearer
   tokens, no sessions, no per-caller identity. `[V]` `docs/API.md:4`
2. **Any "approved for agent consumption" classification.** Repo-wide grep for
   `approved_for`, `agent_readable`, `is_approved`, `approval_state` returns
   **zero hits**. The only `approved` in the codebase is a
   `ModelValidationReport.verdict` value, semantically unrelated.
   `[V]` `institutional_memory.py:203-234`
3. **Any mission concept.** Grep for `class Mission`, `mission_id`,
   `MissionRecord` returns **zero hits**. `[V]`
4. **Any HTTP rate limiting, request budget, or quota.** The existing budget
   (`ResearchBudgetStatus`) counts research experiments, not API calls. `[V]`
5. **Any external-agent identity.** `AgentId` is a closed literal of in-game
   employees. `[V]` `schemas.py:75`
6. **Any MCP server, client, or dependency.** `[V]`
7. **Real market data by default.** `[V]` `market_data.py:572-577`

---

## 5. Duplication audit

Classification key: **A** reuse directly · **B** wrap/adapt later · **C** related
but semantically different · **D** no existing equivalent verified · **E**
dangerous duplication, must not be created.

| Proposed concept | Class | Existing system | Ruling |
|---|---|---|---|
| **Agent identity "Scout"** | **C** | `[V]` `AgentId` already contains `"scout"` — a real in-game employee with a research queue, schedule, memory log, and *explicitly* "Decision Authority: None" (`docs/AI_AGENT_BIBLE.md:31-46`) | **See Decision D-1. The external agent MUST NOT silently reuse `AgentId="scout"`.** |
| Mission | **D** | none | Create as boundary concept. Must reference an existing `AIEvidencePacket` rather than re-implementing context scoping. |
| Evidence scope / context snapshot | **A** | `AIEvidencePacket` | **Reuse.** Do not build a second context builder. |
| Citable evidence item | **A** | `AIEvidenceItem` + citation validation | **Reuse verbatim.** `id` remains the only citable handle. |
| Anti-lookahead boundary | **A** | `knowledge_cutoff_sim_minutes` | **Reuse.** Do not invent a second cutoff. |
| ScoutFinding | **C→D** | `AIReasoningResult` covers ~80% of it | **Boundary DTO only (option D at the wire, option A at rest).** See §9. |
| Finding role | **C** | `AIReasoningRole` is a closed 3-value literal with no scout value | Extend the existing literal; do not create a parallel role system. See Decision D-2. |
| Observations | **A** | `AIEvidenceItem` | Reuse. An observation is a cited packet item, not a new record type. |
| Disconfirming evidence | **A** | `AIReasoningResult` already models contradictory citations `[V]` `ai_reasoning.py:283` | Reuse the existing contradictory-citation channel. |
| Analyst opinion | **B** | `DepartmentOpinion`, `StrategyDepartmentOpinion` | Not in v0 (no submit tools). When added, wrap — do not duplicate. |
| Research records | **A** | `ResearchItem`, `QuantResearchExperiment`, `ResearchExperimentRecord`, `ResearchCouncilReport` | Reuse as the read source. |
| Research approval state | **D** | none | Must be built. See §12.3. |
| Institutional memory | **A** | `InstitutionalMemoryEntry` | Reuse as the read source. **Never create a second memory store.** |
| Memory approval state | **D** | none | Must be built. See §12.4. |
| Provenance | **A** | `InstitutionalMemoryEntry.provenance` + `event_ref`; `DataProvenanceReport`; `AIEvidenceItem.as_of_sim_minutes` | Reuse all three. |
| Simulated/real data labeling | **A** | `DataStatus` on `Candle`; `DataProvenanceReport` categories | Reuse. |
| Audit — game world | **C** | `AuditEntry` is CEO-facing, department-scoped, `sim_day`-stamped | Do **not** write machine-access rows into it. |
| Audit — agent access | **D** | none | New infrastructure log required. See §11. Justified: different actor, different retention, different reader. |
| Outcome evaluation | **A** | `prediction_tracking.py`, `performance_attribution.py`, `trade_attribution.py`, `evaluation_simulator.py` | Reuse when evaluation is wired. Not in v0. |
| Rate limiting | **D** | `ResearchBudgetStatus` is a *research* budget, not a request budget | New, minimal, boundary-local. |
| Second market-data provider | **E** | `MarketDataProvider` ABC + two implementations | **Forbidden.** Serve existing providers; never add a third for Scout. |
| Second event log | **E** | `scribe.py` `MemoryRecord` | **Forbidden.** `[V]` `institutional_memory.py:11-19` already warns against this. |
| Second knowledge graph | **E** | `knowledge_graph.py` | **Forbidden.** |
| Second AI result type | **E** | `AIReasoningResult` | **Forbidden at rest.** A wire DTO is not a second store. |
| Shared cross-agent context | **E** | — | **Forbidden.** See §13.6. |

### Decision D-1 — Agent identity `[P]` PROPOSED CONTRACT DECISION

The external agent is named **`tt-scout`** and is **not** the in-game `scout`
employee. Rationale: `AgentId` is a closed literal describing simulated staff
with in-world schedules and offices; conflating an external process with a
simulated employee would corrupt every downstream consumer that assumes
`AgentId` means "an employee in the building."

The external agent identity lives in a new, separate field
`external_agent_id: str` on the boundary DTO and on every audit row. It is
**not** an `AgentId`.

**Why this cannot be resolved without a decision:** whether `tt-scout`'s output
should later be attributed to the in-game `scout` employee (making the external
agent that employee's reasoning brain) is a product question about TradeTown's
fiction, not a fact derivable from the repository. v0 keeps them separate; that
choice is reversible in one direction only, which is why it is stated here.

### Decision D-2 — Reasoning role `[P]` PROPOSED CONTRACT DECISION

When submission is implemented (not v0), `AIReasoningRole` gains the value
`"scout_market_research"`. Rationale: extending a closed literal is a schema
migration with a known blast radius; creating a parallel role enum is
permanent architectural drift. `[V]` The existing literal is already extended
this way — `"sniper_analyst"` was added for the Memecoin Sniper domain
(`schemas.py:13600`), establishing the precedent.

---

## 6. Trust-boundary diagram

```
┌──────────────────────────────── OpenClaw VPS ────────────────────────────────┐
│  Gateway — loopback only, never exposed                          [V]         │
│    └── agent "tt-scout"                                          [P]         │
│          minimal tool profile · no fs · no exec · no web                     │
│          holds: TradeTown-issued narrow credential               [P]         │
│          holds: NOTHING else of TradeTown's                                  │
└───────────────────────────┬──────────────────────────────────────────────────┘
                            │ outbound only, private network        [P]
                            │ MCP (OpenClaw is the CLIENT)          [D]
                            ▼
┌──────────────────────────── TradeTown environment ───────────────────────────┐
│  MCP server (read-only)                                          [P]         │
│    ├── authenticates the credential          NOT CURRENTLY IMPLEMENTED       │
│    ├── authorizes per tool                   NOT CURRENTLY IMPLEMENTED       │
│    ├── enforces scope, freshness, limits     NOT CURRENTLY IMPLEMENTED       │
│    └── writes agent-access audit rows        NOT CURRENTLY IMPLEMENTED       │
│                            │                                                 │
│                            ▼                                                 │
│  Existing TradeTown systems (READ ONLY through this boundary)     [V]        │
│    market_data · research records · InstitutionalMemoryEntry ·               │
│    AIEvidencePacket · AIReasoningResult                                      │
│                            │                                                 │
│                            ▼                                                 │
│  ╔═══════════════════════════════════════════════════════════════╗           │
│  ║  NEVER REACHABLE FROM THIS BOUNDARY (see §14)                 ║           │
│  ║  Gatekeeper · Risk Contract · position sizing · execution ·   ║           │
│  ║  orders · fills · positions · balances · kill switch ·        ║           │
│  ║  emergency stop · paper/live · strategy deployment            ║           │
│  ╚═══════════════════════════════════════════════════════════════╝           │
└──────────────────────────────────────────────────────────────────────────────┘

TradeTown NEVER holds an OpenClaw gateway credential. The arrow is one-way.
```

---

## 7. Tool contracts

### 7.0 Rules applying to all five tools

| Property | Value |
|---|---|
| Contract version | `v0` — every response carries `contractVersion: "v0"` |
| Read/write class | **READ-ONLY.** No tool may create, modify, delete, approve, reject, promote, schedule, or execute anything. |
| Authority owner | TradeTown, without exception |
| Authentication | Required on every call. **NOT CURRENTLY IMPLEMENTED** — see §10 |
| Authorization | Per-tool grant on the credential. **NOT CURRENTLY IMPLEMENTED** — see §10 |
| Wire format | camelCase JSON, matching `CamelModel` `[V]` `docs/API.md:5-9` |
| Idempotency | All five are idempotent and side-effect-free in business state. Repeat calls with identical inputs return equal results except where live market data legitimately advanced. |
| Retry | Safe to retry on `UNAVAILABLE` and `TIMEOUT` with exponential backoff, minimum 1s, maximum 3 attempts `[P]`. Never retry `INVALID_*`, `FORBIDDEN`, `NOT_FOUND`, `EXPIRED`, `OUT_OF_SCOPE`. |
| Empty result | An empty result set is a **success** (`200`, empty array, `"resultCount": 0`). It is never an error and never an inference that no data exists. |
| Unavailable data | Never substituted, never mocked, never interpolated. Return `UNAVAILABLE` with a specific reason. This mirrors `[V]` `ExternalMarketDataProvider`'s own rule: "NEVER A SILENT MOCK FALLBACK" (`market_data.py:697-700`). |
| Timestamps | Every response carries **both** `asOfSimMinutes` (integer, simulated clock) and `retrievedAt` (ISO-8601 UTC wall clock). These are distinct concepts and must never be conflated `[V]` `market_data.py:85-94`. |
| Provenance | Every returned record carries `dataProvenance` ∈ `REAL \| SYNTHETIC \| SIMULATED \| USER_PROVIDED \| UNAVAILABLE`, reusing `[V]` `DataProvenanceReport`'s existing vocabulary (`schemas.py:1394-1400`). |
| Simulation context | Every response carries `"simulationContext": "paper_simulated"`. `[V]` This is the only honest value: `PaperBroker` is 100% simulated and no live mode exists. |
| Deterministic ordering | Every list result has a total order specified per tool. Ties break on `id` ascending. No tool ever returns an unordered set. |
| Audit | Every invocation writes one agent-access audit row (§11) **before** the result is returned. Audit write failure fails the call closed. |
| Timeout | 10s server-side per call `[P]`. See §15 rationale. |
| Max response size | 256 KB serialized `[P]`. Exceeding it is `RESULT_TOO_LARGE`, never silent truncation. |

### 7.1 `tt_get_mission`

| Property | Value |
|---|---|
| Canonical name | `tt_get_mission` |
| Version | `v0` |
| Purpose | Retrieve the single mission assignment the agent is currently authorized to work on, including its evidence cutoff and prohibitions |
| Authority owner | TradeTown |
| Class | Read-only |
| Rate limit | 5 calls per mission `[P]` |
| Cost semantics | Free — excluded from the per-mission call budget in §15 |

**Input schema**

| Field | Type | Req | Rules |
|---|---|---|---|
| `missionId` | string | yes | Non-empty, ≤128 chars, `^[A-Za-z0-9_-]+$` |

**Output schema** — the Mission object, §8.

**Semantics**

- Returns exactly one mission or an error. Never a list.
- The credential must be bound to this `missionId`; otherwise `FORBIDDEN`.
- An expired mission returns `EXPIRED` and returns no mission body.
- Ordering: not applicable (single object).
- Freshness: the mission is a static assignment; `retrievedAt` reflects read time.
- Pagination: none.

**Errors:** `INVALID_ARGUMENT` (400) · `UNAUTHENTICATED` (401) · `FORBIDDEN` (403) · `NOT_FOUND` (404) · `EXPIRED` (410) · `UNAVAILABLE` (503)

---

### 7.2 `tt_read_market_data`

| Property | Value |
|---|---|
| Canonical name | `tt_read_market_data` |
| Version | `v0` |
| Purpose | Read OHLCV candles and/or a current quote for a symbol inside the mission's declared universe |
| Authority owner | TradeTown |
| Class | Read-only |
| Rate limit | 30 calls/mission, 10 calls/minute `[P]` |
| Cost semantics | Counts against the per-mission call budget |

**Input schema**

| Field | Type | Req | Rules |
|---|---|---|---|
| `missionId` | string | yes | Must match the credential's bound mission |
| `symbol` | string | yes | Must appear in the mission's `marketUniverse`; else `OUT_OF_SCOPE` |
| `timeframe` | enum | yes | Server-declared supported set only. **The supported set is whatever the configured `MarketDataProvider` actually supports** `[V]` — `market_data.py:141-148` states an unsupported timeframe raises `ValueError` which `routers/market.py` turns into a `400`, and explicitly forbids "silently substituting a different timeframe." The MCP server MUST source this enum from the provider, never hardcode it. |
| `limit` | integer | no | 1–500, default 100 `[P]`. See §15. |
| `endTimeSimMinutes` | integer | no | If present, must be ≤ mission `knowledgeCutoffSimMinutes`; else `OUT_OF_SCOPE` |
| `includeQuote` | boolean | no | Default `false` |

**Output schema**

```
{
  contractVersion: "v0",
  simulationContext: "paper_simulated",
  symbol: string,
  timeframe: string,
  candles: [ { timestamp, open, high, low, close, volume, dataStatus } ],
  quote: { price, changePct, volume } | null,
  candleCount: integer,
  requestedLimit: integer,
  complete: boolean,          // false when fewer bars exist than requested
  dataProvenance: "SIMULATED" | "REAL" | "UNAVAILABLE",
  providerClass: string,      // e.g. "MockMarketDataProvider"
  knowledgeCutoffSimMinutes: integer,
  asOfSimMinutes: integer,
  retrievedAt: string         // ISO-8601 UTC
}
```

Candle fields mirror `[V]` `market_data.py:85-102` exactly: `symbol`, `timeframe`,
`timestamp` (ISO-8601 wall clock, deliberately *not* the simulated clock),
`open`, `high`, `low`, `close`, `volume`, `data_status`.

**CURRENTLY SUPPORTED vs FUTURE CONTRACT REQUIREMENT**

| Capability | Status |
|---|---|
| OHLCV candles, oldest-first | `[V]` CURRENTLY SUPPORTED — `market_data.py:141` "Oldest-first" |
| Quote with `price`, `changePct`, `volume` | `[V]` CURRENTLY SUPPORTED — `market_data.py:74-82` |
| `dataStatus` per candle | `[V]` CURRENTLY SUPPORTED |
| Historical window anchoring (`end_time`, `anchor_price`) | `[V]` CURRENTLY SUPPORTED — `market_data.py:127-140` |
| Unsupported-timeframe rejection | `[V]` CURRENTLY SUPPORTED — raises `ValueError` → `400` |
| **Real (non-simulated) market data** | **NOT CURRENTLY IMPLEMENTED by default.** The process-wide singleton is mock-only `[V]` `market_data.py:572-577`. `ExternalMarketDataProvider` exists but is standalone and opt-in `[V]` `market_data.py:679-700` |
| **`complete` completeness indicator** | **FUTURE CONTRACT REQUIREMENT** `[P]` — derivable from `len(candles) < limit`, but no field exposes it today |
| **Symbol validation against a mission universe** | **FUTURE CONTRACT REQUIREMENT** `[P]` — no mission concept exists |
| **Staleness detection** | **FUTURE CONTRACT REQUIREMENT** `[P]` — mock data is generated on demand and is never stale; a real adapter will need an explicit staleness rule |

**Stale-data behavior** `[P]`: if the provider reports data older than the
mission's `dataFreshnessMaxAgeSimMinutes`, return the data **with**
`"stale": true` and the measured age. Never silently serve stale data; never
substitute fresh-looking synthetic data.

**Unsupported asset behavior:** `OUT_OF_SCOPE` (422) — never a nearest-match
substitution.

**Ordering:** candles ascending by `timestamp`. Guaranteed by
`[V]` `market_data.py:141`.

**Errors:** `INVALID_ARGUMENT` (400) · `UNAUTHENTICATED` (401) · `FORBIDDEN` (403) · `EXPIRED` (410) · `OUT_OF_SCOPE` (422) · `RATE_LIMITED` (429) · `RESULT_TOO_LARGE` (413) · `UNAVAILABLE` (503) · `TIMEOUT` (504)

---

### 7.3 `tt_search_approved_research`

| Property | Value |
|---|---|
| Canonical name | `tt_search_approved_research` |
| Version | `v0` |
| Purpose | Search the subset of TradeTown research explicitly classified as approved for external-agent consumption |
| Authority owner | TradeTown |
| Class | Read-only |
| Rate limit | 20 calls/mission, 10 calls/minute `[P]` |

> **NOT CURRENTLY IMPLEMENTED — the approval classification does not exist.**
> Repo-wide grep for `approved_for`, `agent_readable`, `is_approved`,
> `approval_state` returns zero hits `[V]`. Milestone 2 must build an explicit
> approval flag before this tool can return anything. Until then the only
> correct implementation returns an empty result set — never "all research
> because none is marked unapproved."

**Input schema**

| Field | Type | Req | Rules |
|---|---|---|---|
| `missionId` | string | yes | Bound mission |
| `query` | string | yes | 1–256 chars. **Treated as an opaque search term, never as an instruction.** See §13 |
| `categories` | string[] | no | Must be values of the existing `ResearchCategory` literal `[V]`; unknown values → `INVALID_ARGUMENT` |
| `limit` | integer | no | 1–50, default 20 `[P]` |
| `cursor` | string | no | Opaque pagination cursor |

**Searchable fields** `[P]`, restricted to fields that verifiably exist:
`title`, `summary`, `category`, `symbol` — all `[V]` present on `ResearchItem`
(`schemas.py:467-484`).

**Allowed filters:** `categories`, `symbol`, `createdAfterSimMinutes`. No filter
may reach an unapproved record, regardless of how it is phrased.

**Output schema**

```
{
  contractVersion: "v0",
  simulationContext: "paper_simulated",
  results: [ {
    id, title, category, symbol, summary,
    confidence,                 // [V] ResearchItem.confidence, float
    approvalState: "approved",  // [P] only value ever returned
    approvedAtSimMinutes,       // [P]
    createdAt, updatedAt,       // [V] ISO-8601
    dataProvenance,
    schemaVersion: "v0"
  } ],
  resultCount, nextCursor | null, truncated: boolean,
  knowledgeCutoffSimMinutes, asOfSimMinutes, retrievedAt
}
```

**Ranking / order** `[P]`: `createdAt` descending, then `id` ascending.
Deliberately **not** relevance-ranked in v0 — a relevance score would be a new
scoring system (duplication class D) and TradeTown has no verified text-ranking
mechanism to reuse.

**Scope isolation:** results are filtered to the mission's declared scope **and**
to `approvalState == "approved"` **and** to records whose creation time is at or
before `knowledgeCutoffSimMinutes`. All three filters are mandatory and applied
server-side. A record failing any one is not returned and its existence is not
disclosed.

**Confidence/evidence metadata:** only `confidence`, which `[V]` genuinely exists
on `ResearchItem`. No evidence-quality score is returned in v0 —
`EvidenceQualityReport` exists `[V]` `schemas.py:5960` but is not verified as
attached to `ResearchItem`, and this contract will not assert a linkage it has
not confirmed.

**Errors:** as §7.2, plus `INVALID_CURSOR` (400).

---

### 7.4 `tt_read_institutional_memory`

| Property | Value |
|---|---|
| Canonical name | `tt_read_institutional_memory` |
| Version | `v0` |
| Purpose | Read the approved slice of institutional memory relevant to the mission's topic scope |
| Authority owner | TradeTown |
| Class | Read-only |
| Rate limit | 20 calls/mission, 10 calls/minute `[P]` |

> **NOT CURRENTLY IMPLEMENTED — the approval classification does not exist**
> (same finding as §7.3). `InstitutionalMemoryEntry` itself is fully real `[V]`
> `schemas.py:9384-9430`; what is missing is the flag saying an entry may leave
> the building.

**Input schema**

| Field | Type | Req | Rules |
|---|---|---|---|
| `missionId` | string | yes | Bound mission |
| `topics` | string[] | no | Must intersect the mission's `topicScope`; a topic outside it → `OUT_OF_SCOPE` |
| `sources` | string[] | no | Values of the existing `InstitutionalMemorySource` literal `[V]` `schemas.py:9348-9362` |
| `marketRegime` | string | no | Value of the existing `MarketEnvironmentRegime` literal `[V]` |
| `limit` | integer | no | 1–50, default 20 `[P]` |
| `cursor` | string | no | Opaque cursor |

**Allowed fields in the response** — allowlist, not denylist:

`id`, `source`, `createdAt`, `simDay`, `eventRef`, `marketRegime`,
`observation`, `interpretation`, `lesson`, `confidence`, `provenance`,
`supersedesId`, `supersededById`, `approvalState`, `schemaVersion`.

All of the above except `approvalState` and `schemaVersion` are `[V]` real fields
on `InstitutionalMemoryEntry` (`schemas.py:9415-9430`).

**Forbidden fields** — never returned, even if present on the record:
`originatingAgent` (in-world employee attribution — see §13.6 anti-anchoring),
and any field added later that is not on the allowlist above. The allowlist is
closed; adding to it is a contract version change.

**Semantics**

- `interpretation` and `lesson` are nullable by design `[V]` and MUST be returned
  as `null` rather than padded. `[V]` `schemas.py:9395-9403` is explicit that a
  source with nothing to interpret leaves these `None`.
- Superseded entries are **included** with their supersession links intact.
  `[V]` The existing design never deletes or overwrites; hiding them would
  misrepresent institutional history. Consumers must respect `supersededById`.
- `confidence` is `[V]` a real corroboration-count-derived float, recomputed at
  write time. It is not a probability and must not be presented as one.
- **Last-validation time: NOT CURRENTLY IMPLEMENTED.** No such field exists on
  `InstitutionalMemoryEntry` `[V]`. This contract does not invent one. Consumers
  must treat `createdAt`/`simDay` as the only temporal anchors.
- `relevance_pct` is deliberately **excluded**: `[V]` it is recomputed fresh per
  request against the *reader's* context (`institutional_memory.py:38-44`), so
  exporting it across a boundary would export a number whose meaning depends on
  a caller TradeTown no longer controls.

**Ordering** `[P]`: `simDay` descending, then `confidence` descending, then `id`
ascending.

**Errors:** as §7.3.

---

### 7.5 `tt_list_prior_findings`

| Property | Value |
|---|---|
| Canonical name | `tt_list_prior_findings` |
| Version | `v0` |
| Purpose | Return `tt-scout`'s **own** historical findings and their recorded outcomes, for continuity and calibration |
| Authority owner | TradeTown |
| Class | Read-only |
| Rate limit | 10 calls/mission, 5 calls/minute `[P]` |

**Input schema**

| Field | Type | Req | Rules |
|---|---|---|---|
| `missionId` | string | yes | Bound mission |
| `limit` | integer | no | 1–25, default 10 `[P]` |
| `sinceSimMinutes` | integer | no | ≥ 0 |
| `cursor` | string | no | Opaque cursor |

There is deliberately **no** `agentId` parameter. Scope is derived from the
credential, never from a caller-supplied identity. A parameter that could name
another agent is a parameter that will eventually be used to name another agent.

**Output schema**

```
{
  contractVersion: "v0",
  simulationContext: "paper_simulated",
  findings: [ {
    id,
    externalAgentId,            // always the caller's own
    missionId,
    producedAtSimMinutes,
    producedAt,                 // ISO-8601
    claim,                      // the finding's single claim string
    confidence,                 // "high" | "medium" | "low"
    evidenceReferences: [id],   // AIEvidenceItem ids [V]
    status,                     // AIReasoningStatus [V] schemas.py:13605
    outcomeStatus,              // "pending" | "evaluated" | "not_evaluated"
    evaluationResult | null,    // present only when outcomeStatus=="evaluated"
    dataProvenance,
    schemaVersion
  } ],
  resultCount, nextCursor | null, retrievedAt
}
```

**Explicitly NOT returned:**

- The full reasoning body / deliberation of any prior finding. Continuity needs
  the claim and its outcome; replaying prior reasoning produces anchoring, which
  defeats the purpose of an independent second look.
- Any other agent's findings, reasoning, or opinions — including in-game
  employees'. `[V]` `AIReasoningResult` records exist for `researcher` and
  `devils_advocate` roles; none of them are reachable through this tool.
- Any field of `AIReasoningResult` not listed above.

**`evaluationResult`: NOT CURRENTLY IMPLEMENTED for external agents.** Outcome
evaluation systems exist `[V]` (`prediction_tracking.py`,
`performance_attribution.py`, `evaluation_simulator.py`) but none is verified as
wired to an external-agent finding, because no such finding type exists yet. In
v0 the field is always `null` and `outcomeStatus` is always `"not_evaluated"`.
Wiring it is a later milestone and must reuse those systems, not a new one.

**Ordering** `[P]`: `producedAtSimMinutes` descending, then `id` ascending.

**Errors:** as §7.3.

---

## 8. Mission contract

`[P]` **NOT CURRENTLY IMPLEMENTED.** No mission concept exists in the repository
`[V]`. This section defines the contract only.

```
Mission {
  contractVersion:              "v0"
  missionId:                    string   // ^[A-Za-z0-9_-]{1,128}$, correlation key
  externalAgentId:              string   // "tt-scout"; NOT an AgentId  (Decision D-1)
  objective:                    string   // 1..2000 chars, plain text, DATA not instruction
  requestedOutputType:          "scout_finding"      // only value in v0

  // Scope
  topicScope:                   string[] // non-empty; closed list
  marketUniverse:               string[] // symbols; may be empty if the mission
                                         // needs no market data
  allowedTools:                 string[] // subset of the five; enforced server-side

  // Time and evidence boundary
  evidencePacketId:             string | null  // an existing AIEvidencePacket id [V]
  knowledgeCutoffSimMinutes:    integer        // MUST equal the packet's own cutoff
                                               // when evidencePacketId is present [V]
  dataFreshnessMaxAgeSimMinutes: integer       // staleness threshold for §7.2
  createdAtSimMinutes:          integer
  createdAt:                    string   // ISO-8601 UTC
  expiresAt:                    string   // ISO-8601 UTC; hard stop

  // Budget (see §15)
  maxToolCalls:                 integer
  maxMissionLifetimeSeconds:    integer

  // Context
  simulationContext:            "paper_simulated"    // only honest value [V]
  dataProvenanceSummary:        string[]             // e.g. ["market data is SIMULATED"]

  prohibitedActions:            string[]             // closed list, see §14
}
```

**Binding rules**

1. `knowledgeCutoffSimMinutes` is the single anti-lookahead boundary. When
   `evidencePacketId` is present it MUST be copied from that packet, never
   independently computed. `[V]` `AIEvidencePacket.knowledge_cutoff_sim_minutes`
   is already "the hard anti-lookahead boundary" (`schemas.py:13664-13668`), and
   the repository has a history of hindsight-leak fixes at exactly this seam
   (commits `9e59f8f`, `a21b17c`, `6691048`) — this contract must not open a new one.
2. `dataProvenanceSummary` MUST disclose that market data is simulated, reusing
   `[V]` the `known_limitations` discipline of `AIEvidencePacket`.
3. A mission whose `expiresAt` has passed is unusable: every tool returns
   `EXPIRED` (410) and no data.
4. `missionId` is the **correlation key** across every future system: tool calls,
   audit rows, findings, and evaluation records all carry it.

---

## 9. ScoutFinding contract

**Submission is NOT part of v0. No submit tool exists in this contract.** This
section fixes the shape now so that Milestone 2's read-only server and a later
submission milestone cannot drift.

### 9.1 Duplication ruling

`AIReasoningResult` `[V]` already covers most of this concept: persisted,
schema-validated, citation-validated, packet-linked, honest about failure.
The ruling is **option D at the wire, option A at rest**:

- **At the wire:** `ScoutFinding` is a boundary DTO. It exists so that the
  external agent's output can be validated *before* it is allowed to become a
  TradeTown record.
- **At rest:** a validated `ScoutFinding` is persisted as an `AIReasoningResult`
  with `role = "scout_market_research"` (Decision D-2) and an
  `externalAgentId`. **No second reasoning-result store is created.**

### 9.2 Shape

```
ScoutFinding {
  schemaVersion:      "v0"
  missionId:          string        // must match the credential's bound mission
  externalAgentId:    string        // "tt-scout"; server overwrites from credential
  producedAt:         string        // ISO-8601 UTC
  producedAtSimMinutes: integer     // <= mission knowledgeCutoffSimMinutes

  claim:              string        // 1..500 chars, ONE falsifiable statement
  confidence:         "high" | "medium" | "low"   // reuses ResearchCouncilFinding [V]
  confidenceBasis:    string        // 1..500 chars; why, in evidence terms

  observations:       [ { evidenceItemId, assertion } ]   // 1..50
  reasoning:          [ string ]    // 1..20 ordered steps, each <=500 chars
  disconfirming:      [ { evidenceItemId, assertion } ]   // 0..50, see rule 5
  disconfirmingSearchStatement: string   // required; see rule 5
  scopeLimits:        [ string ]    // 1..10; what this does NOT claim
  requestedAction:    "research_more" | "no_action"       // v0: these two only
}
```

### 9.3 Validation rules — all server-side, all mandatory

1. **Every `evidenceItemId` must be a real id in the mission's
   `AIEvidencePacket`.** `[V]` This reuses the existing, working citation
   validator (`ai_reasoning.py:283`), which collects unknown ids into
   `invalidCitations` and sets `citationValidationPassed = false`. A finding with
   any invalid citation is **rejected**, not stored with a warning flag.
2. **No free-form prose becomes a business instruction.** Every string field is
   stored as data and rendered as data. No field is parsed for commands,
   evaluated, templated into a query, or matched against an action vocabulary.
3. **`producedAtSimMinutes` must not exceed the mission cutoff.** Violation is
   rejection. This is the same boundary the repository has already had to defend
   `[V]` (commit `a21b17c`, "anchor evidence cutoff to discovery time").
4. **`claim` must be a single statement.** Enforced by length and by rejecting
   newline characters. A finding that wants to say two things files two findings.
5. **Disconfirming evidence is structurally required.** `disconfirming` may be
   empty **only** when `disconfirmingSearchStatement` explicitly states what was
   searched and that nothing was found. An empty array with an empty statement is
   rejected. This is the one place the contract deliberately spends bytes to
   fight motivated reasoning.
6. **`requestedAction` in v0 is non-actionable by construction.** The enum
   contains only `research_more` and `no_action`. `[V]` The existing
   `AIRecommendation` literal contains `buy`/`sell`/`wait` — those values are
   **deliberately not reused here**, because reusing that enum would put
   actionable values one schema edit away from an external agent's reach.
7. **Rejected findings are not partially stored.** All-or-nothing.
8. A stored finding enters TradeTown in a **pending, advisory** state, exactly as
   `[V]` `ResearchCouncilReport` is "advisory only, never wired into
   `classify_candidacy()`/Champion-Challenger/Certification/Hall-of-Fame"
   (`schemas.py:15121-15128`). That precedent is the model.

### 9.4 Prohibited request values

`requestedAction` may never accept, and the server must reject at the schema
layer: any order, trade, size, execution, risk override, Gatekeeper override,
kill-switch change, paper/live change, strategy deployment, or promotion.

---

## 10. Authentication contract

**NOT CURRENTLY IMPLEMENTED. TradeTown has no inbound authentication of any
kind** `[V]` `docs/API.md:4`. This section specifies intent only. **No credential
is created by this milestone.**

### 10.1 Direction

```
TradeTown  ──issues──▶  narrow credential  ──held by──▶  tt-scout on OpenClaw
```

Never the inverse. TradeTown must never store, request, or be configured with an
OpenClaw gateway token, password, or operator credential. `[D]` An OpenClaw
gateway bearer credential is documented as equivalent to full operator access and
cannot be narrowed by the caller
(`docs/gateway/openai-http-api.md:39-51`, `docs/gateway/tools-invoke-http-api.md:33-49`).

### 10.2 Required properties `[P]`

| Property | Requirement |
|---|---|
| Unique identity | One credential ↔ one `externalAgentId`. Never shared, never reused across agents. |
| Least privilege | Grants exactly the tools in the mission's `allowedTools`. Default deny. |
| Tool-level scope | Authorization is checked per tool per call, not once at connect. |
| Mission binding | Bound to one `missionId`. A credential cannot read another mission's data. |
| Expiration | Expires at or before the mission's `expiresAt`. |
| Rotation | Rotatable without downtime; old credential invalid immediately on rotation. |
| Revocation | Single-call revocation, effective on the next request, no cache window. |
| Rate limiting | Enforced per credential (§15). |
| Cost limiting | `maxToolCalls` enforced per credential per mission. |
| Audit identity | Every audit row carries `credentialId` — a stable, non-secret reference. The credential value itself is never logged, never returned, never persisted in plaintext. This matches `[V]` the codebase's existing secrets discipline (`ai_provider.py:22-27`, `market_data.py:778` redacts keys from error strings). |
| Environment separation | Credentials are per-environment. A dev credential must never authenticate against another environment's data. |

### 10.3 OAuth

`[D]` OpenClaw's MCP client supports `auth: "oauth"` with
`openclaw mcp login <name>` (`docs/tools/mcp.md:125-131`) and supports secret
storage outside config literals (`mcp.md:94`).

**Protocol support is not implementation.** TradeTown has no OAuth
authorization server, no token endpoint, and no client registry `[V]`. Choosing
OAuth means building all three. A simpler bearer credential issued and verified
by TradeTown satisfies every property in §10.2 and is the recommended v0 path
`[P]`; the decision belongs to Milestone 2 and is recorded here as open only
because both options genuinely satisfy the contract.

---

## 11. Audit contract

**The authoritative compliance record is TradeTown's.** OpenClaw's ledger is
correlated telemetry and must never be treated as the authoritative record —
`[D]` its own documentation states "Absence of a row proves nothing" and "It is
not a lossless compliance archive" (`docs/gateway/audit.md:427-441`), with a
30-day / 100,000-row bound (`audit.md:445-449`).

### 11.1 Required fields per MCP call `[P]`

| Field | Required | Notes |
|---|---|---|
| `eventId` | yes | Stable unique id |
| `timestamp` | yes | ISO-8601 UTC, wall clock |
| `simMinutes` | yes | Simulated clock at handling time |
| `externalAgentId` | yes | Never an `AgentId` (Decision D-1) |
| `credentialId` | yes | Reference only. **Never the credential value.** |
| `missionId` | yes | The correlation key |
| `tool` | yes | Canonical tool name |
| `contractVersion` | yes | `"v0"` |
| `requestMetadata` | yes | Field names and value **shapes/sizes** only — never full free-text argument bodies |
| `scopeEvaluated` | yes | Which scope checks ran and their verdicts |
| `resultStatus` | yes | `ok` / `denied` / `error` |
| `errorCode` | when not ok | From §12 |
| `resultCount` | when applicable | |
| `dataProvenance` | yes | Provenance of what was served |
| `latencyMs` | yes | Server-side handling time |
| `requestDigest` | yes | SHA-256 of the canonicalized request |
| `resultDigest` | yes | SHA-256 of the serialized result |

Digests give tamper-evidence and reproducibility without storing potentially
large or sensitive bodies.

### 11.2 Rules

1. The audit row is written **before** the response is returned. A failed audit
   write fails the call closed (§12).
2. Agent-access rows go to a **separate infrastructure log**, not to
   `AuditEntry` `[V]`. Justification: `AuditEntry` is a CEO-facing, in-world,
   department-scoped, `sim_day`-stamped narrative record
   (`schemas.py:10843-10858`); machine-access rows have a different actor, reader,
   retention need, and volume profile. This is duplication class **D**, not **E**.
3. Audit rows are **append-only**. No update or delete path.
4. Retention is TradeTown's decision and must exceed OpenClaw's 30-day window
   `[D]`, since TradeTown's record is the authoritative one.
5. Audit rows are infrastructure telemetry, **not** business state (§7.0). They
   record that a read happened; they change nothing a trading decision reads.

---

## 12. Failure semantics

All five tools fail **closed**. A failure never produces a partial business
artifact, never substitutes synthetic data, and never degrades silently.

### 12.1 Error codes

| Code | HTTP | Retryable | Meaning |
|---|---|---|---|
| `INVALID_ARGUMENT` | 400 | no | Schema/type/range violation |
| `INVALID_CURSOR` | 400 | no | Malformed or expired pagination cursor |
| `UNAUTHENTICATED` | 401 | no | Missing/invalid credential |
| `FORBIDDEN` | 403 | no | Valid credential, tool or mission not granted |
| `NOT_FOUND` | 404 | no | Mission does not exist |
| `EXPIRED` | 410 | no | Mission past `expiresAt` |
| `RESULT_TOO_LARGE` | 413 | no | Would exceed 256 KB; never truncated silently |
| `OUT_OF_SCOPE` | 422 | no | Symbol/topic outside the mission's declared scope |
| `RATE_LIMITED` | 429 | yes, after `retryAfterSeconds` | Budget exceeded |
| `UNAVAILABLE` | 503 | yes | Upstream data source unavailable |
| `TIMEOUT` | 504 | yes | Exceeded the 10s server-side budget |

`[V]` The repository's existing convention is FastAPI `HTTPException` with a
`detail` string and `400` for invalid arguments (`routers/market.py:72-82`).
This contract keeps `400` for that class and adds the codes above; the MCP
server MUST return a machine-readable `errorCode` alongside FastAPI's `detail`,
because a prose `detail` is not a contract.

### 12.2 Specific behaviors

| Situation | Behavior |
|---|---|
| MCP transport unavailable | No partial artifact. The mission does not submit anything. |
| Invalid mission | `INVALID_ARGUMENT` or `NOT_FOUND`; no data |
| Expired mission | `EXPIRED`; no data |
| Out-of-scope symbol/topic | `OUT_OF_SCOPE`; existence of the out-of-scope record is not disclosed |
| Unsupported instrument | `OUT_OF_SCOPE`; never a nearest-match substitution |
| Unsupported timeframe | `INVALID_ARGUMENT`; `[V]` never silently substituted (`market_data.py:143-147`) |
| Stale data | Returned with `"stale": true` and measured age — never silently served as fresh, never replaced |
| Data genuinely unavailable | `UNAVAILABLE` with a specific, **secret-free** reason. `[V]` Mirrors `ExternalMarketDataProvider`'s "NEVER A SILENT MOCK FALLBACK" rule and its key redaction (`market_data.py:697-700, 778`) |
| Oversized request or result | `INVALID_ARGUMENT` / `RESULT_TOO_LARGE` |
| Unauthorized tool | `FORBIDDEN` |
| Malformed agent output (future submit) | Rejected whole; nothing stored |
| Audit write failure | Call fails closed with `UNAVAILABLE`; no data returned |

### 12.3 / 12.4 Approval-state dependency

Both `tt_search_approved_research` and `tt_read_institutional_memory` depend on
an approval classification that **does not exist** `[V]`. Until it is built, the
only correct behavior is to return an empty, successful result set. Returning
unapproved records because nothing is marked unapproved would be a fail-open
default and is explicitly forbidden by this contract.

---

## 13. Security and prompt-injection rules

1. **Tool inputs are data, never instructions.** No agent-supplied string is
   parsed as a command, evaluated, executed, templated into SQL, or matched
   against an action vocabulary. `query` and `objective` are opaque text.
2. **The server treats agent output as untrusted input.** Validation is
   server-side and total. `[V]` This is already the codebase's stated posture:
   "nothing here is ever populated by blindly trusting whatever JSON the model
   returned" (`schemas.py:13678-13684`).
3. **Retrieved content never gains authority by being retrieved.** Market,
   research, and memory content carries no instruction weight regardless of what
   it says. A memory entry whose text reads like a command is still just text.
4. **No path from agent input to arbitrary execution.** No tool exposes SQL, a
   query language, a path, a filename, a shell fragment, an internal API name, or
   any identifier that selects code rather than data.
5. **Parameterized access only.** Every identifier from the agent is validated
   against a closed set or a strict pattern before it reaches persistence.
6. **Anti-anchoring is a security property, not a nicety.** `tt_list_prior_findings`
   withholds prior reasoning bodies and all other agents' output (§7.5) so that a
   future second agent cannot be steered by a first agent's compromised output.
   `originatingAgent` is withheld from memory reads for the same reason.
7. **Errors are secret-free.** No error message ever contains a credential, key,
   internal path, stack trace, or SQL. `[V]` Existing precedent:
   `market_data.py:778` redacts the API key from transport error strings.
8. **Response size and shape are bounded** so that a compromised upstream cannot
   flood the agent's context.

---

## 14. Prohibited surfaces

The Scout credential and tool boundary MUST NEVER expose any of the following.
This list is closed for v0; additions require a contract version bump.

**Governance and risk**
Gatekeeper decisions · Gatekeeper configuration `[V]` `gatekeeper.py` ·
Risk Contract state `[V]` `risk_contract.py` · risk limits · dynamic risk
scaling · `risk_engine.py` · `portfolio_risk.py` · `behavioral_risk.py` ·
`opportunity_gatekeeper.py` · `constitution.py` · `compliance_incidents.py`

**Trading**
position sizing `[V]` `position_sizing.py` · order creation, modification,
cancellation · execution · fills · positions · `portfolio.py` ·
`trade_lifecycle.py` · `broker.py` · `trades` router · account balances `[V]`
`accounts.py` · treasury `[V]` `routers/treasury.py`

**Safety controls**
kill switch · emergency stop `[V]` `routers/emergency.py` · circuit-breaker
tiers `[V]` `trading_modes.py` · trading restrictions `[V]`
`routers/trading_restrictions.py` · paper/live mode switching (**no live mode
exists** `[V]`; the prohibition exists so that introducing one cannot silently
become agent-reachable)

**Credentials and configuration**
broker credentials · broker OAuth · any API secret ·
`TRADETOWN_AI_PROVIDER_API_KEY` · `EXTERNAL_MARKET_DATA_API_KEY` ·
environment variables · `config.py` · agent configuration

**Strategy lifecycle**
strategy deployment `[V]` `strategy_engine.py`, `strategy_compiler.py` ·
champion promotion `[V]` `champion_challenger.py` · Hall of Fame ·
certification · autonomous deployment · `strategy_tournament.py`

**System**
system administration · OpenClaw gateway administration · filesystem ·
shell / exec / process control · arbitrary database access · arbitrary SQL ·
arbitrary internal API invocation · save/load and run management `[V]`
`persistence.py`, `routers/save.py`, `routers/runs.py` · sandbox control `[V]`
`routers/sandbox.py`

**Agent boundary**
memory promotion (`record_institutional_memory` and every `promote_*` function
`[V]` `institutional_memory.py`) · cross-agent session messaging · another
agent's private reasoning or deliberation · in-game employee state mutation ·
`AgentId` impersonation

**Discovered during this audit and added to the list**

- `routers/sandbox.py` (1477 lines — the largest router; a sandbox is an
  execution surface by definition)
- `routers/runs.py` / `routers/save.py` — save-slot and run switching is
  state-destructive; `[V]` `main.py:24-45` documents prior real data loss from
  stale-checkout/restart scenarios
- `black_box.py` / `routers/black_box.py` — internal decision recorder
- `routers/player_vs_ai.py` — player-facing game control
- `nexus.py` — the central tick orchestrator; not a read surface

---

## 15. Rate and budget limits

All values are `[P]` PROPOSED CONTRACT DECISIONS. TradeTown has **no existing
HTTP rate limiting** `[V]`, so no repository-derived numbers exist to inherit.
Each value below states its rationale.

| Limit | Value | Rationale |
|---|---|---|
| Calls per mission (total) | **60** | Enough for ~10 symbols at 3 reads each plus research and memory passes, with headroom. Small enough that a looping agent is stopped within one mission rather than across many. |
| Calls per minute (per credential) | **20** | A real reasoning loop pauses to think; >20/min indicates a loop, not analysis. |
| `tt_get_mission` calls | **5**, free | Idempotent and tiny; excluded from budget so budget exhaustion never hides the mission's own prohibitions from the agent. |
| Max result size | **256 KB** serialized | Bounds context flooding; comfortably fits 500 candles. |
| Max candles per call | **500** | `[V]` `MarketDataProvider.get_candles` takes an explicit `limit` with no documented ceiling; 500 bars is a full chart window and bounds response size. |
| Max historical window | Bounded by `knowledgeCutoffSimMinutes`, not by a fixed span | The anti-lookahead boundary is the real constraint `[V]`; a second independent window limit would be a competing source of truth. |
| Max research results | **50** per call, 20 default | Matches the memory limit for symmetry; forces the agent to narrow rather than dredge. |
| Max memory results | **50** per call, 20 default | Same. |
| Max prior findings | **25** per call, 10 default | Calibration needs recent history, not the full archive. |
| Mission lifetime | **3600 s** | One bounded work session. Prevents an abandoned mission from holding a live credential indefinitely. |
| Per-call timeout | **10 s** | `[V]` The AI provider's own request timeout is 30 s (`ai_provider.py:48`); a pure data read should be far below that, and 10 s leaves room for retry inside the agent's own budget. |
| Reasoning/token budget | **Not enforced at this boundary** | Deliberate. Model-token accounting belongs to the OpenClaw runtime; importing it into TradeTown's authority model would make TradeTown depend on a metric it cannot verify. TradeTown enforces call count, size, and time — all of which it can measure. |

---

## 16. Versioning

- **Contract name:** TradeTown Scout Read-Only Tool Contract
- **Version:** `v0`
- Every response carries `contractVersion`. Every record-shaped payload carries
  `schemaVersion`.
- **Breaking changes increment the major version** (`v0` → `v1`): removing a
  field, narrowing a type, changing an ordering rule, changing an error code's
  meaning, tightening a limit, or adding a required input field.
- **Additive optional fields are non-breaking** and must never change the meaning
  of an existing field. A consumer that ignores an unknown field must remain
  correct.
- Enumerations are closed. Adding a value is **breaking** for any consumer that
  exhaustively matches — including `AIReasoningRole` (Decision D-2).
- The response-field allowlist in §7.4 is closed; extending it is a version change.
- Server and agent must agree on the major version. A version mismatch is
  `INVALID_ARGUMENT`, never a best-effort attempt.

---

## 17. Explicit non-goals

**This milestone does NOT build, and this contract does NOT authorize:**

- an MCP server · an MCP client configuration · any MCP dependency
- an OpenClaw agent, agent config, or tool policy
- any credential, key, token, or authentication implementation
- Tailscale, any network change, any port exposure, any firewall change
- web access, `web_search`, `web_fetch`, or any external-content ingestion
- any submit or write tool
- analyst-opinion submission · department-opinion submission
- automated scheduling, cron, or automations
- memory promotion of any kind
- collaboration orchestration or multi-agent coordination
- a second agent
- live trading, live money, or a live mode
- any change to paper-trading behavior
- strategy deployment or autonomous strategy promotion
- any change to Gatekeeper, Risk Contract, execution, position sizing, or
  existing proposal generation
- any change to `AIProvider` behavior
- any production code change whatsoever

### Recorded decisions

**Web access (Part 17 of the milestone brief):** v0 `tt-scout` has **no**
`web_search` / `web_fetch` capability. Reason: the first milestone proves the
TradeTown trust boundary before adding untrusted external-content ingestion. Web
access is a separate future security milestone with its own review.

**Session and memory:** one mission = one bounded mission session; no eternal
mission context. OpenClaw private memory is scratch and continuity only.
TradeTown institutional memory is authoritative. Scout cannot promote memory.
Specification only — none of this is implemented.

---

## 18. Open questions

Two, both genuinely blocked on decisions that cannot be derived from the
repository:

1. **Is `tt-scout` the in-game `scout` employee's reasoning brain, or a separate
   external analyst?** (Decision D-1.) v0 assumes separate. This is a product
   decision about TradeTown's fiction. Deferring it costs nothing now; deciding
   it wrongly later requires a data migration.
2. **Bearer credential or OAuth?** (§10.3.) Both satisfy every property in
   §10.2. OAuth requires building an authorization server, token endpoint, and
   client registry that do not exist `[V]`. Recommended: bearer for v0. The
   decision belongs to Milestone 2.

No other question was left open. Every other value in this document is either
verified, cited, or a labeled `[P]` decision with a stated rationale.

---

## 19. Exit criteria

| # | Criterion | Status |
|---|---|---|
| 1 | One versioned contract document exists | ✅ this file |
| 2 | Exactly five read-only tools specified | ✅ §7.1–7.5 |
| 3 | Every tool has complete input/output/error semantics | ✅ §7, §12 |
| 4 | No tool can mutate TradeTown business state | ✅ §7.0, §12, §14 |
| 5 | Mission contract defined | ✅ §8 |
| 6 | ScoutFinding contract defined | ✅ §9 |
| 7 | Authentication intent defined, not implemented | ✅ §10 |
| 8 | Authoritative TradeTown audit contract defined | ✅ §11 |
| 9 | Prohibited surfaces include governance, Gatekeeper, risk, sizing, execution, kill switch, paper/live | ✅ §14 |
| 10 | No web access | ✅ §17 |
| 11 | No credentials exist | ✅ none created |
| 12 | No OpenClaw configuration changed | ✅ |
| 13 | No networking changed | ✅ |
| 14 | No production trading behavior changed | ✅ |
| 15 | No duplicate subsystem created | ✅ §5 |
| 16 | All repository-derived claims verified | ✅ §4, file:line throughout |
| 17 | All proposals labeled `[P]` | ✅ |
| 18 | Implementable without inventing missing semantics | ✅ subject to §18 |

---

## 20. Next milestone

> ### MILESTONE 2 — TRADETOWN MCP SERVER, READ-ONLY IMPLEMENTATION
>
> Implement the five tools specified in this document as a read-only MCP server
> inside TradeTown, plus the four capabilities this audit found missing:
> inbound authentication (§10), the approval classification (§12.3/12.4), the
> mission record (§8), and the agent-access audit log (§11).
>
> **Not in Milestone 2:** submit tools, web access, a second agent, networking
> changes, OpenClaw agent creation, live trading.
>
> **Do not begin Milestone 2 from this document alone** — resolve the two open
> questions in §18 first.

---

## Appendix A — Verification index

Every `[V]` claim in this document resolves to one of:

`backend/app/main.py` · `db.py` · `config.py` · `ai_provider.py` ·
`ai_reasoning.py` · `market_data.py` · `institutional_memory.py` ·
`audit_log.py` · `trading_modes.py` · `research_loop.py` · `schemas.py` ·
`routers/market.py` · `docs/API.md` · `docs/AI_AGENT_BIBLE.md` ·
repository-wide grep at HEAD `39bfe9e`.

`[D]` claims resolve to OpenClaw documentation at
`/usr/lib/node_modules/openclaw/docs/` (version 2026.9.1):
`gateway/openai-http-api.md` · `gateway/tools-invoke-http-api.md` ·
`gateway/audit.md` · `tools/mcp.md`.
