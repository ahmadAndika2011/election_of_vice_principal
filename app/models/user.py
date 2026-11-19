"""Model validasi; unique index dibuat di init_auth_indexes(), bukan Field()."""
import unicodedata
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CompleteProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=200)

    @field_validator("username")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = " ".join(unicodedata.normalize("NFKC", value).split())
        if not value or any(unicodedata.category(c).startswith("C") for c in value):
            raise ValueError("Username harus menggunakan nama lengkap yang valid.")
        if not any(c.isalpha() for c in value):
            raise ValueError("Username harus menggunakan nama lengkap.")
        return value


class UserCreate(BaseModel):
    # Dibentuk backend dari identitas Google yang telah diverifikasi.
    google_sub: str
    email: EmailStr
    username: str | None = None
    username_key: str | None = None
    created_at: datetime


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    username: str | None


def username_key(name: str) -> str:
    return unicodedata.normalize("NFKC", name).casefold()
