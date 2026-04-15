"""Prim's Minimum Spanning Tree for prerequisite visualization (Phase 15).

DAA Unit IV. Over the subgraph induced by a set of target skills (and their
prerequisites), compute the MST — i.e. the minimum total learning hours to
touch every required skill exactly once.

Used by the frontend to render a clean tree layout of "what to learn, in
what order, with the least total effort" as a companion to the Dijkstra path.

Time complexity: O((V + E) log V) with a binary heap.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass


Graph = dict[str, dict[str, float]]


@dataclass
class MSTResult:
    edges: list[tuple[str, str, float]]     # (parent, child, weight)
    total_weight: float
    nodes: list[str]


def undirected_from_directed(graph: Graph) -> Graph:
    """Prim's needs an undirected view — mirror every edge."""
    undirected: Graph = {node: dict(neighbors) for node, neighbors in graph.items()}
    for u, neighbors in graph.items():
        for v, w in neighbors.items():
            if v not in undirected:
                undirected[v] = {}
            existing = undirected[v].get(u)
            if existing is None or w < existing:
                undirected[v][u] = w
    return undirected


def prim_mst(graph: Graph, start: str) -> MSTResult:
    """Prim's MST starting from `start`. Only traverses the connected component.

    Returns the MST edges + total weight. If `start` is isolated, returns an
    empty result.
    """
    undirected = undirected_from_directed(graph)
    if start not in undirected:
        return MSTResult(edges=[], total_weight=0.0, nodes=[])

    visited: set[str] = {start}
    edges_out: list[tuple[str, str, float]] = []
    total = 0.0

    # Min-heap of (weight, u, v) — candidate edges from the visited set
    heap: list[tuple[float, str, str]] = []
    for v, w in undirected[start].items():
        heapq.heappush(heap, (w, start, v))

    while heap:
        weight, u, v = heapq.heappop(heap)
        if v in visited:
            continue
        visited.add(v)
        edges_out.append((u, v, weight))
        total += weight
        for next_v, next_w in undirected.get(v, {}).items():
            if next_v not in visited:
                heapq.heappush(heap, (next_w, v, next_v))

    return MSTResult(
        edges=edges_out,
        total_weight=round(total, 2),
        nodes=list(visited),
    )


def mst_over_subset(graph: Graph, skills: list[str]) -> MSTResult:
    """Build an MST that connects every skill in `skills` using `graph` as the
    full universe. Skills outside the graph are ignored. Returns an empty
    result if no skills are present.
    """
    relevant = [s for s in skills if s in graph]
    if not relevant:
        return MSTResult(edges=[], total_weight=0.0, nodes=[])

    # Anchor at the skill with the highest out-degree so the tree is as
    # connected as possible before falling through to unreachable skills.
    def deg(node: str) -> int:
        return len(graph.get(node, {}))

    anchor = max(relevant, key=deg)
    result = prim_mst(graph, anchor)

    # If some required skills weren't reached, we simply return what we could
    # — the caller can render them as disconnected leaves.
    return result
