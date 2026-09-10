"""Covers app/routers/mcp_read.py — TradeTown Read-Only MCP Boundary 1.0.

The properties under test are security properties, not conveniences:

  - approval is FAIL-CLOSED (an un-seeded save yields nothing, never
    everything);
  - the mission knowledge cutoff is enforced, and enforced against the
    honest anchor each record actually has;
  - the response field allowlist is CLOSED (originatingAgent and
    relevancePct never leave the building);
  - no endpoint mutates the save;
  - agent-findings never projects in-game reasoning results.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.routers import mcp_read
from app.schemas import InstitutionalMemoryEntry, ResearchItem
from app.state import game_state


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _research(item_id: str, *, approved: bool, approved_sim: int | None, title: str = "Scanning news") -> ResearchItem:
    return ResearchItem(
        id=item_id,
        title=title,
        symbol="AAPL",
        category="company",
        priority="normal",
        status="in_progress",
        assignedAgent="scout",
        summary="a summary",
        confidence=0.5,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
        approvedForAgentRead=approved,
        approvedForAgentReadAt=_now_iso() if approved else None,
        approvedForAgentReadAtSimMinutes=approved_sim,
        approvedForAgentReadBy="test" if approved else None,
    )


def _memory(
    entry_id: str, *, approved: bool, approved_sim: int | None, sim_day: int
) -> InstitutionalMemoryEntry:
    return InstitutionalMemoryEntry(
        id=entry_id,
        source="risk_event",
        createdAt=_now_iso(),
        simDay=sim_day,
        originatingAgent="sentinel",
        eventRef="evt-1",
        observation="something happened",
        confidence=0.7,
        provenance="promoted from evt-1",
        relevancePct=42.0,
        approvedForAgentRead=approved,
        approvedForAgentReadAt=_now_iso() if approved else None,
        approvedForAgentReadAtSimMinutes=approved_sim,
        approvedForAgentReadBy="test" if approved else None,
    )


def _seed(research: list[ResearchItem], memory: list[InstitutionalMemoryEntry]) -> None:
    async def _apply() -> None:
        state = await game_state.snapshot()
        state.research = research
        state.institutional_memory = memory

    asyncio.run(_apply())


# --------------------------------------------------------------- fail-closed


def test_approval_is_fail_closed_when_nothing_is_seeded() -> None:
    """The single most important test in this file. With no approval flags
    set anywhere, the honest answer is an EMPTY result set — never "all
    research, because none is marked unapproved"."""
    _seed(
        research=[_research("r-1", approved=False, approved_sim=None)],
        memory=[_memory("m-1", approved=False, approved_sim=None, sim_day=1)],
    )
    client = TestClient(app)

    research = client.get("/api/mcp-read/approved-research", params={"knowledgeCutoffSimMinutes": 10_000_000})
    memory = client.get("/api/mcp-read/approved-memory", params={"knowledgeCutoffSimMinutes": 10_000_000})

    assert research.status_code == 200
    assert research.json()["results"] == []
    assert research.json()["resultCount"] == 0
    assert memory.status_code == 200
    assert memory.json()["results"] == []


def test_approved_without_sim_anchor_is_still_withheld() -> None:
    """approvedForAgentRead alone is not enough: without an approval
    sim-minute there is no anchor to prove cutoff containment, so the record
    stays withheld rather than being served unprovable."""
    _seed(research=[_research("r-1", approved=True, approved_sim=None)], memory=[])
    client = TestClient(app)
    response = client.get("/api/mcp-read/approved-research", params={"knowledgeCutoffSimMinutes": 10_000_000})
    assert response.json()["results"] == []


# -------------------------------------------------------------------- cutoff


def test_research_cutoff_excludes_approvals_after_the_cutoff() -> None:
    _seed(
        research=[
            _research("r-early", approved=True, approved_sim=100),
            _research("r-late", approved=True, approved_sim=900),
        ],
        memory=[],
    )
    client = TestClient(app)
    response = client.get("/api/mcp-read/approved-research", params={"knowledgeCutoffSimMinutes": 500})
    ids = [r["id"] for r in response.json()["results"]]
    assert ids == ["r-early"]


def test_research_cutoff_boundary_is_inclusive() -> None:
    _seed(research=[_research("r-exact", approved=True, approved_sim=500)], memory=[])
    client = TestClient(app)
    response = client.get("/api/mcp-read/approved-research", params={"knowledgeCutoffSimMinutes": 500})
    assert [r["id"] for r in response.json()["results"]] == ["r-exact"]


def test_memory_cutoff_enforces_both_sim_day_and_approval_minute() -> None:
    """sim_day 10 == sim-minute 14400, which is after a 5000-minute cutoff,
    so the record is withheld even though its approval minute passes."""
    _seed(
        research=[],
        memory=[
            _memory("m-old", approved=True, approved_sim=100, sim_day=1),
            _memory("m-future-day", approved=True, approved_sim=100, sim_day=10),
        ],
    )
    client = TestClient(app)
    response = client.get("/api/mcp-read/approved-memory", params={"knowledgeCutoffSimMinutes": 5000})
    assert [r["id"] for r in response.json()["results"]] == ["m-old"]


def test_cutoff_enforcement_is_disclosed_honestly() -> None:
    _seed(research=[], memory=[])
    client = TestClient(app)
    research = client.get("/api/mcp-read/approved-research", params={"knowledgeCutoffSimMinutes": 1})
    memory = client.get("/api/mcp-read/approved-memory", params={"knowledgeCutoffSimMinutes": 1})
    assert "approval_sim_minutes_only" in research.json()["cutoffEnforcement"]
    assert "sim_day_and_approval_sim_minutes" in memory.json()["cutoffEnforcement"]


def test_negative_cutoff_is_rejected() -> None:
    client = TestClient(app)
    assert client.get("/api/mcp-read/approved-research", params={"knowledgeCutoffSimMinutes": -1}).status_code == 400


# ----------------------------------------------------------------- allowlist


def test_memory_projection_withholds_originating_agent_and_relevance() -> None:
    _seed(research=[], memory=[_memory("m-1", approved=True, approved_sim=10, sim_day=1)])
    client = TestClient(app)
    entry = client.get("/api/mcp-read/approved-memory", params={"knowledgeCutoffSimMinutes": 10_000_000}).json()[
        "results"
    ][0]
    assert "originatingAgent" not in entry
    assert "relevancePct" not in entry
    assert entry["provenance"]
    assert entry["eventRef"] == "evt-1"


def test_nullable_memory_fields_stay_null_rather_than_padded() -> None:
    _seed(research=[], memory=[_memory("m-1", approved=True, approved_sim=10, sim_day=1)])
    client = TestClient(app)
    entry = client.get("/api/mcp-read/approved-memory", params={"knowledgeCutoffSimMinutes": 10_000_000}).json()[
        "results"
    ][0]
    assert entry["interpretation"] is None
    assert entry["lesson"] is None


# ------------------------------------------------------------------ ordering


def test_research_ordering_is_a_deterministic_total_order() -> None:
    same_time = _now_iso()
    items = [_research(f"r-{n}", approved=True, approved_sim=10) for n in ("c", "a", "b")]
    for item in items:
        item.created_at = same_time
    _seed(research=items, memory=[])
    client = TestClient(app)
    first = client.get("/api/mcp-read/approved-research", params={"knowledgeCutoffSimMinutes": 10_000_000}).json()
    second = client.get("/api/mcp-read/approved-research", params={"knowledgeCutoffSimMinutes": 10_000_000}).json()
    ids = [r["id"] for r in first["results"]]
    assert ids == ["r-a", "r-b", "r-c"]  # equal createdAt -> id ascending
    assert ids == [r["id"] for r in second["results"]]


def test_limit_is_bounded_and_truncation_is_disclosed() -> None:
    _seed(research=[_research(f"r-{n}", approved=True, approved_sim=10) for n in range(5)], memory=[])
    client = TestClient(app)
    response = client.get(
        "/api/mcp-read/approved-research", params={"knowledgeCutoffSimMinutes": 10_000_000, "limit": 2}
    )
    assert response.json()["resultCount"] == 2
    assert response.json()["truncated"] is True
    over = client.get(
        "/api/mcp-read/approved-research",
        params={"knowledgeCutoffSimMinutes": 10_000_000, "limit": mcp_read.RESEARCH_MAX_LIMIT + 1},
    )
    assert over.status_code == 422


# ------------------------------------------------------------ agent findings


def test_agent_findings_is_empty_and_never_projects_in_game_reasoning() -> None:
    """Empty is CORRECT here, not unimplemented: projecting this codebase's
    in-game ai_reasoning_results would expose another agent's private
    reasoning to an external agent."""
    client = TestClient(app)
    response = client.get(
        "/api/mcp-read/agent-findings",
        params={"externalAgentId": "tt-scout", "knowledgeCutoffSimMinutes": 10_000_000},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["dataCategory"] == "unavailable"
    assert "no external-agent findings exist" in body["cutoffEnforcement"]


def test_agent_findings_rejects_blank_agent_id() -> None:
    client = TestClient(app)
    response = client.get(
        "/api/mcp-read/agent-findings",
        params={"externalAgentId": "   ", "knowledgeCutoffSimMinutes": 1},
    )
    assert response.status_code == 400


# ------------------------------------------------------------------ envelope


def test_every_response_reports_run_and_paper_simulation_context() -> None:
    _seed(research=[], memory=[])
    client = TestClient(app)
    for path, params in (
        ("/api/mcp-read/approved-research", {"knowledgeCutoffSimMinutes": 1}),
        ("/api/mcp-read/approved-memory", {"knowledgeCutoffSimMinutes": 1}),
        ("/api/mcp-read/agent-findings", {"externalAgentId": "tt-scout", "knowledgeCutoffSimMinutes": 1}),
    ):
        body = client.get(path, params=params).json()
        assert body["contractVersion"] == "v0"
        assert body["simulationContext"] == "paper_simulated"
        assert body["runId"]
        assert body["retrievedAt"]


# ------------------------------------------------------------ mutation-free


def test_reads_do_not_mutate_the_save() -> None:
    research = [_research("r-1", approved=True, approved_sim=10)]
    memory = [_memory("m-1", approved=True, approved_sim=10, sim_day=1)]
    _seed(research=research, memory=memory)

    before = asyncio.run(_snapshot_json())
    client = TestClient(app)
    client.get("/api/mcp-read/approved-research", params={"knowledgeCutoffSimMinutes": 10_000_000})
    client.get("/api/mcp-read/approved-memory", params={"knowledgeCutoffSimMinutes": 10_000_000})
    client.get(
        "/api/mcp-read/agent-findings",
        params={"externalAgentId": "tt-scout", "knowledgeCutoffSimMinutes": 10_000_000},
    )
    after = asyncio.run(_snapshot_json())
    assert before == after


async def _snapshot_json() -> str:
    state = await game_state.snapshot()
    return state.model_dump_json()


def test_router_declares_no_mutating_http_methods() -> None:
    """A structural guarantee: this router has no POST/PUT/PATCH/DELETE
    route, so no future edit can add one without failing this test."""
    methods: set[str] = set()
    for route in mcp_read.router.routes:
        methods |= set(getattr(route, "methods", set()))
    assert methods <= {"GET", "HEAD"}
