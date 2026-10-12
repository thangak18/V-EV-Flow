"""Per-vehicle outcomes and the metric definitions shared by every strategy.

- ``success_rate``: vehicles that found a free port on arrival / ``vehicle_count``.
  Vehicles served only after waiting are not successes at arrival.
- ``failed_count``: vehicles with no feasible plan, that left after waiting
  longer than the maximum wait, or that never arrived inside the window.
  Failed vehicles stay in every denominator.
- ``mean_detour_km``: over vehicles that were assigned a station (km).
- ``mean_wait_minutes``: over vehicles that reached a station; abandoned
  vehicles count the maximum wait they endured (minutes).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.backend.contracts.simulation import SimulationMetrics


class OutcomeStatus(StrEnum):
    SUCCESS = "success"
    SERVED_AFTER_WAIT = "served_after_wait"
    FAILED = "failed"


@dataclass(frozen=True)
class VehicleOutcome:
    vehicle_id: str
    status: OutcomeStatus
    detour_km: float | None = None
    wait_minutes: float | None = None
    reason: str | None = None


def calculate_metrics(outcomes: Sequence[VehicleOutcome], vehicle_count: int) -> SimulationMetrics:
    if vehicle_count < 0 or len(outcomes) > vehicle_count:
        raise ValueError("outcomes cannot exceed vehicle_count")
    if vehicle_count == 0:
        return SimulationMetrics(
            success_rate=0.0,
            mean_detour_km=0.0,
            mean_wait_minutes=0.0,
            failed_count=0,
            vehicle_count=0,
        )
    successes = sum(item.status is OutcomeStatus.SUCCESS for item in outcomes)
    # A vehicle without an outcome never finished: it counts as failed.
    failed = (
        vehicle_count
        - len(outcomes)
        + sum(item.status is OutcomeStatus.FAILED for item in outcomes)
    )
    detours = [item.detour_km for item in outcomes if item.detour_km is not None]
    waits = [item.wait_minutes for item in outcomes if item.wait_minutes is not None]
    return SimulationMetrics(
        success_rate=successes / vehicle_count,
        mean_detour_km=sum(detours) / len(detours) if detours else 0.0,
        mean_wait_minutes=sum(waits) / len(waits) if waits else 0.0,
        failed_count=failed,
        vehicle_count=vehicle_count,
    )
