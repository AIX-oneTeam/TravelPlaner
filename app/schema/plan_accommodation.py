import enum
import phonenumbers
from pydantic import BaseModel, field_validator

from schema import PlanCommon

class AccomodationType(enum):
    HOTEL = "호텔"
    MOTEL = "모텔"
    GUESTHOUSE = "게스트하우스"
    HOSTEL = "호스텔"
    PENSION = "펜션"
    RESORT = "리조트"
    CONDO = "콘도"
    INN = "여관"
    RYOKAN = "료칸"
    HANOK = "한옥"
    CAMP = "캠핑"
    GLAMPING = "글램핑"
    


class Accommodation(BaseModel, PlanCommon):
    id: int
    accommodation_type: AccomodationType
    phone_number: str
    business_status: str  # 영업 상태
    business_hours: str  # 영업 시간


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
        
    
    
