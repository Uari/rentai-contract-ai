
from pydantic import BaseModel, Field, conint
from typing import List

class LeaseDoc(BaseModel):
    lessor: str = Field(..., description="임대인")
    lessee: str = Field(..., description="임차인")
    address: str
    deposit: conint(ge=0) = 0
    monthly_rent: conint(ge=0) = 0
    period_months: conint(ge=1) = 12
    special_terms: str = ""
    pages: List[str] = []
