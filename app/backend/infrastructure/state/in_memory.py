from typing import Generic, TypeVar

T = TypeVar("T")


class InMemoryAllocationStore(Generic[T]):
    """Small process-local store; callers own DTO validation and locking."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def save(self, request_id: str, value: T) -> T:
        self._items[request_id] = value
        return value

    def get(self, request_id: str) -> T | None:
        return self._items.get(request_id)

    def reset(self) -> None:
        self._items.clear()
