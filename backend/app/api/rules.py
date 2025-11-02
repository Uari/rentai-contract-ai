
from fastapi import APIRouter
from app.services.rule_engine.loader import current_rule_version

router = APIRouter(tags=["rules"])

@router.get("/rules/version")
def get_version():
    return {"rule_version": current_rule_version()}
