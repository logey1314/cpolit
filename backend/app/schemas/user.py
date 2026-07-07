from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    external_user_id: str | None = None
    phone: str | None = None
    name: str | None = None
    source: str | None = None
    tags: list[str] | None = None
    purchase_status: str | None = None
    operation_status: str | None = None
    merged_user_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class UserPageOut(BaseModel):
    total: int
    items: list[UserOut]

class UserImportIn(BaseModel):
    external_user_id: str | None = None
    phone: str | None = None
    name: str | None = None
    source: str | None = None
    tags: list[str] | None = None
    purchase_status: str | None = None
    operation_status: str | None = None

class UserImportRequest(BaseModel):
    source: str | None = None
    users: list[UserImportIn]

class UserImportError(BaseModel):
    index: int
    message: str

class UserImportResult(BaseModel):
    imported_count: int
    errors: list[UserImportError] = []

class UserIdentityGroupOut(BaseModel):
    main_user: UserOut
    records: list[UserOut]