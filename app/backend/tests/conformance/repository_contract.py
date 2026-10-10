class StationRepositoryContract:
    def make_repository(self):
        raise NotImplementedError

    def test_list_returns_valid_unique_station_ids(self) -> None:
        stations = self.make_repository().list_stations()
        assert stations
        assert len({item.station_id for item in stations}) == len(stations)
