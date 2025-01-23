from datetime import datetime
import phonenumbers
from pydantic import BaseModel, EmailStr, Field, field_validator

from schema.address import Address

"""_summary_: 카드 정보 스키마입니다. 식별자는 따로 없습니다.
"""
class CreditCardInfo(BaseModel):
    card_number: str
    expiry_date: str
    cvv: str
    cardholder_name: str
    

"""__summary__ : 회원 스키마입니다. 식별자는 id입니다.
"""
class Member(BaseModel):
    id: int
    name: str
    email: EmailStr # 이메일 형식 유효성 검사(pydantic)
    # password: str
    nickname: str
    birth_day: int
    address: Address
    phone_number: str
    # voice: str #논의 필요
    credit: CreditCardInfo

    planId: list[int]

    role: str
    created_at: datetime
    updated_at: datetime


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