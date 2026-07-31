from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegistrationInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    full_name: str | None = Field(None, min_length=1, max_length=160)
    invitation_code: str = Field(min_length=5, max_length=64)

    @field_validator("password")
    @classmethod
    def require_strong_password(cls, value: str) -> str:
        if not all((
            any(character.islower() for character in value),
            any(character.isupper() for character in value),
            any(character.isdigit() for character in value),
            any(not character.isalnum() for character in value),
        )):
            raise ValueError("Password must include uppercase, lowercase, number, and symbol characters.")
        return value


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
