# -*- coding: utf-8 -*-
"""
LangGraph 워크플로우 그래프 구성
"""
from langgraph.graph import StateGraph, END
from typing import Dict, Any

from .state import AnalysisState
from .nodes import (
    validate_file,
    determine_file_type,
    extract_with_ocr,
    extract_with_parser,
    check_scan,
    prepare_sentences,
    extract_fields,
    extract_tables_node,
    detect_signature_node,
    evaluate_rules_node,
    process_issues,
    format_result,
    should_use_ocr,
    should_check_scan,
)


def create_analysis_graph():
    """
    계약서 분석 워크플로우 그래프 생성
    
    Returns:
        StateGraph: 구성된 LangGraph 그래프
    """
    # 그래프 생성
    workflow = StateGraph(AnalysisState)
    
    # 노드 추가
    workflow.add_node("validate_file", validate_file)
    workflow.add_node("determine_file_type", determine_file_type)
    workflow.add_node("extract_with_ocr", extract_with_ocr)
    workflow.add_node("extract_with_parser", extract_with_parser)
    workflow.add_node("check_scan", check_scan)
    workflow.add_node("prepare_sentences", prepare_sentences)
    workflow.add_node("extract_fields", extract_fields)
    workflow.add_node("extract_tables", extract_tables_node)
    workflow.add_node("detect_signature", detect_signature_node)
    workflow.add_node("evaluate_rules", evaluate_rules_node)
    workflow.add_node("process_issues", process_issues)
    workflow.add_node("format_result", format_result)
    
    # 엣지 추가 (워크플로우 정의)
    workflow.set_entry_point("validate_file")
    
    workflow.add_edge("validate_file", "determine_file_type")
    workflow.add_conditional_edges(
        "determine_file_type",
        should_use_ocr,
        {
            "ocr": "extract_with_ocr",
            "parser": "extract_with_parser",
        }
    )
    
    # 파서 사용 후 스캔본 체크
    workflow.add_conditional_edges(
        "extract_with_parser",
        should_check_scan,
        {
            "check_scan": "check_scan",
            "end": END,
        }
    )
    
    # OCR 또는 파서 완료 후 문장 분리
    workflow.add_edge("extract_with_ocr", "prepare_sentences")
    workflow.add_edge("check_scan", "prepare_sentences")
    
    # 병렬 처리: 필드 추출, 표 추출, 서명 감지
    workflow.add_edge("prepare_sentences", "extract_fields")
    workflow.add_edge("extract_fields", "extract_tables")
    workflow.add_edge("extract_tables", "detect_signature")
    
    # 룰 평가 및 이슈 처리
    workflow.add_edge("detect_signature", "evaluate_rules")
    workflow.add_edge("evaluate_rules", "process_issues")
    workflow.add_edge("process_issues", "format_result")
    workflow.add_edge("format_result", END)
    
    # 그래프 컴파일
    app = workflow.compile()
    
    return app


# 편의 함수: 동기 버전 (비동기 노드가 있어서 실제로는 async 필요)
async def run_analysis(file_content: bytes, filename: str, use_ocr: bool = False, k: int = 3) -> Dict[str, Any]:
    """
    분석 워크플로우 실행
    
    Args:
        file_content: 파일 바이너리 데이터
        filename: 파일명
        use_ocr: OCR 강제 사용 여부
        k: RAG 검색 개수
    
    Returns:
        최종 분석 결과
    """
    graph = create_analysis_graph()
    
    initial_state: AnalysisState = {
        "file_content": file_content,
        "filename": filename,
        "use_ocr": use_ocr,
        "k": k,
        "file_type": None,
        "text_full": "",
        "page_count": 0,
        "sentences": [],
        "extracted_fields": {},
        "tables": [],
        "signature_detected": False,
        "risk": {},
        "issues": [],
        "all_rag_refs": [],
        "result": None,
        "error": None,
    }
    
    result = await graph.ainvoke(initial_state)
    
    # 에러가 있으면 예외 발생
    if result.get("error"):
        raise Exception(result["error"])
    
    return result.get("result", {})
