from sqlmodel import Relationship, SQLModel, Field
from typing import List
from datetime import datetime, date
from pydantic.functional_validators import field_validator
import phonenumbers

class Member(SQLModel, table=True):
    member_id: int | None = Field(default=None, primary_key=True)
    name: str = Field(..., max_length=50, nullable=False)  # VARCHAR(50)
    email: str = Field(..., max_length=255)  # VARCHAR(255)
    access_token: str = Field(..., max_length=255)
    refresh_token: str = Field(..., max_length=255)
    oauth: str = Field(..., max_length=50)
    nickname: str | None = Field(default=None, max_length=50)
    sex: str | None = Field(default=None, max_length=10)
    picture_url: str | None = Field(default=None, max_length=2083)
    birth: date | None = Field(default=None)
    address: str | None = Field(default=None, max_length=255)
    zip: str | None = Field(default=None, max_length=10)
    phone_number: str | None = Field(default=None, max_length=20)
    voice: str | None = Field(default=None, max_length=255)
    role: str | None = Field(default=None, max_length=10)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    # 전화번호 유효성 검사
    @field_validator("phone_number")
    def check_phone_number(cls, values):
        phone_number = values.get('phone_number')
        try:
            parsed_number = phonenumbers.is_valid_number(phone_number)
            if not parsed_number:
                raise ValueError(f"Invalid phone number: {phone_number}")
        except phonenumbers.phonenumberutil.NumberParseException as e:
            raise ValueError(f"Invalid phone number: {phone_number}") from e
        return values