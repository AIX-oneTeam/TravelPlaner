from pydantic import BaseModel
from typing import List
from fastapi import APIRouter

router = APIRouter()

class UserInputData(BaseModel) :
    location : str
    check_in_date : str
    check_out_date: str
    concepts: List[str]
    