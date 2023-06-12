from typing import Any, Dict, List, Optional
from uuid import UUID
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult
from pydantic import Field
import time
import uuid


class LogLLMRayCallbackHandler(BaseCallbackHandler):
    log_path: str | None = None
    ray_id: str = ""
    sql_script: str | None = None
    was_sql_timeout_error: bool = False

    def __init__(self, log_path: str, ray_id:str) -> None:
        self.log_path = log_path
        self.ray_id = ray_id

    # comment: returned value may be None
    def get_sql_script(self) -> str:
        """
        Returns the SQL script.
        Note: It makes sense to call the method only after llm has completed.
        """
        return self.sql_script

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        if self.log_path:
            prompt = prompts[0]
            header_str = (
                f"\n-------------{time.asctime()}-{self.ray_id}-Prompt-------------\n"
            )
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(header_str)
                f.write(prompt)

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        if self.log_path:
            header_str = f"\n-------------{time.asctime()}-{self.ray_id}-LLM Responce-------------\n"
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(header_str)
                f.write(str(response))

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        if serialized["name"] == "query_sql_db":
            self.sql_script = input_str.strip()

    def on_tool_end(self, output: str, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> Any:
        if kwargs.get("name") == "query_sql_db":
            lower_output = output.lower()
            if "error" in lower_output and "timeout" in lower_output:
                self.was_sql_timeout_error = True
