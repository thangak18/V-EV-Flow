from collections.abc import Callable
from threading import Lock
from typing import Generic, TypeVar

T = TypeVar("T")


class InMemoryAllocationStore(Generic[T]):
    """Small process-local store; callers own DTO validation and locking."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}
        self._lock = Lock()

    def save(self, request_id: str, value: T) -> T:
        with self._lock:
            self._items[request_id] = value
        return value

    def get(self, request_id: str) -> T | None:
        with self._lock:
            return self._items.get(request_id)

    def get_or_create(self, request_id: str, factory: Callable[[], T]) -> tuple[T, bool]:
        """Return a stored value or atomically construct and store one."""
        with self._lock:
            value = self._items.get(request_id)
            if value is not None:
                return value, False
            value = factory()
            self._items[request_id] = value
            return value, True

    def reset(self) -> None:
        with self._lock:
            self._items.clear()
