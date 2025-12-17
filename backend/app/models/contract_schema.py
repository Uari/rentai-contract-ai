from pydantic import BaseModel, Field, conint
from typing import List, Dict, Any, Optional

class LeaseDoc(BaseModel):
    lessor: str = Field(..., description="임대인")
    lessee: str = Field(..., description="임차인")
    address: str
    deposit: conint(ge=0) = 0
    monthly_rent: conint(ge=0) = 0
    period_months: conint(ge=1) = 12
    special_terms: str = ""
    pages: List[str] = []

class Issue(BaseModel):
    code: str
    severity: str  # HIGH | MED | LOW
    message: str
    evidence: List[Dict[str, Any]] = []

class FieldItem(BaseModel):
    label: str
    value: Optional[str] = None
    evidence: List[Dict[str, Any]] = []

class Summary(BaseModel):
    filename: str
    pages: int
    tables: int
    signatures: int
    extracted_by: str

class AnalysisResult(BaseModel):
    summary: Summary
    fields: List[FieldItem]
    issues: List[Issue]
    rag: List[Dict[str, Any]]  # {text, source, score}
