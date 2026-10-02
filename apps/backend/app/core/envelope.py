from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Meta(BaseModel):
    page: int | None = None
    per_page: int | None = None
    total: int | None = None


class Envelope(BaseModel, Generic[T]):
    """Every JSON response: {"success", "data", "meta", "errors"}."""

    success: bool = True
    data: T
    meta: Meta | None = None
    errors: list[dict[str, Any]] = []


class Page(BaseModel):
    page: int = 1
    per_page: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def ok(data: Any, meta: Meta | None = None) -> Envelope:
    return Envelope(data=data, meta=meta)
