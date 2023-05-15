from typing import Any, Dict, List
from uuid import UUID
from langchain.callbacks.base import BaseCallbackHandler
from pydantic import Field


class LogLLMPromptCallbackHandler(BaseCallbackHandler):
    log_path: str = Field()

    def __init__(self, log_path: str) -> None:
        self.log_path = log_path

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> Any:
        prompt = prompts[0]
        if self.log_path:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"\n------------------{parent_run_id}------------------\n")
                f.write(prompt)
        return prompt