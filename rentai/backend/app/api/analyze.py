# ⚠️ 레거시 API 라우터 (미사용)
# 현재 공식 엔드포인트는 backend/fastapi_app.py 의 /analyze/pdf

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["analyze"])


@router.post("/analyze")
async def analyze_deprecated():
    """레거시 파이프라인 엔드포인트 - 사용 중단."""
    raise HTTPException(status_code=410, detail="/analyze/pdf (FastAPI v2) 엔드포인트를 사용하세요.")


@router.post("/analyze/pdf")
async def analyze_pdf_deprecated():
    """레거시 엔드포인트 - 사용 중단."""
    raise HTTPException(status_code=410, detail="backend/fastapi_app.py 에서 제공되는 /analyze/pdf 를 사용하세요.")