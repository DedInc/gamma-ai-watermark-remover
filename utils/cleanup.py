"""Background cleanup support for generated output files."""

import asyncio
import logging
import os
import time
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def ensure_directories(*directories: str) -> None:
    """Create required application directories if they do not exist."""
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


async def cleanup_old_files(
    output_folder: str, interval_seconds: int, max_age_seconds: int
) -> None:
    """Periodically delete generated files older than max_age_seconds."""
    while True:
        try:
            cleaned = _delete_expired_files(output_folder, max_age_seconds)
            if cleaned > 0:
                logger.info(
                    "Auto-cleanup: removed %s expired file(s) from %s/",
                    cleaned,
                    output_folder,
                )
        except Exception as exc:
            logger.error("Auto-cleanup error: %s", exc)
        await asyncio.sleep(interval_seconds)


def _delete_expired_files(output_folder: str, max_age_seconds: int) -> int:
    """Delete expired regular files from output_folder and return count."""
    now = time.time()
    cleaned = 0
    for filename in os.listdir(output_folder):
        if filename == ".gitkeep":
            continue
        file_path = os.path.join(output_folder, filename)
        if not os.path.isfile(file_path):
            continue
        file_age = now - os.path.getmtime(file_path)
        if file_age > max_age_seconds:
            os.unlink(file_path)
            cleaned += 1
            logger.debug("Auto-cleanup: removed %s (age: %.0fs)", filename, file_age)
    return cleaned


def create_lifespan(
    output_folder: str, interval_seconds: int, max_age_seconds: int
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Create the FastAPI lifespan context for cleanup scheduling."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        cleanup_task = asyncio.create_task(
            cleanup_old_files(output_folder, interval_seconds, max_age_seconds)
        )
        logger.info(
            "Auto-cleanup background task started (interval: %ds, max age: %ds)",
            interval_seconds,
            max_age_seconds,
        )
        yield
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        logger.info("Auto-cleanup background task stopped")

    return lifespan
