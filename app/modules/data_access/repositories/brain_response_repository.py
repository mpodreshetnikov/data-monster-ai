import logging
from ..models.brain_response_data import BrainResponseData, BrainResponseType
from .i_repository import IRepository
from sqlalchemy import select
from modules.common.timeout_execution import execute_with_timeout


logger = logging.getLogger(__name__)


class BrainResponseRepository(IRepository):
    def __init__(self, async_session, timeout_seconds):
        self.async_session = async_session
        self.timeout_seconds = timeout_seconds

    async def add(
            self,
            ray_id: str,
            question: str,
            answer: str,
            sql_script: str | None = None,
            type: BrainResponseType = BrainResponseType.SQL
        ):
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

    async def update(self, id, new_data):
        async with self.async_session() as session:
            result = execute_with_timeout(
                session.execute(
                    select(BrainResponseData)
                    .where(BrainResponseData.id == id)
                ),
                self.timeout_seconds
            )
            brain_response_data = result.scalar_one_or_none()
            if brain_response_data:
                for attr, value in new_data.items():
                    setattr(brain_response_data, attr, value)
                await session.commit()


    async def get(self, ray_id):
        async with self.async_session() as session:
            result = await execute_with_timeout(
                session.execute(
                    select(BrainResponseData)
                    .where(BrainResponseData.user_request_ray_id == ray_id)
                    .limit(1)
                ),
                self.timeout_seconds
            )
            brain_response_data = result.scalar_one_or_none()
            return brain_response_data

    async def get_all(self, ray_id):
        async with self.async_session() as session:
            result = await execute_with_timeout(
                session.execute(
                    select(BrainResponseData)
                    .where(BrainResponseData.user_request_ray_id == ray_id)
                ),
                self.timeout_seconds
            )
            brain_responses_data = result.scalars().all()
                
            return brain_responses_data

    async def delete(self, id):
        async with self.async_session() as session:
            result = await execute_with_timeout(
                session.execute(
                    select(BrainResponseData)
                    .where(BrainResponseData.id == id)
                ),
                self.timeout_seconds
            )
            brain_response_data = result.scalar_one_or_none()
            session.delete(brain_response_data)
            await execute_with_timeout(session.commit(), self.timeout_seconds)

    async def get_last_clarifying_question(self, ray_id: str) -> BrainResponseData | None:
        async with self.async_session() as session:
            result = await execute_with_timeout(session.execute(
                    select(BrainResponseData)
                    .where(BrainResponseData.user_request_ray_id == ray_id)
                    .where(BrainResponseData.type == BrainResponseType.CLARIFYING_QUESTION)
            ), self.timeout_seconds)
            brain_responses_data = result.scalars().all()
            
            if brain_responses_data:
                return brain_responses_data[-1]
            
            return None
