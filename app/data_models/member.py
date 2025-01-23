from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, date
from pydantic.functional_validators import field_validator
import phonenumbers

class Member(SQLModel, table=True):
    member_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(sa_column_kwargs={"length": 50})  # VARCHAR(50)
    email: str = Field(sa_column_kwargs={"length": 255})  # VARCHAR(255)
    access_token: str = Field(sa_column_kwargs={"length": 255})
    refresh_token: str = Field(sa_column_kwargs={"length": 255})
    oauth: str = Field(sa_column_kwargs={"length": 255})
    nickname: Optional[str] = Field(default=None, sa_column_kwargs={"length": 50})
    sex: Optional[str] = Field(default=None, sa_column_kwargs={"length": 10})
    picture_url: Optional[str] = Field(default=None, sa_column_kwargs={"length": 2083})
    birth: Optional[datetime] = None
    address: Optional[str] = Field(default=None, sa_column_kwargs={"length": 255})
    zip: Optional[str] = Field(default=None, sa_column_kwargs={"length": 10})
    phone_number: Optional[str] = Field(default=None, sa_column_kwargs={"length": 20})
    voice: Optional[str] = Field(default=None, sa_column_kwargs={"length": 255})
    role: Optional[str] = Field(default=None, sa_column_kwargs={"length": 10})
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

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