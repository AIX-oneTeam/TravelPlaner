from typing import Optional

from pydantic import Field
from sqlmodel import SQLModel


class AdministrativeDivision(SQLModel, table=True):
    city_id: Optional[int] = Field(default=None, primary_key=True)
    city_province: str = Field(max_length=50)
    city_county: str = Field(max_length=50)
