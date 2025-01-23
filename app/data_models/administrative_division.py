from typing import Optional

from pydantic import Field


class AdministrativeDivision(SQLModel, table=True):
    city_id: Optional[int] = Field(default=None, primary_key=True)
    city_province: str = Field(sa_column_kwargs={"length": 50})
    city_county: str = Field(sa_column_kwargs={"length": 50})
