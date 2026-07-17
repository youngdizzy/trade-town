# Version History

A version-by-version summary of TradeTown's scope. For the itemized
per-change list (including bug fixes), see [`CHANGELOG.md`](../CHANGELOG.md)
at the repo root; this file is the higher-level "what was each version
about and why" narrative, plus what's intentionally deferred.

## v0.1 — Foundation

One employee (Scout), a small HQ (Lobby + Scout Office + CEO Office +
Brain Room), a live backend simulation driving Scout's daily
schedule/mood/energy/memory, save/load, and Docker Compose deployment with
an nginx reverse proxy. Established the core client/server architecture
(server-authoritative agent state over WebSocket, client-authoritative
player/settings/dialogue) that every later version builds on without
rewriting.

## v0.2 — Multi-agent office

Three more agents (Atlas, Echo, Nova), each with a distinct personality
and daily routine; two new rooms (Meeting Room, Break Room) plus an
upgraded Brain Room ("Mission Control"); a reusable server-authoritative
`Task` system; the NEXUS orchestrator (task assignment, meetings, breaks,
whiteboards, discovery news); a newspaper stand; and an extended save
schema. Generalized the v0.1 single-agent architecture (`ScoutState` →
`Record<AgentId, AgentState>`, `ScoutNPC` → `AgentNPC`) to support an
arbitrary agent roster without a rewrite — a design choice that paid off
directly in v0.3, where adding a fifth agent (Scribe) required zero
Phaser scene changes.

## v0.3 — Intelligence & research

A fifth agent (Scribe, the company historian); a `MarketDataProvider`
interface with a mock adapter (no real market API, no trades — see
`docs/Architecture.md`); a rotating research queue across an 8-symbol
watchlist with per-agent confidence; meetings that now produce real
discussion transcripts and minutes; a searchable `CompanyMemory` log with
a dedicated viewer; and an upgraded Brain Room HUD / newspaper /
whiteboards surfacing all of it. Extended (not replaced) v0.2's `Task`
system with categories, and v0.2's meeting/break `AgentOverride`
mechanism gained a `discussion` field rather than a parallel state
machine.

**Explicitly not in v0.3** (per the brief's STOP CONDITION): paper
trading, brokerage connections, live trading of any kind, or a real
market data API call. "Future trade" flags are a logged note for a human
to consider, never a queued or simulated order.

## What's next for v0.4 (not started, not scoped)

These are candidate directions surfaced by v0.3's design, not commitments
— nothing below has been designed, and per every version's stop
condition, work stops at the end of its own brief:

- **A real `MarketDataProvider` adapter.** The interface and mock
  implementation are already in place (`market_data.py`); the natural
  next step is one real vendor (Polygon, Finnhub, Alpha Vantage, Yahoo
  Finance, or Schwab) behind an API key, still with a mock fallback when
  no key is configured.
- **Model-generated meeting discussion.** v0.3's discussion lines are
  templated flavor text tied to real research state (see
  `discussion.py`); the architecture (participants + their current
  research focus + a transcript slot on `MeetingState`) was deliberately
  built so a future version could swap the template call for a real model
  call without touching the meeting start/end state machine.
- **A `CompanyMemory` REST search endpoint.** `memory.search()` already
  implements the filter contract; it's just not wired to a route yet,
  since the frontend currently filters the WS-synced list client-side.
- **Paper trading**, once there's a real market data connection and a
  clear UX for "propose a trade" vs. "execute a trade" — deliberately
  out of scope for both v0.3 and this list's priority ordering; the
  "future trade candidate" flag exists specifically so this can build on
  real flagged candidates later rather than starting from nothing.
