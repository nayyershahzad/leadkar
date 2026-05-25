"""Shared test fixtures.

pytest-asyncio runs each test in its own event loop, but the app-level async
SQLAlchemy engine pools asyncpg connections bound to the loop that created them.
Dispose the pool after every test so the next test (new loop) gets fresh
connections instead of failing with "Event loop is closed".
"""

import pytest_asyncio

from app.db import engine


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()
