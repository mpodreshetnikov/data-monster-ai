from typing import Any, Dict, List, Optional
from uuid import UUID
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult
from pydantic import Field
import time
import uuid
from modules.data_access.models.brain_response_data import BrainResponseData
from os import urandom


class LogLLMRayCallbackHandler(BaseCallbackHandler):
    log_path: str = Field()
    ray_id: str = Field()
    brain_response_data: BrainResponseData = BrainResponseData()

    def __init__(self, log_path: str) -> None:
        self.log_path = log_path
        self.ray_id = str(uuid.uuid4())

    def get_ray_str(self) -> str:
        return self.ray_id

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> Any:
        if self.log_path:
            prompt = prompts[0]
            header_str = f"\n-------------{time.asctime()}-{self.ray_id}-Prompt-------------\n"
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(header_str)
                f.write(prompt)

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> Any:
        if self.log_path:
            header_str = f"\n-------------{time.asctime()}-{self.ray_id}-LLM Responce-------------\n"
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(header_str)
                f.write(str(response))

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any,) -> None:
        if serialized['name'] == 'query_sql_db':
            self.brain_response_data.ray_id = self.ray_id
            self.brain_response_data.sql_script = input_str