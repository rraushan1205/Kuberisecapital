from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class ClientLoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class ClientSessionOutput(BaseModel):
    user_id: UUID
    email: EmailStr
    account_status: str
