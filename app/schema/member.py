"""__summary__ : 회원 스키마입니다. 식별자는 id입니다."""
from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import Optional
from datetime import datetime, date
from pydantic.functional_validators import field_validator
import phonenumbers

class Member(BaseModel):
    member_id: Optional[int] = Field(None, description="Member ID")
    name: str = Field(..., max_length=50, description="Name of the member")
    email: EmailStr = Field(..., description="Email address")
    access_token: str = Field(..., max_length=255, description="Access token")
    refresh_token: str = Field(..., max_length=255, description="Refresh token")
    oauth: str = Field(..., max_length=255, description="OAuth provider")
    nickname: Optional[str] = Field(None, max_length=50, description="Nickname")
    sex: Optional[str] = Field(None, max_length=10, description="Sex")
    picture_url: Optional[HttpUrl] = Field(None, description="Picture URL")
    birth: Optional[date] = Field(None, description="Date of birth")
    address: Optional[str] = Field(None, max_length=255, description="Address")
    zip: Optional[str] = Field(None, max_length=10, description="Zip code")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
    voice: Optional[str] = Field(None, max_length=255, description="Voice data")
    role: Optional[str] = Field(None, max_length=10, description="Role")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")

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
