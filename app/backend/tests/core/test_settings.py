"""Tests for validated backend settings and adapter selection."""

from pydantic import ValidationError

from app.backend.core.settings import Settings, get_settings


def test_mock_mode_needs_no_external_secret() -> None:
    settings = Settings(data_backend="mock", predictor_backend="fake", route_backend="fake")
    assert settings.demo_seed == 42


def test_goong_mode_requires_rest_key() -> None:
    try:
        Settings(route_backend="goong", goong_rest_api_key=None)
    except ValidationError:
        return
    raise AssertionError("goong mode accepted a missing key")


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()
