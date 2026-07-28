import { useEffect, useMemo, useRef, useState } from "react";
import { AGENT_PROFILES } from "@/game/systems/AgentProfiles";
import type { AgentId, KnowledgeEdge, KnowledgeNode, KnowledgeNodeType } from "@/types";
import { useKnowledgeGraph } from "./lib/useKnowledgeGraph";
import { EmptyState, StatusPill, TerminalLabel } from "./ui";

const TYPE_COLORS: Record<KnowledgeNodeType, string> = {
  agent: "#bfe3ff",
  branch: "#3ce28a",
  research: "#4fd8ff",
  academy_project: "#a78bfa",
  executive_review: "#d4af37",
  coach_report: "#ffb443",
  hall_of_fame: "#ff6ec7",
};

const TYPE_LABELS: Record<KnowledgeNodeType, string> = {
  agent: "Agent",
  branch: "Knowledge Branch",
  research: "Research",
  academy_project: "Academy Project",
  executive_review: "Executive Review",
  coach_report: "Coach Report",
  hall_of_fame: "Hall of Fame",
};

const ALL_TYPES = Object.keys(TYPE_COLORS) as KnowledgeNodeType[];
const NODE_RADIUS: Record<KnowledgeNodeType, number> = {
  agent: 15,
  branch: 11,
  research: 9,
  academy_project: 9,
  executive_review: 10,
  coach_report: 9,
  hall_of_fame: 9,
};

function nodeColor(node: KnowledgeNode): string {
  if (node.type === "agent") {
    const agentId = node.id.replace(/^agent-/, "") as AgentId;
    const profile = AGENT_PROFILES[agentId];
    if (profile) return `#${profile.tint.toString(16).padStart(6, "0")}`;
  }
  return TYPE_COLORS[node.type];
}

interface Pos {
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx: number;
  fy: number;
}

/**
 * A bounded, synchronous Fruchterman-Reingold-style force layout with
 * velocity + damping (rather than a temperature-capped direct move) so it
 * settles into an even spread instead of oscillating or collapsing when
 * many nodes share a hub (e.g. ten agents on one Knowledge Branch). Runs
 * once per graph fetch (not every animation frame) — cheap enough at the
 * sizes this codebase actually produces (dozens to a few hundred nodes;
 * verified against a 170-node/285-edge graph from a 1500-tick smoke test),
 * and capping iterations by node count keeps the worst case bounded.
 * Positions are unbounded (no fixed "world" canvas) — the caller fits the
 * view to whatever bounding box the layout actually settles into.
 */
function computeLayout(nodes: KnowledgeNode[], edges: KnowledgeEdge[]): Map<string, Pos> {
  const positions = new Map<string, Pos>();
  const n = nodes.length;
  if (n === 0) return positions;

  const initRadius = 80 + n * 3;
  nodes.forEach((node, i) => {
    const angle = (i / n) * Math.PI * 2;
    positions.set(node.id, { x: Math.cos(angle) * initRadius, y: Math.sin(angle) * initRadius, vx: 0, vy: 0, fx: 0, fy: 0 });
  });

  const k = 60 + Math.sqrt(n) * 6;
  const iterations = n > 220 ? 140 : n > 80 ? 200 : 260;
  const damping = 0.82;
  const maxSpeed = k * 0.6;

  for (let iter = 0; iter < iterations; iter++) {
    for (const p of positions.values()) {
      p.fx = 0;
      p.fy = 0;
    }

    for (let i = 0; i < n; i++) {
      const nodeI = nodes[i];
      const a = nodeI && positions.get(nodeI.id);
      if (!a) continue;
      for (let j = i + 1; j < n; j++) {
        const nodeJ = nodes[j];
        const b = nodeJ && positions.get(nodeJ.id);
        if (!b) continue;
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 0.5) {
          dx = Math.random() - 0.5;
          dy = Math.random() - 0.5;
          dist = 0.5;
        }
        const force = (k * k) / dist;
        const ux = dx / dist;
        const uy = dy / dist;
        a.fx += ux * force;
        a.fy += uy * force;
        b.fx -= ux * force;
        b.fy -= uy * force;
      }
    }

    for (const edge of edges) {
      const a = positions.get(edge.source);
      const b = positions.get(edge.target);
      if (!a || !b) continue;
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 0.5;
      const force = (dist * dist) / k;
      const ux = dx / dist;
      const uy = dy / dist;
      a.fx -= ux * force;
      a.fy -= uy * force;
      b.fx += ux * force;
      b.fy += uy * force;
    }

    // A weak pull toward the origin — keeps weakly-connected subgraphs
    // (e.g. an agent whose only edge is to their own Knowledge Branch)
    // from drifting arbitrarily far under pure repulsion, so the fit-to-
    // bounding-box view doesn't have to zoom out to accommodate an outlier
    // and shrink the well-connected majority down to nothing.
    for (const p of positions.values()) {
      p.fx -= p.x * 0.006;
      p.fy -= p.y * 0.006;
    }

    for (const p of positions.values()) {
      p.vx = (p.vx + p.fx * 0.02) * damping;
      p.vy = (p.vy + p.fy * 0.02) * damping;
      const speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy);
      if (speed > maxSpeed) {
        p.vx = (p.vx / speed) * maxSpeed;
        p.vy = (p.vy / speed) * maxSpeed;
      }
      p.x += p.vx;
      p.y += p.vy;
    }
  }

  return positions;
}

interface ViewTransform {
  panX: number;
  panY: number;
  scale: number;
}

/**
 * v0.7 Feature 25.5 — the Interactive Knowledge Map. Every node/edge here
 * comes straight from GET /api/knowledge-graph (see
 * backend/app/knowledge_graph.py) — a real, checkable relationship between
 * already-persisted records, never a fabricated connection. Node
 * *positions* are the one purely-visual invention: a force-directed layout
 * computed client-side purely to make the real graph legible, not a
 * second source of truth about the data itself.
 */
export function KnowledgeGraphView({ onClose }: { onClose: () => void }) {
  const { graph, loading, error } = useKnowledgeGraph(true);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<ViewTransform>({ panX: 0, panY: 0, scale: 1 });
  const dragRef = useRef<{ x: number; y: number; dragging: boolean; moved: boolean } | null>(null);
  const [visibleTypes, setVisibleTypes] = useState<Set<KnowledgeNodeType>>(new Set(ALL_TYPES));
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const nodes = useMemo(() => graph?.nodes ?? [], [graph]);
  const edges = useMemo(() => graph?.edges ?? [], [graph]);
  const positions = useMemo(() => computeLayout(nodes, edges), [nodes, edges]);

  // Center + fit the initial view once positions are known. Layout
  // positions are unbounded (see computeLayout), so fit against the real
  // bounding box of the resulting positions rather than a fixed canvas.
  useEffect(() => {
    const container = containerRef.current;
    if (!container || positions.size === 0) return;
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    positions.forEach((p) => {
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x);
      maxY = Math.max(maxY, p.y);
    });
    const pad = 60;
    const spanX = Math.max(1, maxX - minX + pad * 2);
    const spanY = Math.max(1, maxY - minY + pad * 2);
    const scale = Math.min(3, Math.min(container.clientWidth / spanX, container.clientHeight / spanY));
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    viewRef.current = {
      scale,
      panX: container.clientWidth / 2 - centerX * scale,
      panY: container.clientHeight / 2 - centerY * scale,
    };
  }, [positions]);

  const nodeById = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  const selectedNode = selectedId ? (nodeById.get(selectedId) ?? null) : null;
  const connectedEdges = useMemo(() => (selectedId ? edges.filter((e) => e.source === selectedId || e.target === selectedId) : []), [edges, selectedId]);
  const connectedIds = useMemo(() => {
    const ids = new Set<string>();
    connectedEdges.forEach((e) => {
      ids.add(e.source);
      ids.add(e.target);
    });
    return ids;
  }, [connectedEdges]);

  const searchLower = search.trim().toLowerCase();
  const visibleNodeIds = useMemo(() => {
    const ids = new Set<string>();
    nodes.forEach((n) => {
      if (visibleTypes.has(n.type)) ids.add(n.id);
    });
    return ids;
  }, [nodes, visibleTypes]);

  const recentDiscoveries = useMemo(
    () =>
      [...nodes]
        .filter((n) => n.timestamp)
        .sort((a, b) => (b.timestamp ?? "").localeCompare(a.timestamp ?? ""))
        .slice(0, 8),
    [nodes],
  );

  // Imperative canvas draw loop — animates edge flow + node glow pulse
  // continuously, but only recomputes when the underlying graph/filters
  // change; pan/zoom/selection are read from refs/closures each frame so
  // dragging never triggers a React re-render.
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    let raf = 0;
    const start = performance.now();

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = container.clientWidth * dpr;
      canvas.height = container.clientHeight * dpr;
      canvas.style.width = `${container.clientWidth}px`;
      canvas.style.height = `${container.clientHeight}px`;
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(container);

    const draw = (now: number) => {
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      const dpr = window.devicePixelRatio || 1;
      const { panX, panY, scale } = viewRef.current;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.fillStyle = "#060a12";
      ctx.fillRect(0, 0, canvas.width / dpr, canvas.height / dpr);
      ctx.setTransform(scale * dpr, 0, 0, scale * dpr, panX * dpr, panY * dpr);

      const t = (now - start) / 1000;
      const pulse = 0.5 + 0.5 * Math.sin(t * 1.6);
      const focusActive = selectedId !== null || searchLower.length > 0;

      // Edges — a slow marching-dash flow to read as "living" wiring.
      edges.forEach((edge) => {
        if (!visibleNodeIds.has(edge.source) || !visibleNodeIds.has(edge.target)) return;
        const a = positions.get(edge.source);
        const b = positions.get(edge.target);
        if (!a || !b) return;
        const isFocused = selectedId !== null && (edge.source === selectedId || edge.target === selectedId);
        const alpha = focusActive ? (selectedId ? (isFocused ? 0.85 : 0.06) : 0.35) : 0.28;
        ctx.strokeStyle = isFocused ? "#f4e6c9" : "#2a4a63";
        ctx.globalAlpha = alpha;
        ctx.lineWidth = (isFocused ? 1.6 : 0.9) / scale;
        ctx.setLineDash([6 / scale, 5 / scale]);
        ctx.lineDashOffset = -t * 22;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
        ctx.setLineDash([]);
      });
      ctx.globalAlpha = 1;

      // Nodes — glowing halo + solid core; dimmed when out of focus.
      nodes.forEach((node) => {
        if (!visibleNodeIds.has(node.id)) return;
        const p = positions.get(node.id);
        if (!p) return;
        const matchesSearch = searchLower.length === 0 || node.label.toLowerCase().includes(searchLower) || node.subtitle.toLowerCase().includes(searchLower);
        const isSelected = node.id === selectedId;
        const isConnected = selectedId !== null && connectedIds.has(node.id);
        let alpha = 1;
        if (searchLower.length > 0 && !matchesSearch) alpha = 0.12;
        if (selectedId !== null && !isSelected && !isConnected) alpha = Math.min(alpha, 0.15);
        const color = nodeColor(node);
        const r = NODE_RADIUS[node.type];

        ctx.globalAlpha = alpha * (0.35 + 0.25 * pulse);
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, r + (isSelected ? 10 : 6), 0, Math.PI * 2);
        ctx.fill();

        ctx.globalAlpha = alpha;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fill();
        if (isSelected) {
          ctx.strokeStyle = "#f4e6c9";
          ctx.lineWidth = 2 / scale;
          ctx.stroke();
        }

        const activelyMatching = searchLower.length > 0 && matchesSearch;
        if ((scale > 0.75 || isSelected || activelyMatching) && alpha > 0.5) {
          ctx.globalAlpha = alpha;
          ctx.fillStyle = "#d8e6f2";
          ctx.font = `${11 / scale}px monospace`;
          ctx.textAlign = "center";
          ctx.fillText(node.label.length > 28 ? `${node.label.slice(0, 27)}…` : node.label, p.x, p.y + r + 12 / scale);
        }
      });
      ctx.globalAlpha = 1;

      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);

    const worldFromEvent = (e: MouseEvent): { x: number; y: number } => {
      const rect = canvas.getBoundingClientRect();
      const { panX, panY, scale } = viewRef.current;
      return { x: (e.clientX - rect.left - panX) / scale, y: (e.clientY - rect.top - panY) / scale };
    };

    const hitTest = (x: number, y: number): KnowledgeNode | null => {
      for (let i = nodes.length - 1; i >= 0; i--) {
        const node = nodes[i];
        if (!node || !visibleNodeIds.has(node.id)) continue;
        const p = positions.get(node.id);
        if (!p) continue;
        const r = NODE_RADIUS[node.type] + 4;
        if ((p.x - x) ** 2 + (p.y - y) ** 2 <= r * r) return node;
      }
      return null;
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const view = viewRef.current;
      const worldX = (mx - view.panX) / view.scale;
      const worldY = (my - view.panY) / view.scale;
      const nextScale = Math.min(3, Math.max(0.25, view.scale * (e.deltaY > 0 ? 0.9 : 1.1)));
      viewRef.current = { scale: nextScale, panX: mx - worldX * nextScale, panY: my - worldY * nextScale };
    };
    const onMouseDown = (e: MouseEvent) => {
      dragRef.current = { x: e.clientX, y: e.clientY, dragging: true, moved: false };
    };
    const onMouseMove = (e: MouseEvent) => {
      const drag = dragRef.current;
      if (!drag?.dragging) return;
      const dx = e.clientX - drag.x;
      const dy = e.clientY - drag.y;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) drag.moved = true;
      viewRef.current = { ...viewRef.current, panX: viewRef.current.panX + dx, panY: viewRef.current.panY + dy };
      drag.x = e.clientX;
      drag.y = e.clientY;
    };
    const endDrag = (e: MouseEvent) => {
      const drag = dragRef.current;
      dragRef.current = null;
      if (!drag || drag.moved) return;
      const { x, y } = worldFromEvent(e);
      const hit = hitTest(x, y);
      setSelectedId(hit ? hit.id : null);
    };

    canvas.addEventListener("wheel", onWheel, { passive: false });
    canvas.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", endDrag);

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      canvas.removeEventListener("wheel", onWheel);
      canvas.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", endDrag);
    };
  }, [nodes, edges, positions, visibleNodeIds, selectedId, connectedIds, searchLower]);

  const toggleType = (type: KnowledgeNodeType) => {
    setVisibleTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const jumpTo = (id: string) => setSelectedId(id);

  return (
    <div className="absolute inset-0 z-10 flex flex-col bg-cmd-bg/95 backdrop-blur-sm">
      <header className="flex flex-wrap items-center gap-2 border-b border-cmd-border bg-cmd-panel/90 px-4 py-2.5">
        <span className="tracking-[0.2em] text-cmd-cyan">COMPANY KNOWLEDGE GRAPH</span>
        {graph && (
          <StatusPill tone="cyan">
            {graph.nodes.length} NODES · {graph.edges.length} LINKS
          </StatusPill>
        )}
        <div className="ml-2 flex flex-wrap items-center gap-1">
          {ALL_TYPES.map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => toggleType(type)}
              className="inline-flex items-center gap-1 rounded-sm border px-2 py-0.5 text-[9px] uppercase tracking-wider transition-colors"
              style={{
                borderColor: visibleTypes.has(type) ? `${TYPE_COLORS[type]}80` : "#1f3348",
                color: visibleTypes.has(type) ? TYPE_COLORS[type] : "#6c8299",
                backgroundColor: "rgba(6,10,18,0.6)",
              }}
            >
              <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ backgroundColor: visibleTypes.has(type) ? TYPE_COLORS[type] : "#3a4a5c" }} />
              {TYPE_LABELS[type]}
            </button>
          ))}
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search the network…"
          className="ml-auto w-48 rounded-sm border border-cmd-border bg-cmd-bg px-2 py-1 text-[10px] text-cmd-text placeholder:text-cmd-textDim focus:border-cmd-cyan/60 focus:outline-none"
        />
        <button
          type="button"
          onClick={onClose}
          className="rounded-sm border border-cmd-border px-2.5 py-1 text-cmd-textDim transition-colors hover:border-cmd-red/50 hover:text-cmd-red"
        >
          CLOSE ✕
        </button>
      </header>

      <div className="relative flex min-h-0 flex-1">
        <div ref={containerRef} className="relative min-w-0 flex-1">
          {loading && nodes.length === 0 ? (
            <div className="flex h-full items-center justify-center text-cmd-textDim">Mapping the company's knowledge…</div>
          ) : error && nodes.length === 0 ? (
            <div className="flex h-full items-center justify-center text-cmd-red">Knowledge Graph unavailable — {error}</div>
          ) : nodes.length === 0 ? (
            <div className="flex h-full items-center justify-center">
              <EmptyState>No knowledge recorded yet — the graph grows as research, Academy projects, and reviews complete.</EmptyState>
            </div>
          ) : (
            <canvas ref={canvasRef} className="block cursor-grab active:cursor-grabbing" />
          )}
        </div>

        <aside className="w-72 flex-none overflow-y-auto border-l border-cmd-border bg-cmd-panel/90 p-3">
          {selectedNode ? (
            <>
              <TerminalLabel>{TYPE_LABELS[selectedNode.type]}</TerminalLabel>
              <div className="mb-1 text-cmd-cyan">{selectedNode.label}</div>
              <div className="mb-2 text-[10px] text-cmd-textDim">{selectedNode.subtitle}</div>
              {selectedNode.timestamp && <div className="mb-3 text-[9px] text-cmd-textDim">{new Date(selectedNode.timestamp).toLocaleString()}</div>}
              <TerminalLabel>Connections ({connectedEdges.length})</TerminalLabel>
              {connectedEdges.length === 0 ? (
                <EmptyState>No recorded connections.</EmptyState>
              ) : (
                <div className="space-y-1.5">
                  {connectedEdges.map((edge, i) => {
                    const otherId = edge.source === selectedNode.id ? edge.target : edge.source;
                    const other = nodeById.get(otherId);
                    if (!other) return null;
                    const direction = edge.source === selectedNode.id ? "→" : "←";
                    return (
                      <button
                        key={`${edge.source}-${edge.target}-${edge.relation}-${i}`}
                        type="button"
                        onClick={() => jumpTo(other.id)}
                        className="block w-full rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-left text-[9px] transition-colors hover:border-cmd-cyan/50"
                      >
                        <span style={{ color: nodeColor(other) }}>{other.label}</span>
                        <span className="ml-1 text-cmd-textDim">
                          {direction} {edge.label}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
              <button type="button" onClick={() => setSelectedId(null)} className="mt-3 text-[9px] uppercase tracking-wider text-cmd-textDim hover:text-cmd-cyan">
                ‹ back to overview
              </button>
            </>
          ) : (
            <>
              <TerminalLabel>Recent Discoveries</TerminalLabel>
              {recentDiscoveries.length === 0 ? (
                <EmptyState>Nothing on record yet.</EmptyState>
              ) : (
                <div className="space-y-1.5">
                  {recentDiscoveries.map((node) => (
                    <button
                      key={node.id}
                      type="button"
                      onClick={() => jumpTo(node.id)}
                      className="block w-full rounded-sm border border-cmd-border/60 bg-cmd-bg/40 p-1.5 text-left text-[9px] transition-colors hover:border-cmd-cyan/50"
                    >
                      <span style={{ color: nodeColor(node) }}>{node.label}</span>
                      <div className="mt-0.5 text-cmd-textDim">{node.subtitle}</div>
                    </button>
                  ))}
                </div>
              )}
              <div className="mt-4 text-[9px] leading-relaxed text-cmd-textDim">
                Scroll to zoom, drag to pan, click a node to inspect it. Every node and connection here traces to a real completed
                research item, Academy project, executive review, or company milestone — nothing is invented.
              </div>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
