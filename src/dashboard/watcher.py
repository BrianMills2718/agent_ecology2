"""File watcher for detecting changes to JSONL event log."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable, Awaitable, Any, TYPE_CHECKING
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileSystemEvent

from ..config import get_validated_config

if TYPE_CHECKING:
    from watchdog.observers import Observer as ObserverType


class JSONLFileHandler(FileSystemEventHandler):
    """Handler for JSONL file modification events."""

    def __init__(
        self,
        file_path: Path,
        callback: Callable[[], Awaitable[None]],
        loop: asyncio.AbstractEventLoop
    ) -> None:
        self.file_path = file_path
        self.callback = callback
        self.loop = loop
        self._debounce_task: asyncio.Task[None] | None = None
        # Debounce delay from config (converted from ms to seconds)
        config = get_validated_config()
        self._debounce_delay = config.dashboard.debounce_delay_ms / 1000.0

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification event."""
        if not isinstance(event, FileModifiedEvent):
            return

        src_path = event.src_path if isinstance(event.src_path, str) else event.src_path.decode()
        event_path = Path(src_path)
        if event_path.name != self.file_path.name:
            return

        # Schedule debounced callback
        asyncio.run_coroutine_threadsafe(
            self._schedule_callback(),
            self.loop
        )

    async def _schedule_callback(self) -> None:
        """Debounce callback to avoid rapid successive calls."""
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

        self._debounce_task = asyncio.create_task(self._debounced_callback())

    async def _debounced_callback(self) -> None:
        """Wait for debounce delay then call callback."""
        try:
            await asyncio.sleep(self._debounce_delay)
            await self.callback()
        except asyncio.CancelledError:
            pass


class JSONLWatcher:
    """Watch a JSONL file for changes and trigger callbacks."""

    def __init__(self, jsonl_path: str | Path) -> None:
        self.jsonl_path = Path(jsonl_path).resolve()
        self.observer: Any = None  # watchdog Observer - type not recognized by mypy
        self.handler: JSONLFileHandler | None = None
        self._callbacks: list[Callable[[], Awaitable[None]]] = []
        self._running = False

    def add_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Add a callback to be triggered on file changes."""
        self._callbacks.append(callback)

    async def start(self) -> None:
        """Start watching the file."""
        if self._running:
            return

        loop = asyncio.get_event_loop()

        async def combined_callback() -> None:
            for cb in self._callbacks:
                try:
                    await cb()
                except Exception as e:
                    print(f"Watcher callback error: {e}")

        self.handler = JSONLFileHandler(
            self.jsonl_path,
            combined_callback,
            loop
        )

        self.observer = Observer()
        self.observer.schedule(
            self.handler,
            str(self.jsonl_path.parent),
            recursive=False
        )
        self.observer.start()
        self._running = True

    def stop(self) -> None:
        """Stop watching the file."""
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=1.0)
            self.observer = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running


class PollingWatcher:
    """Fallback polling-based watcher for when watchdog isn't reliable."""

    def __init__(self, jsonl_path: str | Path, poll_interval: float | None = None) -> None:
        self.jsonl_path = Path(jsonl_path).resolve()
        if poll_interval is None:
            poll_interval = get_validated_config().dashboard.poll_interval
        self.poll_interval = poll_interval
        self._callbacks: list[Callable[[], Awaitable[None]]] = []
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._last_size: int = 0
        self._last_mtime: float = 0

    def add_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Add a callback to be triggered on file changes."""
        self._callbacks.append(callback)

    async def start(self) -> None:
        """Start polling the file."""
        if self._running:
            return

        # Initialize tracking values
        if self.jsonl_path.exists():
            stat = self.jsonl_path.stat()
            self._last_size = stat.st_size
            self._last_mtime = stat.st_mtime

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await asyncio.sleep(self.poll_interval)

                if not self.jsonl_path.exists():
                    continue

                stat = self.jsonl_path.stat()
                if stat.st_size != self._last_size or stat.st_mtime != self._last_mtime:
                    self._last_size = stat.st_size
                    self._last_mtime = stat.st_mtime

                    # Trigger callbacks
                    for cb in self._callbacks:
                        try:
                            await cb()
                        except Exception as e:
                            print(f"Polling callback error: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Polling error: {e}")
                await asyncio.sleep(1.0)

    def stop(self) -> None:
        """Stop polling."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    @property
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running
