import asyncio
import logging


logger = logging.getLogger(__name__)

async def execute_with_timeout(coroutine, timeout_seconds):
    if timeout_seconds is None:
        return await coroutine
    try:
        return await asyncio.wait_for(coroutine, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning("Query execution timed out")