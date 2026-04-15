"""0/1 Knapsack DP for time-constrained study optimization (Phase 15).

DAA Unit IV. Given a list of candidate study topics (each with an hours cost
and a fit-score-impact value) and a time budget in hours, return the subset
that maximizes total value.

Classic bottom-up DP with integer-hour discretization. Time complexity:
O(n × W) where n is the number of topics and W is the (integerised) budget.
Space: O(n × W) so we can reconstruct which items were chosen.

We discretize hours to 0.5h steps by multiplying by 2, then divide back when
returning results. This keeps the DP table small while still letting us
accept fractional hours from dynamic edge weights.
"""
from __future__ import annotations

from dataclasses import dataclass


SCALE = 2  # half-hour granularity


@dataclass
class KnapsackItem:
    topic: str
    hours: float            # cost (learning hours after dynamic weighting)
    value: float            # impact on fit score (arbitrary positive units)
    reason: str = ""        # human-readable explanation


@dataclass
class KnapsackResult:
    included: list[KnapsackItem]
    excluded: list[KnapsackItem]
    total_hours: float
    total_value: float
    budget_hours: float


def solve(items: list[KnapsackItem], budget_hours: float) -> KnapsackResult:
    """Bottom-up 0/1 Knapsack DP.

    Scales hours to half-hour units so we can use integer indexing. Values
    stay as floats — DP comparisons use >.
    """
    if budget_hours <= 0 or not items:
        return KnapsackResult(
            included=[],
            excluded=list(items),
            total_hours=0.0,
            total_value=0.0,
            budget_hours=budget_hours,
        )

    # Scaled weights (integer half-hours)
    weights: list[int] = [max(1, round(item.hours * SCALE)) for item in items]
    values: list[float] = [float(item.value) for item in items]
    capacity: int = max(0, round(budget_hours * SCALE))

    n = len(items)
    # dp[i][w] = max value considering first i items with capacity w
    dp: list[list[float]] = [[0.0] * (capacity + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        wi = weights[i - 1]
        vi = values[i - 1]
        for w in range(capacity + 1):
            dp[i][w] = dp[i - 1][w]
            if wi <= w:
                candidate = dp[i - 1][w - wi] + vi
                if candidate > dp[i][w]:
                    dp[i][w] = candidate

    # Backtrack to recover included items
    included_indices: list[int] = []
    w = capacity
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            included_indices.append(i - 1)
            w -= weights[i - 1]
    included_indices.reverse()

    included_set = set(included_indices)
    included_items = [items[i] for i in included_indices]
    excluded_items = [items[i] for i in range(n) if i not in included_set]

    total_hours = sum(item.hours for item in included_items)
    total_value = dp[n][capacity]

    return KnapsackResult(
        included=included_items,
        excluded=excluded_items,
        total_hours=round(total_hours, 2),
        total_value=round(total_value, 2),
        budget_hours=budget_hours,
    )
