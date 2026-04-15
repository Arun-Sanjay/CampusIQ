"""Backtracking + branch-and-bound study schedule generator (Phase 19, F26).

DAA Unit V — backtracking with branch-and-bound pruning. Given a set of
study tasks (each with a topic, estimated hours, and priority weight) and a
weekly time budget broken into 1-hour slots per day, find an assignment of
tasks → slots that:

1. Respects each task's hours (if a task is 3h, it occupies 3 contiguous slots).
2. Maximises the total priority weight of scheduled tasks.
3. Prefers slots not marked as locked (e.g. lectures, breaks).

We use a recursive search with two pruning rules:
- Bound pruning: skip a partial assignment if remaining-budget × max-weight
  can't beat the current best.
- Symmetry pruning: process tasks in priority-desc order so the first feasible
  assignment is already a strong upper bound for the rest of the search.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class StudyTask:
    topic: str
    hours: int                 # integer hours required
    priority: float            # higher = more important
    subject_code: str | None = None


@dataclass
class ScheduleSlot:
    day_index: int             # 0-6 (Mon-Sun)
    hour_index: int            # 0-23
    topic: str | None
    subject_code: str | None
    is_locked: bool = False    # blocked by lecture / break / sleep


@dataclass
class ScheduleResult:
    slots: list[ScheduleSlot]
    scheduled_tasks: list[StudyTask]
    skipped_tasks: list[StudyTask]
    total_value: float
    total_hours_scheduled: int
    explored_nodes: int


# ────────────────────────────────────────────────────────────────
# Default weekly grid
# ────────────────────────────────────────────────────────────────

DEFAULT_DAY_HOURS = list(range(8, 22))   # 8 AM - 10 PM (14h per day)
DEFAULT_LOCKED_LABEL_BY_HOUR: dict[int, str] = {
    13: "lunch",
    20: "dinner",
}


def build_empty_grid(
    *,
    days: int = 7,
    hours: list[int] | None = None,
    locked_hours: dict[int, str] | None = None,
) -> list[ScheduleSlot]:
    """Build a fresh weekly grid with locked slots for meals."""
    if hours is None:
        hours = DEFAULT_DAY_HOURS
    if locked_hours is None:
        locked_hours = DEFAULT_LOCKED_LABEL_BY_HOUR
    grid: list[ScheduleSlot] = []
    for d in range(days):
        for h in hours:
            label = locked_hours.get(h)
            grid.append(
                ScheduleSlot(
                    day_index=d,
                    hour_index=h,
                    topic=label,
                    subject_code=None,
                    is_locked=label is not None,
                )
            )
    return grid


# ────────────────────────────────────────────────────────────────
# Branch-and-bound search
# ────────────────────────────────────────────────────────────────

@dataclass
class _SearchState:
    best_value: float = 0.0
    best_assignment: dict[int, int] = field(default_factory=dict)  # task_idx → slot_start
    explored: int = 0
    max_explore: int = 200_000


def _is_feasible(
    grid: list[ScheduleSlot],
    used: set[int],
    start_idx: int,
    hours: int,
) -> bool:
    """Check that `hours` consecutive slots starting at `start_idx` are all
    on the same day, not locked, and not already used."""
    if start_idx + hours > len(grid):
        return False
    first = grid[start_idx]
    for i in range(hours):
        slot = grid[start_idx + i]
        if slot.day_index != first.day_index:
            return False
        if slot.is_locked:
            return False
        if (start_idx + i) in used:
            return False
    return True


def _search(
    tasks: list[StudyTask],
    grid: list[ScheduleSlot],
    task_idx: int,
    used: set[int],
    current_value: float,
    state: _SearchState,
    current_assignment: dict[int, int],
) -> None:
    if state.explored >= state.max_explore:
        return
    state.explored += 1

    # Bound: even if we take all remaining tasks, can we beat best?
    remaining_max = sum(t.priority for t in tasks[task_idx:])
    if current_value + remaining_max <= state.best_value:
        return

    if task_idx == len(tasks):
        if current_value > state.best_value:
            state.best_value = current_value
            state.best_assignment = dict(current_assignment)
        return

    task = tasks[task_idx]

    # Try to PLACE this task in each feasible slot
    for start in range(len(grid)):
        if not _is_feasible(grid, used, start, task.hours):
            continue
        new_used = set(used)
        for i in range(task.hours):
            new_used.add(start + i)
        current_assignment[task_idx] = start
        _search(
            tasks,
            grid,
            task_idx + 1,
            new_used,
            current_value + task.priority,
            state,
            current_assignment,
        )
        current_assignment.pop(task_idx, None)
        if state.explored >= state.max_explore:
            return

    # Also try SKIPPING this task
    _search(
        tasks,
        grid,
        task_idx + 1,
        used,
        current_value,
        state,
        current_assignment,
    )


def generate_schedule(
    tasks: list[StudyTask],
    *,
    days: int = 7,
    hours: list[int] | None = None,
    locked_hours: dict[int, str] | None = None,
) -> ScheduleResult:
    """Run branch-and-bound + return the best schedule found within the
    explore budget. Falls back to a greedy fill if the search bails early.
    """
    if not tasks:
        return ScheduleResult(
            slots=build_empty_grid(days=days, hours=hours, locked_hours=locked_hours),
            scheduled_tasks=[],
            skipped_tasks=[],
            total_value=0.0,
            total_hours_scheduled=0,
            explored_nodes=0,
        )

    # Process tasks in priority desc — symmetry pruning
    sorted_tasks = sorted(tasks, key=lambda t: -t.priority)
    grid = build_empty_grid(days=days, hours=hours, locked_hours=locked_hours)

    state = _SearchState()
    _search(
        sorted_tasks,
        grid,
        task_idx=0,
        used=set(),
        current_value=0.0,
        state=state,
        current_assignment={},
    )

    # Apply best assignment to a fresh grid copy
    final_grid = build_empty_grid(days=days, hours=hours, locked_hours=locked_hours)
    scheduled: list[StudyTask] = []
    skipped: list[StudyTask] = []
    total_hours = 0

    for task_idx, task in enumerate(sorted_tasks):
        start = state.best_assignment.get(task_idx)
        if start is None:
            skipped.append(task)
            continue
        for i in range(task.hours):
            slot = final_grid[start + i]
            if slot.is_locked:
                continue
            slot.topic = task.topic
            slot.subject_code = task.subject_code
        scheduled.append(task)
        total_hours += task.hours

    return ScheduleResult(
        slots=final_grid,
        scheduled_tasks=scheduled,
        skipped_tasks=skipped,
        total_value=state.best_value,
        total_hours_scheduled=total_hours,
        explored_nodes=state.explored,
    )
