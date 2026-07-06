from typing import Any, TypeVar, Generic

from pydantic import BaseModel

T = TypeVar("T")

class Result(BaseModel,Generic[T]):
    code: int = 0
    message: str = "success"
    data: T = None

    @classmethod
    def success(cls,data:T | None = None):
        return cls(code=200, message="success", data=data)