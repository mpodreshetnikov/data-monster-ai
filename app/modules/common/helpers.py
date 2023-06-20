from logging import getLogger, Logger
from typing import Coroutine, TypeVar, Any

__logger = getLogger(__name__)

T = TypeVar("T")
async def a_exec_no_raise(
    func: Coroutine[Any, Any, T],
    logger: Logger | None = None,
) -> T | None:
    if not func:
        raise ValueError("Func was not provided.")
    logger = logger or __logger
    try:
        return await func
    except Exception as e:
        logger.error(e, exc_info=True)
    return None