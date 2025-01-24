from datetime import datetime, time
from typing import List, Optional
import phonenumbers
from pydantic import field_validator
from sqlmodel import Field, Relationship, SQLModel

class AdministrativeDivision(SQLModel, table=True):
    __tablename__ = "administrative_division"
    id: int | None = Field(default=None, primary_key=True)
    city_province: str = Field(max_length=50)
    city_county: str = Field(max_length=50)

class Member(SQLModel, table=True):
    __tablename__ = "member"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(..., max_length=50, nullable=False)  # VARCHAR(50)
    email: str = Field(..., max_length=255)  # VARCHAR(255)
    access_token: str = Field(max_length=2083)
    refresh_token: str = Field(max_length=2083)
    oauth: str = Field(max_length=50)
    nickname: Optional[str] = Field(default=None, max_length=50)
    sex: Optional[str] = Field(default=None, max_length=10)
    picture_url: Optional[str] = Field(default=None, max_length=2083)
    birth: Optional[datetime] = None
    address: Optional[str] = Field(default=None, max_length=255)
    zip: Optional[str] = Field(default=None, max_length=10)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    voice: Optional[str] = Field(default=None, max_length=255)
    role: Optional[str] = Field(default=None, max_length=10)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    plans: List["Plan"] = Relationship(back_populates="member")


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

        
class Plan(SQLModel, table=True):
    __tablename__ = "plan"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = Field(default=None, max_length=255)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    main_location: Optional[str] = Field(default=None, max_length=50)
    ages: Optional[int] = None
    companion_count: Optional[int] = None
    concepts: Optional[str] = Field(default=None, max_length=255)
    member_id: int = Field(foreign_key="member.id")

    member: Member = Relationship(back_populates="plans")

    checklist: Optional["Checklist"] = Relationship(back_populates="plan")
    plan_spots: List["PlanSpotMap"] = Relationship(back_populates="plan")

class Spot(SQLModel, table=True):
    __tablename__ = "spot"
    id: Optional[int] = Field(default=None, primary_key=True)
    kor_name: str = Field(max_length=255)
    eng_name: Optional[str] = Field(default=None, max_length=255)
    description: str = Field(max_length=255)
    address: str = Field(max_length=255)
    zip: str = Field(max_length=10)
    url: Optional[str] = Field(default=None, max_length=2083)
    image_url: str = Field(max_length=2083)
    map_url: str = Field(max_length=2083)
    likes: Optional[int] = None
    satisfaction: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    spot_category: int
    phone_number: Optional[str] = Field(default=None, max_length=300)
    business_status: Optional[bool] = None
    business_hours: Optional[str] = Field(default=None, max_length=255)

    plan_spots: List["PlanSpotMap"] = Relationship(back_populates="spot")
    spot_tags: List["PlanSpotTagMap"] = Relationship(back_populates="spot")


class PlanSpotMap(SQLModel, table=True):
    __tablename__ = "plan_spot_map"
    plan_id: int = Field(foreign_key="plan.id", primary_key=True)
    spot_id: int = Field(foreign_key="spot.id", primary_key=True)
    day_x: int = Field(...)
    order: int = Field(...)
    spot_time: Optional[time] = Field(default=None)  # 시간 필드 추가

    plan: Plan = Relationship(back_populates="plan_spots")
    spot: Spot = Relationship(back_populates="plan_spots")

class SpotTag(SQLModel, table=True):
    __tablename__ = "spot_tag"
    id: Optional[int] = Field(default=None, primary_key=True)
    spot_tag: str = Field(max_length=255)

    spot_tags: List["PlanSpotTagMap"] = Relationship(back_populates="spot_tag")
    
class PlanSpotTagMap(SQLModel, table=True):
    __tablename__ = "plan_spot_tag_map"
    spot_id: int = Field(foreign_key="spot.id", primary_key=True)
    spot_tag_id: int = Field(foreign_key="spot_tag.id", primary_key=True)

    spot: Spot = Relationship(back_populates="spot_tags")
    spot_tag: SpotTag = Relationship(back_populates="spot_tags")

class Checklist(SQLModel, table=True):
    __tablename__ = "checklist"
    plan_id: int = Field(primary_key=True, foreign_key="plan.id")
    item: Optional[str] = Field(default=None, max_length=255)
    state: Optional[bool] = None

    plan: Plan = Relationship(back_populates="checklist")