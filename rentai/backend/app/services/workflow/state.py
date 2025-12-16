# -*- coding: utf-8 -*-
"""
LangGraph 상태 정의
"""
from typing import TypedDict, List, Dict, Any, Optional
from typing_extensions import Annotated
from operator import add


class AnalysisState(TypedDict):
    """
    계약서 분석 워크플로우 상태
    
    모든 중간 결과와 최종 결과를 포함하는 상태 객체
    """
    # ========== 입력 파라미터 ==========
    file_content: bytes  # 업로드된 파일의 바이너리 데이터
    filename: str  # 파일명
    use_ocr: bool  # OCR 강제 사용 여부
    k: int  # RAG 검색 개수 (Top-k)
    
    # ========== 파일 처리 결과 ==========
    file_type: Optional[str]  # "image" | "pdf" | None
    text_full: str  # 추출된 전체 텍스트
    page_count: int  # 페이지 수
    sentences: List[Dict[str, Any]]  # 문장 리스트 [{"id": int, "page": int, "text": str}, ...]
    
    # ========== 추출 결과 ==========
    extracted_fields: Dict[str, Any]  # extract_all 결과
    tables: List[Any]  # 추출된 표 리스트
    signature_detected: bool  # 서명 감지 여부
    
    # ========== 분석 결과 ==========
    risk: Dict[str, Any]  # 룰 평가 결과
    issues: List[Dict[str, Any]]  # 이슈 리스트
    all_rag_refs: Annotated[List[Dict[str, Any]], add]  # 모든 RAG 참조 (자동 병합)
    
    # ========== 최종 결과 ==========
    result: Optional[Dict[str, Any]]  # 최종 API 응답 형식
    error: Optional[str]  # 에러 메시지
