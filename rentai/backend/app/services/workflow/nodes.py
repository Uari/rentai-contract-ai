# -*- coding: utf-8 -*-
"""
LangGraph 노드 함수들

각 노드는 AnalysisState를 받아서 수정하고 반환합니다.
"""
from typing import Dict, Any
from pathlib import Path
import sys

# 프로젝트 경로 설정
project_root = Path(__file__).resolve().parents[4]  # .../rentai
backend_root = project_root / "backend"
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
if str(backend_root) not in sys.path:
    sys.path.append(str(backend_root))

from app.services.parser_pdf.enhanced_parser import parse_pdf
from app.services.parser_pdf.table_extractor import extract_tables
from app.services.parser_pdf.sign_detection import detect_signature
from app.services.parser_pdf.ocr_extractor import is_image_file, is_pdf_file
from app.services.extractors.lease_fields import extract_all
from app.services.rules.rule_engine import evaluate_rules
from app.services.rag.retrieval import search as rag_search
from app.services.llm.issue_advisor import generate_issue_guide_async

# RULES_PATH
RULES_PATH = str(project_root / "rules" / "rules_v2.yml")

# Clova OCR (선택적)
try:
    from app.services.parser_pdf.naver_clova_ocr import extract_text_auto_clova
    CLOVA_OCR_AVAILABLE = True
except ImportError:
    CLOVA_OCR_AVAILABLE = False
    extract_text_auto_clova = None


def validate_file(state: Dict[str, Any]) -> Dict[str, Any]:
    """파일 검증"""
    ALLOWED_SUFFIX = (".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif")
    MAX_FILE_MB = 20
    
    filename = state.get("filename", "")
    file_content = state.get("file_content", b"")
    
    # 파일 확장자 체크
    if not filename.lower().endswith(ALLOWED_SUFFIX):
        state["error"] = f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(ALLOWED_SUFFIX)}"
        return state
    
    # 용량 체크
    size_mb = len(file_content) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        state["error"] = f"파일 용량 초과(최대 {MAX_FILE_MB}MB)"
        return state
    
    return state


def determine_file_type(state: Dict[str, Any]) -> Dict[str, Any]:
    """파일 타입 판별"""
    filename = state.get("filename", "")
    
    if is_image_file(filename):
        state["file_type"] = "image"
    elif is_pdf_file(filename):
        state["file_type"] = "pdf"
    else:
        state["file_type"] = None
        state["error"] = "지원하지 않는 파일 형식입니다."
    
    return state


def extract_with_ocr(state: Dict[str, Any]) -> Dict[str, Any]:
    """OCR을 사용한 텍스트 추출"""
    if not CLOVA_OCR_AVAILABLE or extract_text_auto_clova is None:
        state["error"] = "Clova OCR이 사용 불가능합니다. API 키를 확인하세요."
        return state
    
    try:
        file_content = state.get("file_content", b"")
        filename = state.get("filename", "")
        ocr_result = extract_text_auto_clova(file_content, filename)
        state["text_full"] = ocr_result.get("text", "")
        state["page_count"] = ocr_result.get("page_count", 0)
    except Exception as e:
        state["error"] = f"OCR 실패: {e}"
    
    return state


def extract_with_parser(state: Dict[str, Any]) -> Dict[str, Any]:
    """일반 PDF 파서를 사용한 텍스트 추출"""
    try:
        file_content = state.get("file_content", b"")
        parsed = parse_pdf(file_content)
        state["text_full"] = parsed.get("text_full", "")
        state["page_count"] = parsed.get("page_count", 0)
    except Exception as e:
        state["error"] = f"PDF 파싱 실패: {e}"
    
    return state


def check_scan(state: Dict[str, Any]) -> Dict[str, Any]:
    """스캔본 감지 (텍스트가 너무 적으면 스캔본으로 판단)"""
    text_full = state.get("text_full", "")
    
    # 텍스트가 100자 미만이면 스캔본으로 판단
    if len(text_full.strip()) < 100 and CLOVA_OCR_AVAILABLE:
        # OCR로 재시도
        return extract_with_ocr(state)
    
    return state


def prepare_sentences(state: Dict[str, Any]) -> Dict[str, Any]:
    """문장 분리"""
    text_full = state.get("text_full", "")
    
    # 간단한 문장 분리 (개행 기준)
    raw_sentences = [s.strip() for s in text_full.split('\n') if s.strip()]
    sentences = [
        {"id": i, "page": 1, "text": s} 
        for i, s in enumerate(raw_sentences)
    ]
    state["sentences"] = sentences
    
    return state


async def extract_fields(state: Dict[str, Any]) -> Dict[str, Any]:
    """필드 추출 (주소 LLM 보정 포함)"""
    text_full = state.get("text_full", "")
    sentences = state.get("sentences", [])
    
    try:
        extracted = extract_all(text_full, sentences)
        
        # 주소 LLM 보정
        if extracted.get("address", {}).get("value"):
            from app.services.llm.address_corrector import correct_address_async
            original_addr = extracted["address"]["value"]
            try:
                corrected_addr = await correct_address_async(original_addr, context_text=text_full)
                if corrected_addr and corrected_addr != original_addr:
                    extracted["address"]["value"] = corrected_addr
                    print(f"[Address] 보정: {original_addr} → {corrected_addr}")
            except Exception as e:
                print(f"[Address] LLM 보정 실패 (기본 보정 사용): {e}")
        
        state["extracted_fields"] = extracted
    except Exception as e:
        state["error"] = f"필드 추출 실패: {e}"
    
    return state


def extract_tables_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """표 추출"""
    file_content = state.get("file_content", b"")
    
    try:
        tables = extract_tables(file_content)
        state["tables"] = tables
    except Exception:
        state["tables"] = []
    
    return state


def detect_signature_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """서명 감지"""
    sentences = state.get("sentences", [])
    
    try:
        signature = detect_signature(sentences)
        state["signature_detected"] = signature
    except Exception:
        state["signature_detected"] = False
    
    return state


def evaluate_rules_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """룰 평가"""
    extracted_fields = state.get("extracted_fields", {})
    text_full = state.get("text_full", "")
    signature_detected = state.get("signature_detected", False)
    tables = state.get("tables", [])
    
    extras = {
        "signature_detected": signature_detected,
        "tables_found": len(tables)
    }
    
    try:
        risk = evaluate_rules(extracted_fields, text_full, extras, RULES_PATH)
        state["risk"] = risk
        state["issues"] = risk.get("issues", [])
    except Exception as e:
        state["error"] = f"룰 평가 실패: {e}"
    
    return state


async def process_issues(state: Dict[str, Any]) -> Dict[str, Any]:
    """이슈별 RAG 검색 및 LLM 가이드 생성"""
    issues = state.get("issues", [])
    extracted_fields = state.get("extracted_fields", {})
    k = state.get("k", 3)
    
    all_rag_refs = []
    processed_issues = []
    
    for issue in issues:
        # 1. RAG 검색
        base_q = issue.get("message", "") or issue.get("title", "")
        hint = ""
        
        conf_date_val = extracted_fields.get("confirmation_date", {}).get("value")
        if conf_date_val:
            hint += f" 확정일자:{conf_date_val}"
        
        rr_val = extracted_fields.get("resident_reported", {}).get("value")
        if rr_val is not None:
            hint += f" 전입신고:{rr_val}"
        
        query = f"{base_q} {hint} 임대차보호법 근거"
        refs = rag_search(query, k=k)
        issue["references"] = refs
        all_rag_refs.extend(refs)
        
        # 2. LLM 가이드 생성
        reasons = issue.get("reasons", [])
        description = ", ".join(reasons) if reasons else base_q
        
        guide_data = None
        if base_q and len(base_q) > 2:
            try:
                guide_data = await generate_issue_guide_async(base_q, description)
            except Exception as e:
                print(f"LLM Guide Error: {e}")
        
        # LLM 가이드가 없으면 fallback 가이드 사용
        if not guide_data:
            from app.services.llm.issue_guide_fallback import get_fallback_guide
            guide_data = get_fallback_guide(base_q, description)
            if guide_data:
                print(f"[Guide] Fallback 가이드 사용: {base_q}")
        
        if guide_data:
            issue["guide"] = guide_data
        
        processed_issues.append(issue)
    
    state["issues"] = processed_issues
    state["all_rag_refs"] = all_rag_refs
    
    return state


def format_result(state: Dict[str, Any]) -> Dict[str, Any]:
    """최종 결과 포맷팅"""
    filename = state.get("filename", "")
    page_count = state.get("page_count", 0)
    tables = state.get("tables", [])
    signature_detected = state.get("signature_detected", False)
    sentences = state.get("sentences", [])
    extracted_fields = state.get("extracted_fields", {})
    risk = state.get("risk", {})
    issues = state.get("issues", [])
    all_rag_refs = state.get("all_rag_refs", [])
    file_content = state.get("file_content", b"")
    size_mb = len(file_content) / (1024 * 1024)
    
    # Summary
    summary = {
        "filename": filename,
        "pages": page_count,
        "tables": len(tables),
        "signatures": 1 if signature_detected else 0,
    }
    
    # Fields
    fields = []
    field_mapping = {
        "confirmation_date": "확정일자",
        "resident_reported": "전입신고",
        "maintenance_fee": "관리비",
        "restoration_clause": "원상복구",
        "termination_penalty": "위약 조항",
        "rent": "보증금/월세",
        "period": "계약기간",
        "address": "주소",
    }
    
    # 숫자 포맷팅 헬퍼 함수
    def format_number(num):
        """숫자를 천단위 콤마로 포맷팅"""
        if num is None:
            return None
        try:
            return f"{int(num):,}"
        except (ValueError, TypeError):
            return str(num) if num else None
    
    for key, label in field_mapping.items():
        node = extracted_fields.get(key, {})
        if isinstance(node, dict):
            value = node.get("value")
            if value is not None:
                if isinstance(value, dict):
                    if key == "rent":
                        deposit = value.get('deposit')
                        monthly_rent = value.get('monthly_rent')
                        deposit_str = format_number(deposit) if deposit is not None else "0"
                        monthly_rent_str = format_number(monthly_rent) if monthly_rent is not None else "0"
                        val_str = f"보증금: {deposit_str} / 월세: {monthly_rent_str}"
                    elif key == "period":
                        val_str = f"{value.get('start', '')} ~ {value.get('end', '')}"
                    elif key == "maintenance_fee":
                        included = value.get("included")
                        if included is True:
                            val_str = "포함"
                        elif included is False:
                            val_str = "미포함"
                        else:
                            val_str = "미포함"  # None이거나 데이터 없을 때
                    else:
                        val_str = str(value)
                else:
                    val_str = str(value)
                fields.append({"label": label, "value": val_str})
    
    # Issues
    issues_list = []
    for issue in issues:
        issues_list.append({
            "code": issue.get("id") or issue.get("code", ""),
            "severity": issue.get("severity", "MED"),
            "message": issue.get("title") or issue.get("message", ""),
            "evidence": issue.get("reasons", []),
        })
    
    # RAG (중복 제거)
    seen_rag = set()
    rag_list = []
    for ref in all_rag_refs:
        ref_key = (ref.get("text", "")[:50], ref.get("source", ""))
        if ref_key not in seen_rag:
            seen_rag.add(ref_key)
            rag_list.append({
                "text": ref.get("text", ""),
                "source": ref.get("source", ""),
                "score": ref.get("score"),
            })
    
    state["result"] = {
        "summary": summary,
        "fields": fields,
        "issues": issues_list,
        "rag": rag_list,
        "file": filename,
        "size_mb": round(size_mb, 2),
        "page_count": page_count,
        "sentence_count": len(sentences),
        "tables_found": len(tables),
        "signature_detected": signature_detected,
        "preview_sentences": sentences[:5],
        "extracted_fields": extracted_fields,
        "risk": risk,
    }
    
    return state


def should_use_ocr(state: Dict[str, Any]) -> str:
    """OCR 사용 여부 결정"""
    file_type = state.get("file_type")
    use_ocr = state.get("use_ocr", False)
    
    if file_type == "image":
        return "ocr"  # 이미지는 항상 OCR
    elif file_type == "pdf" and use_ocr:
        return "ocr"  # PDF이지만 OCR 강제 사용
    else:
        return "parser"  # 일반 PDF 파서


def should_check_scan(state: Dict[str, Any]) -> str:
    """스캔본 체크 여부"""
    if state.get("error"):
        return "end"
    return "check_scan"
