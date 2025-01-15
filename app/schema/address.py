from pydantic import BaseModel

"""
_summary_ : 주소 스키마입니다. 식별자는 따로 없습니다.

"""
class Address(BaseModel):
    street: str
    dong: str
    si: str
    do: str
    zip: str
    country: str
