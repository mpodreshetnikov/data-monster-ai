from typing import Optional
from ..models.user_request import UserRequest


class IRepository:
    async def add(
        self, ray_id: int, timestamp: str, username: str, user_id: int
    ) -> None:
        raise NotImplementedError

    async def update(self, ray_id: int, new_data: dict) -> None:
        raise NotImplementedError

    async def get(self, user_id: int) -> Optional[UserRequest]:
        raise NotImplementedError

    async def delete(self, user_id: int) -> None:
        raise NotImplementedError
