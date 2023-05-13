from pydantic.dataclasses import dataclass


@dataclass
class UserNotAllowedException(Exception):
    method_name: str = None