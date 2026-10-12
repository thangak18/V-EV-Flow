"""Deterministic baseline allocation strategies.

Both share one feasibility filter and tie-break by ``station_id``. The runner
only passes feasible candidates (compatible connector, reachable); the SOC
check here is a second guard so the strategies stay safe when used alone.
"""

from collections.abc import Callable

from app.backend.contracts.recommendation import (
    AllocationContext,
    FeasibleCandidate,
    RankedCandidate,
    RankedPlan,
)

DEFAULT_MIN_SOC_PCT = 10.0


def _feasible(context: AllocationContext, min_soc_pct: float) -> list[FeasibleCandidate]:
    return [item for item in context.candidates if item.arrival_soc_pct >= min_soc_pct]


def _plan(ordered: list[FeasibleCandidate], reasons: list[str]) -> RankedPlan:
    ranked = [
        RankedCandidate(**item.model_dump(), rank=index + 1, score=-item.distance_km)
        for index, item in enumerate(ordered[:2])
    ]
    return RankedPlan(
        primary=ranked[0] if ranked else None,
        backup=ranked[1] if len(ranked) > 1 else None,
        plan_p=None,
        reasons=reasons if ranked else ["no feasible station"],
    )


def _by_distance(items: list[FeasibleCandidate]) -> list[FeasibleCandidate]:
    return sorted(items, key=lambda item: (item.distance_km, item.station_id))


class NearestStrategy:
    def __init__(self, min_soc_pct: float = DEFAULT_MIN_SOC_PCT) -> None:
        self._min_soc_pct = min_soc_pct

    def select(self, context: AllocationContext) -> RankedPlan:
        ordered = _by_distance(_feasible(context, self._min_soc_pct))
        return _plan(ordered, ["nearest feasible station"])


class CurrentlyAvailableStrategy:
    """Nearest feasible station that has a free port now; nearest feasible otherwise."""

    def __init__(
        self, free_ports: Callable[[str], int], min_soc_pct: float = DEFAULT_MIN_SOC_PCT
    ) -> None:
        self._free_ports = free_ports
        self._min_soc_pct = min_soc_pct

    def select(self, context: AllocationContext) -> RankedPlan:
        feasible = _feasible(context, self._min_soc_pct)
        free = [item for item in feasible if self._free_ports(item.station_id) > 0]
        if free:
            rest = [item for item in feasible if item not in free]
            return _plan(
                _by_distance(free) + _by_distance(rest),
                ["nearest feasible station with a free port"],
            )
        return _plan(
            _by_distance(feasible),
            ["no feasible station has a free port; fell back to nearest feasible station"],
        )
