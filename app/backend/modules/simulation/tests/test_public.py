import pytest

from app.backend.contracts.enums import Scenario, Strategy
from app.backend.modules.simulation import public
from app.backend.modules.simulation.baselines import CurrentlyAvailableStrategy, NearestStrategy
from app.backend.modules.simulation.tests.test_runner import STATIONS, make_config

CONFIG = make_config()
RUNNER = public.DefaultSimulationRunner(
    lambda _request: pytest.fail("loader not expected"), STATIONS, {Scenario.NORMAL: CONFIG}
)


def test_public_exports_runner_and_baselines() -> None:
    for name in (
        "DefaultSimulationRunner",
        "NearestStrategy",
        "CurrentlyAvailableStrategy",
        "compare_strategies",
        "strategy_for",
        "bundle_hash",
    ):
        assert name in public.__all__
        assert hasattr(public, name)


def test_strategy_for_maps_baselines() -> None:
    assert isinstance(public.strategy_for(RUNNER, Strategy.NEAREST), NearestStrategy)
    assert isinstance(
        public.strategy_for(RUNNER, Strategy.CURRENTLY_AVAILABLE), CurrentlyAvailableStrategy
    )


def test_strategy_for_returns_injected_ai_strategy() -> None:
    ai = NearestStrategy()
    assert public.strategy_for(RUNNER, Strategy.AI_ALLOCATION, ai) is ai


def test_strategy_for_rejects_missing_ai_strategy() -> None:
    with pytest.raises(ValueError, match="ai_allocation"):
        public.strategy_for(RUNNER, Strategy.AI_ALLOCATION)
