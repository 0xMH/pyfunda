"""Private parallel execution helpers."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Generic, TypeVar


ClientT = TypeVar("ClientT")
ItemT = TypeVar("ItemT")
ResultT = TypeVar("ResultT")


class _ParallelRunner(Generic[ClientT]):
    """Reusable per-thread client pool for IO-bound batch work."""

    def __init__(
        self,
        client_factory: Callable[[], ClientT],
        close_client: Callable[[ClientT], None],
    ) -> None:
        self._client_factory = client_factory
        self._close_client = close_client
        self._executor: ThreadPoolExecutor | None = None
        self._workers = 0
        self._local = threading.local()
        self._clients: list[ClientT] = []
        self._clients_lock = threading.Lock()
        self._runner_lock = threading.RLock()

    def close(self) -> None:
        with self._runner_lock:
            executor = self._executor
            clients = self._clients
            self._executor = None
            self._workers = 0
            self._local = threading.local()
            self._clients = []

            if executor is not None:
                executor.shutdown(wait=True)
            for client in clients:
                self._close_client(client)

    def map(
        self,
        func: Callable[[ClientT, ItemT], ResultT],
        items: Iterable[ItemT],
        *,
        workers: int,
    ) -> list[ResultT]:
        if workers < 1:
            raise ValueError("workers must be >= 1")

        items = list(items)
        if not items:
            return []

        with self._runner_lock:
            executor = self._executor_for(workers)
            return list(executor.map(lambda item: func(self._client(), item), items))

    def _executor_for(self, workers: int) -> ThreadPoolExecutor:
        if self._executor is not None and workers <= self._workers:
            return self._executor

        self.close()
        self._executor = ThreadPoolExecutor(max_workers=workers)
        self._workers = workers
        return self._executor

    def _client(self) -> ClientT:
        existing = getattr(self._local, "client", None)
        if existing is not None:
            return existing

        created = self._client_factory()
        self._local.client = created
        with self._clients_lock:
            self._clients.append(created)
        return created
