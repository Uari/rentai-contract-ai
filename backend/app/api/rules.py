from fastapi import APIRouter
from app.services.rules.loader import load_rules

router = APIRouter(tags=["rules"])

@router.get("/rules/version")
def get_version():
    """룰셋 버전 조회"""
    version, _ = load_rules()
    return {"rule_version": version}
