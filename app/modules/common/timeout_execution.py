import asyncio
import logging
from typing import Coroutine, Any


logger = logging.getLogger(__name__)

async def execute_with_timeout(coroutine:Coroutine, timeout_seconds: int) -> Any:
    if timeout_seconds is None:
        return await coroutine
    try:
        return await asyncio.wait_for(coroutine, timeout=timeout_seconds)
    except asyncio.TimeoutError as e:
        logger.warning("Query execution timed out")
        raise e