"""Company Knowledge Graph endpoint (v0.7 Feature 25.5). See
app/knowledge_graph.py's module docstring for what's real vs. explicitly
not built.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.agents import all_agent_ids
from app.knowledge_graph import build_knowledge_graph
from app.schemas import KnowledgeGraph
from app.state import game_state

router = APIRouter(prefix="/api", tags=["knowledge-graph"])


@router.get("/knowledge-graph", response_model=KnowledgeGraph)
async def knowledge_graph() -> KnowledgeGraph:
    """Read-only and computed fresh on every call (see
    app/knowledge_graph.py's module docstring for why it's never
    persisted). No game-state lock needed — nothing here mutates the
    save, only reads the current snapshot."""
    state = await game_state.snapshot()
    return build_knowledge_graph(
        agent_ids=all_agent_ids(),
        research=state.research,
        academy_completed_projects=state.academy_completed_projects,
        agent_knowledge=state.agent_knowledge,
        executive_reviews=state.executive_reviews,
        coach_reports=state.coach_reports,
        hall_of_fame=state.hall_of_fame,
    )
