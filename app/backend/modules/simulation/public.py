"""Stable simulation-module entry point."""

from app.backend.modules.simulation.baselines import CurrentlyAvailableStrategy, NearestStrategy
from app.backend.modules.simulation.engine import SimulationEngine
from app.backend.modules.simulation.history import (
    STATUS_COLUMNS,
    build_status_window,
    generate_status_history,
    snapshots_to_frame,
    write_status_history,
)
from app.backend.modules.simulation.runner import (
    AvailabilityFn,
    DefaultSimulationRunner,
    FixtureLoader,
    bundle_hash,
    compare_strategies,
    strategy_for,
)

__all__ = [
    "STATUS_COLUMNS",
    "AvailabilityFn",
    "CurrentlyAvailableStrategy",
    "DefaultSimulationRunner",
    "FixtureLoader",
    "NearestStrategy",
    "SimulationEngine",
    "build_status_window",
    "bundle_hash",
    "compare_strategies",
    "generate_status_history",
    "snapshots_to_frame",
    "strategy_for",
    "write_status_history",
]
