from pydantic.dataclasses import dataclass


def add_info_to_exception(e: Exception, key: str, value: str) -> Exception:
    e.args = (*e.args, f"{key}:{value}")
    return e


def get_info_from_exception(e: Exception, key: str) -> str | None:
    for arg in e.args:
        if isinstance(arg, str) and arg.startswith(f"{key}:"):
            return arg.split(":", 1)[1]
    return None


@dataclass
class BotAnswerExceptionBase(Exception):
    pass


@dataclass
class AgentLimitExceededAnswerException(BotAnswerExceptionBase):
    agent_work_text: str


@dataclass
class SQLTimeoutAnswerException(BotAnswerExceptionBase):
    pass


@dataclass
class CreatedNotWorkingSQLAnswerException(BotAnswerExceptionBase):
    pass


@dataclass
class NoDataReturnedFromDBAnswerException(BotAnswerExceptionBase):
    pass


@dataclass
class LLMContextExceededAnswerException(BotAnswerExceptionBase):
    pass