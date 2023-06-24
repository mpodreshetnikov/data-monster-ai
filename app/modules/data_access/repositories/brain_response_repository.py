import logging
from ..models.brain_response_data import (
    BrainResponseData,
    BrainResponseType,
)
from sqlalchemy import select, and_
from modules.common.timeout_execution import execute_with_timeout

logger = logging.getLogger(__name__)


class BrainResponseRepository:
    def __init__(self, async_session, timeout_seconds):
        self.async_session = async_session
        self.timeout_seconds = timeout_seconds

    async def add(
        self,
        ray_id: str,
        question: str,
        answer: str | None = None,
        sql_script: str | None = None,
        type: BrainResponseType = BrainResponseType.SQL,
    ) -> BrainResponseData:
        async with self.async_session() as session:
            brain_response_data = BrainResponseData(
                user_request_ray_id=ray_id,
                type=type,
                question=question,
                sql_script=sql_script,
                answer=answer,
            )
            session.add(brain_response_data)
            await execute_with_timeout(session.commit(), self.timeout_seconds)
            await execute_with_timeout(
                session.refresh(brain_response_data), self.timeout_seconds
            )
            return brain_response_data

    async def update(self, brain_response_data: BrainResponseData):
        async with self.async_session() as session:
            await execute_with_timeout(
                session.merge(brain_response_data), self.timeout_seconds
            )
            await execute_with_timeout(session.commit(), self.timeout_seconds)

    async def get_last_brain_sql(self, ray_id: str) -> BrainResponseData | None:
        async with self.async_session() as session:
            result = await execute_with_timeout(
                session.execute(
                    select(BrainResponseData).where(
                        and_(
                            BrainResponseData.user_request_ray_id == ray_id,
                            BrainResponseData.type == BrainResponseType.SQL,
                        )
                    )
                ),
                self.timeout_seconds,
            )
            brain_responses_data = result.scalars().all()

            return brain_responses_data[-1] if brain_responses_data else None

    async def get_last_clarifying_question(
        self, ray_id: str
    ) -> BrainResponseData | None:
        async with self.async_session() as session:
            result = await execute_with_timeout(
                session.execute(
                    select(BrainResponseData)
                    .where(BrainResponseData.user_request_ray_id == ray_id)
                    .where(
                        BrainResponseData.type == BrainResponseType.CLARIFYING_QUESTION
                    )
                ),
                self.timeout_seconds,
            )
            brain_responses_data = result.scalars().all()

            return brain_responses_data[-1] if brain_responses_data else None
