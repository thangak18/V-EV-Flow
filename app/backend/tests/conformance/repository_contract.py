import pytest

from app.backend.contracts.errors import StationNotFoundError


class StationRepositoryContract:
    def make_repository(self):
        raise NotImplementedError

    def test_list_returns_valid_unique_station_ids(self) -> None:
        stations = self.make_repository().list_stations()
        assert stations
        assert len({item.station_id for item in stations}) == len(stations)

    def test_list_order_is_stable(self) -> None:
        repository = self.make_repository()
        assert repository.list_stations() == repository.list_stations()

    def test_unknown_station_has_typed_not_found_error(self) -> None:
        repository = self.make_repository()
        with pytest.raises(StationNotFoundError):
            repository.get_station("UNKNOWN")
