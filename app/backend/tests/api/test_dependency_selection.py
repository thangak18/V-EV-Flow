from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.backend.api.dependencies import build_container
from app.backend.contracts.enums import Scenario
from app.backend.core.settings import Settings
from app.backend.infrastructure.repositories.mock import MockStatusRepository
from app.backend.infrastructure.services.fakes import FakePredictor, FakeRouteProvider


def test_mock_dependencies_are_scenario_scoped_and_share_c6_store() -> None:
    container = build_container(Settings())

    assert isinstance(container.routes, FakeRouteProvider)
    assert set(container.status_repositories_by_scenario) == set(Scenario)
    assert set(container.predictors_by_scenario) == set(Scenario)
    assert all(
        isinstance(item, MockStatusRepository)
        for item in container.status_repositories_by_scenario.values()
    )
    assert all(
        isinstance(item, FakePredictor) for item in container.predictors_by_scenario.values()
    )
    assert container.allocation_coordinator._store is container.virtual_load_store


def test_real_and_model_backends_fail_explicitly() -> None:
    import pytest

    from app.backend.api.dependencies import StartupConfigurationError

    with pytest.raises(ValueError, match="real data requires"):
        Settings(data_backend="real")
    for settings in (
        Settings(data_backend="file", predictor_backend="model", model_dir=Path(".")),
    ):
        try:
            build_container(settings)
        except StartupConfigurationError:
            pass
        else:
            raise AssertionError("unavailable backend must not fall back")


def test_goong_owned_client_closes_with_application_lifespan() -> None:
    from app.backend.api.main import create_app

    app = create_app(Settings(route_backend="goong", goong_rest_api_key="not-a-secret"))
    client = app.state.container.owned_route_client
    assert client is not None and not client.is_closed
    with TestClient(app):
        pass
    assert client.is_closed


def test_external_goong_client_is_not_owned() -> None:
    from app.backend.api.main import create_app

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"routes": []}))
    external = httpx.AsyncClient(transport=transport)
    app = create_app(
        Settings(route_backend="goong", goong_rest_api_key="x"),
        route_client=external,
    )
    with TestClient(app):
        pass
    assert not external.is_closed


def test_charge_duration_above_c6_maximum_is_rejected() -> None:
    from app.backend.modules.recommendation.allocation import MAX_RESERVATION_DURATION_MINUTES

    with pytest.raises(ValueError, match="reservation maximum"):
        Settings(assumed_charge_duration_minutes=MAX_RESERVATION_DURATION_MINUTES + 0.1)


def test_fake_horizon_must_support_the_pressure_proxy() -> None:
    with pytest.raises(ValueError, match="30-minute pressure proxy"):
        Settings(fake_prediction_horizon_minutes=20)
