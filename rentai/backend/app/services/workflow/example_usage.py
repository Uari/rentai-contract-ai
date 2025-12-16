# -*- coding: utf-8 -*-
"""
LangGraph 워크플로우 사용 예시

기존 FastAPI 엔드포인트에 LangGraph를 통합하는 방법을 보여줍니다.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from typing import Dict, Any

# LangGraph 워크플로우 import
from app.services.workflow.graph import run_analysis

app = FastAPI()


@app.post("/analyze/pdf/langgraph")
async def analyze_pdf_langgraph(
    file: UploadFile = File(...),
    use_ocr: bool = Query(False, description="OCR 사용 강제 (스캔본인 경우)"),
    k: int = Query(3, description="RAG 검색 개수 (Top-k)")
) -> Dict[str, Any]:
    """
    LangGraph를 사용한 계약서 분석 API
    
    기존 /analyze/pdf와 동일한 기능이지만 LangGraph 워크플로우로 구현됨
    """
    # 파일 읽기
    content = await file.read()
    
    try:
        # LangGraph 워크플로우 실행
        result = await run_analysis(
            file_content=content,
            filename=file.filename or "unknown",
            use_ocr=use_ocr,
            k=k
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


# ============================================================
# 기존 엔드포인트와의 비교
# ============================================================

"""
기존 방식 (fastapi_app.py의 analyze_pdf):
- 모든 로직이 하나의 함수에 300줄 이상
- 조건부 분기가 if-else로 복잡하게 얽혀있음
- 각 단계의 상태를 명시적으로 관리하지 않음
- 테스트하기 어려움
- 디버깅이 어려움

LangGraph 방식:
- 각 단계가 명확히 분리된 노드 함수
- 그래프로 워크플로우 시각화 가능
- 상태가 명시적으로 관리됨
- 각 노드를 독립적으로 테스트 가능
- LangGraph Studio로 시각화 및 디버깅 가능
- 에러 복구 (Durable Execution) 지원 가능
"""
