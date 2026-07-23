from pydantic import BaseModel, EmailStr, Field


class UserRegistrationInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    full_name: str | None = Field(None, min_length=1, max_length=160)


class UserRegistrationOutput(BaseModel):
    message: str
    email: str


class UserLoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserLoginOutput(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserInfo"


class UserInfo(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    account_status: str
    email_verified: bool


class AccountStatusResponse(BaseModel):
    email: str
    account_status: str
    message: str
