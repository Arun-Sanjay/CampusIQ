"""Dijkstra's shortest path for the Adaptive Learning Engine (Phase 15).

DAA Unit IV. Standard textbook implementation using a binary min-heap.
The graph here is a directed weighted graph where nodes are skill names
(strings) and edge weights are estimated learning hours AFTER dynamic
adjustment for the student's current mastery (see `skill_graph.py`).

Time complexity: O((V + E) log V) with a heap-based priority queue.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass


# ── Types ──

Graph = dict[str, dict[str, float]]
"""Adjacency dict: graph[u][v] = weight of edge u -> v."""


@dataclass
class ShortestPathResult:
    source: str
    target: str
    total_cost: float
    path: list[str]                    # ordered list of nodes from source to target
    edges_with_weights: list[tuple[str, str, float]]
    distances: dict[str, float]        # node -> cumulative cost from source (for debugging)


def dijkstra(graph: Graph, source: str, target: str) -> ShortestPathResult:
    """Classic Dijkstra. Returns the shortest path + total cost.

    If `target` is unreachable, returns an empty path and `total_cost = inf`.
    """
    if source not in graph:
        graph[source] = {}
    if target not in graph:
        graph[target] = {}

    distances: dict[str, float] = {node: math.inf for node in graph}
    distances[source] = 0.0
    predecessors: dict[str, str | None] = {node: None for node in graph}

    # Min-heap keyed by cumulative distance
    heap: list[tuple[float, str]] = [(0.0, source)]
    visited: set[str] = set()

    while heap:
        current_dist, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)

        if u == target:
            break

        for v, weight in graph.get(u, {}).items():
            if v in visited:
                continue
            new_dist = current_dist + weight
            if new_dist < distances.get(v, math.inf):
                distances[v] = new_dist
                predecessors[v] = u
                heapq.heappush(heap, (new_dist, v))

    # Reconstruct path
    path: list[str] = []
    cursor: str | None = target
    while cursor is not None:
        path.append(cursor)
        cursor = predecessors.get(cursor)
    path.reverse()

    if not path or path[0] != source:
        # Target unreachable
        return ShortestPathResult(
            source=source,
            target=target,
            total_cost=math.inf,
            path=[],
            edges_with_weights=[],
            distances=distances,
        )

    edges: list[tuple[str, str, float]] = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edges.append((u, v, graph[u][v]))

    return ShortestPathResult(
        source=source,
        target=target,
        total_cost=distances[target],
        path=path,
        edges_with_weights=edges,
        distances=distances,
    )


def dijkstra_multi_target(
    graph: Graph,
    source: str,
    targets: list[str],
) -> dict[str, ShortestPathResult]:
    """Run Dijkstra once from `source` and return the shortest path to each target.

    Slightly faster than running `dijkstra()` per target because the heap pass
    is shared. Useful when computing paths to every skill a company requires.
    """
    if source not in graph:
        graph[source] = {}

    distances: dict[str, float] = {node: math.inf for node in graph}
    distances[source] = 0.0
    predecessors: dict[str, str | None] = {node: None for node in graph}

    heap: list[tuple[float, str]] = [(0.0, source)]
    visited: set[str] = set()

    while heap:
        current_dist, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)

        for v, weight in graph.get(u, {}).items():
            if v in visited:
                continue
            new_dist = current_dist + weight
            if new_dist < distances.get(v, math.inf):
                distances[v] = new_dist
                predecessors[v] = u
                heapq.heappush(heap, (new_dist, v))

    results: dict[str, ShortestPathResult] = {}
    for target in targets:
        path: list[str] = []
        cursor: str | None = target
        while cursor is not None:
            path.append(cursor)
            cursor = predecessors.get(cursor)
        path.reverse()
        if not path or path[0] != source or distances.get(target, math.inf) == math.inf:
            results[target] = ShortestPathResult(
                source=source,
                target=target,
                total_cost=math.inf,
                path=[],
                edges_with_weights=[],
                distances=distances,
            )
            continue

        edges: list[tuple[str, str, float]] = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edges.append((u, v, graph[u][v]))
        results[target] = ShortestPathResult(
            source=source,
            target=target,
            total_cost=distances[target],
            path=path,
            edges_with_weights=edges,
            distances=distances,
        )
    return results
