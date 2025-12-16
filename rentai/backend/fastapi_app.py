from pathlib import Path
import sys

# ============================================================
# ✅ 프로젝트 경로 설정 (⚠️ 반드시 상단에 위치해야 함)
# ============================================================
# 현재 파일 = rentai/backend/fastapi_app.py
project_root = Path(__file__).resolve().parents[1]   # .../rentai
backend_root  = project_root / "backend"

# Report/PDF 생성 모듈, backend 패키지 인식되도록 경로 추가
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
if str(backend_root) not in sys.path:
    sys.path.append(str(backend_root))

# 룰셋 경로 (전역 상수)
RULES_PATH = str(project_root / "rules" / "rules_v2.yml")

# ============================================================
# ✅ FastAPI & 서비스 import
# ============================================================
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List
import io
import base64

from app.services.parser_pdf.enhanced_parser import parse_pdf
from app.services.parser_pdf.table_extractor import extract_tables
from app.services.parser_pdf.sign_detection import detect_signature
from app.services.extractors.lease_fields import extract_all
from app.services.rules.rule_engine import evaluate_rules
from report.generator import generate_pdf_bytes   # ✅ report/ 폴더 인식됨
from app.services.rag.retrieval import search, RULE_HINTS, stats  # stats 임포트

# RAG 관련 모듈
from app.services.rag.retrieval import search as rag_search
from app.services.rag.retrieval import RULE_HINTS
from app.services.rag.retrieval import search as law_search
from app.services.rag.retrieval import kb_status as kb_status_fn, search as rag_search

# OCR 관련 import
from app.services.parser_pdf.ocr_extractor import (
    extract_text_auto,
    is_image_file,
    is_pdf_file,
    OCR_AVAILABLE,
    PDF2IMAGE_AVAILABLE
)

# Naver Clova OCR import (최고 정확도)
try:
    from app.services.parser_pdf.naver_clova_ocr import (
        extract_text_auto_clova,
        check_api_credentials as check_clova_credentials
    )
    # API 키 확인
    try:
        check_clova_credentials()
        CLOVA_OCR_AVAILABLE = True
    except:
        CLOVA_OCR_AVAILABLE = False
except ImportError:
    CLOVA_OCR_AVAILABLE = False

# ============================================================
# ✅ 앱 설정
# ============================================================
MAX_FILE_MB = 20
ALLOWED_SUFFIX = (".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif")

app = FastAPI(title="RentAI Parser API", version="0.1.0")

# CORS (Streamlit/웹 연동 대비)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ============================================================
# ✅ 헬스 체크
# ============================================================
@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}

# ============================================================
# ✅ 분석 API (텍스트 + 필드 + 룰 평가)
# ============================================================
@app.post("/analyze/pdf")
async def analyze_pdf(
    file: UploadFile = File(...), 
    use_ocr: bool = Query(False, description="OCR 사용 강제 (스캔본인 경우)"),
    k: int = Query(3, description="RAG 검색 개수 (Top-k)")
) -> Dict[str, Any]:
    """
    임대차 계약서 분석 API (PDF, 이미지 지원)
    
    - 이미지 파일: 자동으로 Clova OCR 사용
    - PDF 파일: 일반 파서 사용 (use_ocr=true면 Clova OCR 사용)
    - 스캔본 PDF: 자동으로 Clova OCR로 fallback
    """
    # 🔍 파일명 체크
    if not file.filename.lower().endswith(ALLOWED_SUFFIX):
        raise HTTPException(
            status_code=400, 
            detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(ALLOWED_SUFFIX)}"
        )

    # 🔍 용량 제한
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(status_code=413, detail=f"파일 용량 초과(최대 {MAX_FILE_MB}MB)")

    # 🔍 파일 타입 판별 및 텍스트 추출
    from app.services.parser_pdf.ocr_extractor import is_image_file, is_pdf_file
    
    text_full = ""
    page_count = 0
    
    # 이미지 파일이면 Clova OCR 사용
    if is_image_file(file.filename):
        if CLOVA_OCR_AVAILABLE:
            try:
                ocr_result = extract_text_auto_clova(content, file.filename)
                text_full = ocr_result['text']
                page_count = ocr_result['page_count']
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"이미지 OCR 실패: {e}")
        else:
            raise HTTPException(
                status_code=503, 
                detail="이미지 파일은 Clova OCR이 필요합니다. .env에 API 키를 설정하세요."
            )
    # PDF 파일
    elif is_pdf_file(file.filename):
        # OCR 강제 사용 또는 스캔본 감지
        if use_ocr:
            if CLOVA_OCR_AVAILABLE:
                try:
                    ocr_result = extract_text_auto_clova(content, file.filename)
                    text_full = ocr_result['text']
                    page_count = ocr_result['page_count']
                except Exception as e:
                    raise HTTPException(status_code=422, detail=f"PDF OCR 실패: {e}")
            else:
                raise HTTPException(
                    status_code=503,
                    detail="OCR 사용을 위해서는 Clova OCR API 키가 필요합니다."
                )
        else:
            # 일반 PDF 파싱 시도
            try:
                parsed = parse_pdf(content)
                text_full = parsed["text_full"]
                page_count = parsed["page_count"]
                
                # 추출된 텍스트가 너무 적으면 스캔본일 가능성 → Clova OCR로 재시도
                if len(text_full.strip()) < 100 and CLOVA_OCR_AVAILABLE:
                    try:
                        ocr_result = extract_text_auto_clova(content, file.filename)
                        text_full = ocr_result['text']
                        page_count = ocr_result['page_count']
                    except:
                        pass  # OCR 실패해도 원본 텍스트 사용
            except Exception as e:
                # 일반 파싱 실패 → Clova OCR 시도
                if CLOVA_OCR_AVAILABLE:
                    try:
                        ocr_result = extract_text_auto_clova(content, file.filename)
                        text_full = ocr_result['text']
                        page_count = ocr_result['page_count']
                    except Exception as ocr_err:
                        raise HTTPException(status_code=422, detail=f"텍스트 추출 실패: PDF 파싱 실패 ({e}), OCR도 실패 ({ocr_err})")
                else:
                    raise HTTPException(status_code=422, detail=f"텍스트 파싱 실패: {e}")
    else:
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")
    
    # 문장 분리 (parsed 객체가 없으므로 직접 처리)
    # extract_all 함수는 딕셔너리 리스트 형식을 기대함 (id, page, text 필드 필요)
    raw_sentences = [s.strip() for s in text_full.split('\n') if s.strip()]
    sentences = [{"id": i, "page": 1, "text": s} for i, s in enumerate(raw_sentences)]

    extracted = extract_all(text_full, sentences)
    
    # 주소 LLM 보정 (비동기)
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

    # 표 추출
    try:
        tables = extract_tables(content)
    except Exception:
        tables = []

    # 서명 감지
    try:
        signature = detect_signature(sentences)
    except Exception:
        signature = False

    # ✅ 룰 평가
    extras = {"signature_detected": signature, "tables_found": len(tables)}
    risk = evaluate_rules(extracted, text_full, extras, RULES_PATH)

    # 룰 엔진 결과에 법령 근거 인용 붙이기 + LLM 가이드 생성
    from app.services.llm.issue_advisor import generate_issue_guide_async
    
    issues = risk.get("issues", [])
    all_rag_refs = []  # 모든 RAG 참조 수집
    
    # 비동기 처리를 위해 이슈 처리 로직 개선
    processed_issues = []
    
    for issue in issues:
        # 1. RAG 검색 (기존 로직)
        base_q = issue.get("message", "") or issue.get("title", "")
        hint = ""
        conf_date_val = extracted.get("confirmation_date", {}).get("value")
        if conf_date_val:
            hint += f" 확정일자:{conf_date_val}"
        rr_val = extracted.get("resident_reported", {}).get("value")
        if rr_val is not None:
            hint += f" 전입신고:{rr_val}"

        query = f"{base_q} {hint} 임대차보호법 근거"
        refs = law_search(query, k=k)
        issue["references"] = refs
        all_rag_refs.extend(refs)
        
        # 2. LLM 가이드 생성 (비동기 호출)
        # 상세 설명을 위한 텍스트 조합
        reasons = issue.get("reasons", [])
        description = ", ".join(reasons) if reasons else base_q
        
        guide_data = None
        try:
            # 룰 코드가 있거나 타이틀이 명확한 경우만 호출 (불필요한 호출 방지)
            if base_q and len(base_q) > 2:
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
            # 가이드 정보를 이슈 객체에 추가 (프론트엔드에서 사용)
            issue["guide"] = guide_data
            
        processed_issues.append(issue)

    risk["issues"] = processed_issues

    # 프론트엔드 기대 형식으로 변환
    # 1. summary 생성
    summary = {
        "filename": file.filename,
        "pages": page_count,
        "tables": len(tables),
        "signatures": 1 if signature else 0,
    }

    # 2. fields 리스트 생성 (extracted_fields 변환)
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
        node = extracted.get(key, {})
        if isinstance(node, dict):
            value = node.get("value")
            if value is not None:
                # 중첩 구조 처리 (rent, period, maintenance_fee)
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

    # 3. issues 리스트 생성 (risk.issues 변환)
    issues_list = []
    for issue in issues:
        issues_list.append({
            "code": issue.get("id") or issue.get("code", ""),
            "severity": issue.get("severity", "MED"),
            "message": issue.get("title") or issue.get("message", ""),
            "evidence": issue.get("reasons", []),  # reasons를 evidence로 매핑
        })

    # 4. rag 리스트 생성 (중복 제거)
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

    return {
        "summary": summary,
        "fields": fields,
        "issues": issues_list,
        "rag": rag_list,
        # 하위 호환을 위한 원본 데이터도 포함
        "file": file.filename,
        "size_mb": round(size_mb, 2),
        "page_count": page_count,
        "sentence_count": len(sentences),
        "tables_found": len(tables),
        "signature_detected": signature,
        "preview_sentences": sentences[:5],
        "extracted_fields": extracted,
        "risk": risk,
    }

# ============================================================
# ✅ LangGraph 기반 분석 API (새로운 워크플로우)
# ============================================================
@app.post("/analyze/pdf/langgraph")
async def analyze_pdf_langgraph(
    file: UploadFile = File(...),
    use_ocr: bool = Query(False, description="OCR 사용 강제 (스캔본인 경우)"),
    k: int = Query(3, description="RAG 검색 개수 (Top-k)")
) -> Dict[str, Any]:
    """
    LangGraph 워크플로우를 사용한 계약서 분석 API
    
    기존 /analyze/pdf와 동일한 기능이지만 LangGraph로 구조화된 워크플로우를 사용합니다.
    - 각 단계가 명확히 분리된 노드로 구성
    - 상태 관리가 명시적
    - 디버깅 및 모니터링 용이
    """
    try:
        from app.services.workflow.graph import run_analysis
        
        # 파일 읽기
        content = await file.read()
        
        # LangGraph 워크플로우 실행
        result = await run_analysis(
            file_content=content,
            filename=file.filename or "unknown",
            use_ocr=use_ocr,
            k=k
        )
        return result
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"LangGraph 모듈을 불러올 수 없습니다: {e}. langgraph 패키지가 설치되어 있는지 확인하세요."
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"분석 실패: {str(e)}")

# ============================================================
# ✅ 리포트 생성 + 다운로드 (PDF/이미지 지원)
# ============================================================
@app.post("/report/pdf")
async def report_pdf(file: UploadFile = File(...), use_ocr: bool = Query(False, description="OCR 사용 강제")):
    """
    분석 리포트 생성 (PDF/이미지 모두 지원)
    """
    # 파일명 체크
    if not file.filename.lower().endswith(ALLOWED_SUFFIX):
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(ALLOWED_SUFFIX)}"
        )
    
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    
    # 파일 타입 판별 및 텍스트 추출
    from app.services.parser_pdf.ocr_extractor import is_image_file, is_pdf_file
    
    text_full = ""
    page_count = 0
    
    # 이미지 파일이면 Clova OCR 사용
    if is_image_file(file.filename):
        if CLOVA_OCR_AVAILABLE:
            try:
                ocr_result = extract_text_auto_clova(content, file.filename)
                text_full = ocr_result['text']
                page_count = ocr_result['page_count']
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"이미지 OCR 실패: {e}")
        else:
            raise HTTPException(
                status_code=503,
                detail="이미지 파일은 Clova OCR이 필요합니다."
            )
    # PDF 파일
    elif is_pdf_file(file.filename):
        if use_ocr:
            if CLOVA_OCR_AVAILABLE:
                try:
                    ocr_result = extract_text_auto_clova(content, file.filename)
                    text_full = ocr_result['text']
                    page_count = ocr_result['page_count']
                except Exception as e:
                    raise HTTPException(status_code=422, detail=f"PDF OCR 실패: {e}")
            else:
                raise HTTPException(status_code=503, detail="OCR 사용을 위해서는 Clova OCR API 키가 필요합니다.")
        else:
            try:
                parsed = parse_pdf(content)
                text_full = parsed["text_full"]
                page_count = parsed["page_count"]
                
                # 스캔본 감지 및 자동 OCR
                if len(text_full.strip()) < 100 and CLOVA_OCR_AVAILABLE:
                    try:
                        ocr_result = extract_text_auto_clova(content, file.filename)
                        text_full = ocr_result['text']
                        page_count = ocr_result['page_count']
                    except:
                        pass
            except Exception as e:
                if CLOVA_OCR_AVAILABLE:
                    try:
                        ocr_result = extract_text_auto_clova(content, file.filename)
                        text_full = ocr_result['text']
                        page_count = ocr_result['page_count']
                    except Exception as ocr_err:
                        raise HTTPException(status_code=422, detail=f"텍스트 추출 실패: {e}, OCR도 실패: {ocr_err}")
                else:
                    raise HTTPException(status_code=422, detail=f"텍스트 파싱 실패: {e}")
    else:
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")
    
    # 문장 분리
    raw_sentences = [s.strip() for s in text_full.split('\n') if s.strip()]
    sentences = [{"id": i, "page": 1, "text": s} for i, s in enumerate(raw_sentences)]

    try:
        tables = extract_tables(content)
    except Exception:
        tables = []
    try:
        signature = detect_signature(sentences)
    except Exception:
        signature = False

    extracted = extract_all(text_full, sentences)
    
    # 주소 LLM 보정 (비동기)
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

    extras = {"signature_detected": signature, "tables_found": len(tables)}
    risk = evaluate_rules(extracted, text_full, extras, RULES_PATH)

    # 룰 엔진 결과에 법령 근거 인용 붙이기 + LLM 가이드 생성
    from app.services.llm.issue_advisor import generate_issue_guide_async
    
    issues = risk.get("issues", [])
    all_rag_refs = []  # 모든 RAG 참조 수집
    
    # 비동기 처리를 위해 이슈 처리 로직 개선
    processed_issues = []
    
    for issue in issues:
        # 1. RAG 검색 (기존 로직)
        base_q = issue.get("message", "") or issue.get("title", "")
        hint = ""
        conf_date_val = extracted.get("confirmation_date", {}).get("value")
        if conf_date_val:
            hint += f" 확정일자:{conf_date_val}"
        
        query = f"{base_q} {hint} 임대차보호법 근거"
        refs = law_search(query, k=3)
        issue["references"] = refs
        all_rag_refs.extend(refs)
        
        # 2. LLM 가이드 생성 (비동기 호출)
        # 상세 설명을 위한 텍스트 조합
        reasons = issue.get("reasons", [])
        description = ", ".join(reasons) if reasons else base_q
        
        guide_data = None
        try:
            # 룰 코드가 있거나 타이틀이 명확한 경우만 호출 (불필요한 호출 방지)
            if base_q and len(base_q) > 2:
                guide_data = await generate_issue_guide_async(base_q, description)
        except Exception as e:
            print(f"LLM Guide Error: {e}")
            
        if guide_data:
            # LLM이 생성한 가이드 정보를 이슈 객체에 추가 (프론트엔드에서 사용)
            issue["guide"] = guide_data
            
        processed_issues.append(issue)

    risk["issues"] = processed_issues

    context = {
        "file": file.filename,
        "page_count": page_count,
        "sentence_count": len(sentences),
        "tables_found": len(tables),
        "signature_detected": signature,
        "extracted_fields": extracted,
        "preview_sentences": sentences[:5],
        "risk": risk,
    }

    pdf_bytes = generate_pdf_bytes(context)
    return StreamingResponse(io.BytesIO(pdf_bytes),
                             media_type="application/pdf",
                             headers={"Content-Disposition": 'attachment; filename="analysis_report.pdf"'})

# @app.get("/reference/law")
# def reference_law(q: str, k: int = 3):
#     try:
#         return rag_search(q, k=k)
#     except Exception as e:
#         raise HTTPException(status_code=503, detail=f"KB not ready: {e}")

@app.get("/reference/debug")
def kb_debug():
    return stats()

# (중간) 앱/미들웨어 정의 아래에 디버그/도움용 엔드포인트 추가

@app.get("/kb/status")
def api_kb_status() -> Dict[str, Any]:
    """Chroma 상태 확인 (count, 경로)"""
    return kb_status_fn()

@app.get("/reference/law")
def api_reference_law(q: str = Query(..., description="검색어"), k: int = 3) -> List[Dict[str, Any]]:
    """RAG 검색(간단 확인용)"""
    return rag_search(q, k=k)

# ============================================================
# ✅ PDF 텍스트 추출 API (텍스트만 조회)
# ============================================================
@app.post("/extract/pdf-text")
async def extract_pdf_text(
    file: UploadFile = File(...),
    format: str = Query("full", description="반환 형식: 'full'(전체), 'pages'(페이지별), 'sentences'(문장별)"),
    use_ocr: bool = Query(False, description="OCR 사용 강제")
) -> Dict[str, Any]:
    """
    PDF/이미지에서 텍스트만 추출하여 반환
    
    - format='full': 전체 텍스트를 하나의 문자열로 반환
    - format='pages': 페이지별로 분리하여 반환
    - format='sentences': 문장별로 분리하여 반환
    """
    # 파일명 체크
    if not file.filename.lower().endswith(ALLOWED_SUFFIX):
        raise HTTPException(
            status_code=400, 
            detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(ALLOWED_SUFFIX)}"
        )
    
    # 용량 제한
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(status_code=413, detail=f"파일 용량 초과(최대 {MAX_FILE_MB}MB)")
    
    # 파일 타입 판별 및 텍스트 추출
    from app.services.parser_pdf.ocr_extractor import is_image_file, is_pdf_file
    
    text_full = ""
    page_count = 0
    parsed = None
    
    # 이미지 파일이면 Clova OCR 사용
    if is_image_file(file.filename):
        if CLOVA_OCR_AVAILABLE:
            try:
                ocr_result = extract_text_auto_clova(content, file.filename)
                text_full = ocr_result['text']
                page_count = ocr_result['page_count']
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"이미지 OCR 실패: {e}")
        else:
            raise HTTPException(status_code=503, detail="이미지 파일은 Clova OCR이 필요합니다.")
    # PDF 파일
    elif is_pdf_file(file.filename):
        if use_ocr:
            if CLOVA_OCR_AVAILABLE:
                try:
                    ocr_result = extract_text_auto_clova(content, file.filename)
                    text_full = ocr_result['text']
                    page_count = ocr_result['page_count']
                except Exception as e:
                    raise HTTPException(status_code=422, detail=f"PDF OCR 실패: {e}")
            else:
                raise HTTPException(status_code=503, detail="OCR 사용을 위해서는 Clova OCR API 키가 필요합니다.")
        else:
            try:
                parsed = parse_pdf(content)
                text_full = parsed["text_full"]
                page_count = parsed["page_count"]
                
                # 스캔본 감지 및 자동 OCR
                if len(text_full.strip()) < 100 and CLOVA_OCR_AVAILABLE:
                    try:
                        ocr_result = extract_text_auto_clova(content, file.filename)
                        text_full = ocr_result['text']
                        page_count = ocr_result['page_count']
                        parsed = None  # OCR 사용 시 parsed는 None
                    except:
                        pass
            except Exception as e:
                if CLOVA_OCR_AVAILABLE:
                    try:
                        ocr_result = extract_text_auto_clova(content, file.filename)
                        text_full = ocr_result['text']
                        page_count = ocr_result['page_count']
                        parsed = None
                    except Exception as ocr_err:
                        raise HTTPException(status_code=422, detail=f"텍스트 추출 실패: {e}, OCR도 실패: {ocr_err}")
                else:
                    raise HTTPException(status_code=422, detail=f"텍스트 파싱 실패: {e}")
    else:
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")
    
    # OCR을 사용한 경우 (parsed가 None) 문장 분리
    if parsed is None:
        raw_sentences = [s.strip() for s in text_full.split('\n') if s.strip()]
        sentences = [{"id": i, "page": 1, "text": s} for i, s in enumerate(raw_sentences)]
        pages = [{"page": 1, "text": text_full}]
        sentence_count = len(sentences)
    else:
        sentences = parsed["sentences"]
        pages = parsed["pages"]
        sentence_count = parsed["sentence_count"]
    
    # 형식에 따라 반환
    if format == "pages":
        return {
            "filename": file.filename,
            "page_count": page_count,
            "format": "pages",
            "pages": pages,  # [{"page": 1, "text": "..."}, ...]
        }
    elif format == "sentences":
        return {
            "filename": file.filename,
            "sentence_count": sentence_count,
            "format": "sentences",
            "sentences": sentences,  # [{"id": "p1_s1", "page": 1, "text": "..."}, ...]
        }
    else:  # format == "full"
        return {
            "filename": file.filename,
            "page_count": page_count,
            "sentence_count": sentence_count,
            "format": "full",
            "text": text_full,  # 전체 텍스트
            "text_length": len(text_full),
        }

# ============================================================
# ✅ 통합 텍스트 추출 API (PDF + 이미지, OCR 지원)
# ============================================================
@app.post("/extract/text/clova")
async def extract_text_clova(
    file: UploadFile = File(...),
    format: str = Query("full", description="반환 형식: 'full'(전체), 'pages'(페이지별)"),
    min_confidence: float = Query(0.0, description="최소 신뢰도 (0.0~1.0)")
) -> Dict[str, Any]:
    """
    Naver Clova OCR로 텍스트 추출 (최고 정확도 95~99%)
    - 한글 문서 인식에 최적화
    - 월 1,000건 무료
    
    지원 파일: PDF, JPG, PNG, BMP, TIFF
    """
    if not CLOVA_OCR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Naver Clova OCR이 설정되지 않았습니다. .env 파일에 API 키를 추가하세요."
        )
    
    # 파일명 체크
    fname = file.filename.lower() if file.filename else ""
    if not fname.endswith(ALLOWED_SUFFIX):
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일입니다. 허용: {', '.join(ALLOWED_SUFFIX)}"
        )
    
    # 파일 읽기
    content = await file.read()
    
    # 용량 체크
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"파일이 너무 큽니다 (최대 {MAX_FILE_MB}MB)"
        )
    
    # Clova OCR 수행
    try:
        result = extract_text_auto_clova(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Clova OCR 실패: {str(e)}")
    
    # 신뢰도 필터링 (이미지인 경우)
    if result['type'] == 'image' and min_confidence > 0 and 'fields' in result:
        filtered_text = []
        for field in result['fields']:
            if field['confidence'] >= min_confidence:
                filtered_text.append(field['text'])
        result['text'] = '\n'.join(filtered_text)
    
    # 형식에 따라 반환
    if format == "pages" and 'pages' in result:
        return {
            "filename": file.filename,
            "type": result["type"],
            "page_count": result["page_count"],
            "format": "pages",
            "pages": result["pages"],
            "ocr_engine": "naver_clova"
        }
    else:
        return {
            "filename": file.filename,
            "type": result["type"],
            "page_count": result["page_count"],
            "format": "full",
            "text": result["text"],
            "text_length": len(result["text"]),
            "ocr_engine": "naver_clova"
        }


@app.post("/extract/text")
async def extract_text(
    file: UploadFile = File(...),
    use_ocr: bool = Query(False, description="OCR 사용 여부 (이미지는 자동, PDF는 선택)"),
    format: str = Query("full", description="반환 형식: 'full'(전체), 'pages'(페이지별)")
) -> Dict[str, Any]:
    """
    PDF, 이미지 파일에서 텍스트 추출 (OCR 지원)
    
    지원 형식:
    - PDF: .pdf
    - 이미지: .jpg, .jpeg, .png, .bmp, .tiff, .tif
    
    - 이미지 파일: 자동으로 OCR 사용
    - PDF 파일: use_ocr=True면 OCR 사용 (스캔본 처리)
    """
    # 파일명 체크
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in ALLOWED_SUFFIX):
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(ALLOWED_SUFFIX)}"
        )
    
    # 용량 제한
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(status_code=413, detail=f"파일 용량 초과(최대 {MAX_FILE_MB}MB)")
    
    # OCR 사용 가능 여부 확인
    if (is_image_file(file.filename) or use_ocr) and not OCR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="OCR 기능을 사용할 수 없습니다. pytesseract와 Tesseract OCR이 설치되어 있는지 확인하세요."
        )
    
    if is_pdf_file(file.filename) and use_ocr and not PDF2IMAGE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="PDF OCR 기능을 사용할 수 없습니다. pdf2image가 설치되어 있는지 확인하세요."
        )
    
    # 텍스트 추출
    try:
        if is_image_file(file.filename):
            # 이미지 파일은 항상 OCR 사용
            result = extract_text_auto(content, file.filename, use_ocr=True)
        elif is_pdf_file(file.filename):
            if use_ocr:
                # OCR로 추출
                result = extract_text_auto(content, file.filename, use_ocr=True)
            else:
                # 일반 PDF 파서 시도
                try:
                    parsed = parse_pdf(content)
                    result = {
                        "type": "pdf",
                        "pages": parsed["pages"],
                        "text_full": parsed["text_full"],
                        "page_count": parsed["page_count"]
                    }
                except Exception:
                    # 실패 시 OCR로 재시도
                    result = extract_text_auto(content, file.filename, use_ocr=True)
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"텍스트 추출 실패: {str(e)}")
    
    # 형식에 따라 반환
    if format == "pages":
        return {
            "filename": file.filename,
            "type": result["type"],
            "page_count": result["page_count"],
            "format": "pages",
            "pages": result["pages"],
        }
    else:  # format == "full"
        return {
            "filename": file.filename,
            "type": result["type"],
            "page_count": result["page_count"],
            "format": "full",
            "text": result["text_full"],
            "text_length": len(result["text_full"]),
        }


# ============================================================
# ✅ 개인정보 마스킹 API
# ============================================================
@app.post("/mask/pdf")
async def mask_pdf(
    file: UploadFile = File(...),
    mask_resident_numbers: bool = Query(True, description="주민번호 마스킹 여부"),
    mask_addresses: bool = Query(True, description="주소 마스킹 여부"),
    address_keep_chars: int = Query(10, description="주소 앞부분 유지할 문자 수")
) -> StreamingResponse:
    """
    PDF에서 개인정보 마스킹 처리 (검은색 박스로 덮기)
    
    - 주민번호 뒷자리 마스킹
    - 주소 뒷부분 마스킹
    - 마스킹된 PDF 다운로드
    """
    from app.services.parser_pdf.pii_masking import mask_pdf_pii
    
    # 파일명 체크
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="PDF 파일만 지원합니다."
        )
    
    # 파일 읽기
    content = await file.read()
    
    try:
        # 마스킹 처리
        masked_pdf = mask_pdf_pii(
            pdf_bytes=content,
            mask_resident_numbers=mask_resident_numbers,
            mask_addresses=mask_addresses,
            address_keep_chars=address_keep_chars
        )
        
        # 마스킹된 PDF 반환
        return StreamingResponse(
            io.BytesIO(masked_pdf),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="masked_{file.filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"마스킹 처리 실패: {str(e)}")


@app.post("/mask/image")
async def mask_image(
    file: UploadFile = File(...),
    mask_resident_numbers: bool = Query(True, description="주민번호 마스킹 여부"),
    mask_addresses: bool = Query(True, description="주소 마스킹 여부"),
    mask_phone_numbers: bool = Query(True, description="전화번호 마스킹 여부"),
    address_keep_chars: int = Query(10, description="주소 앞부분 유지할 문자 수")
) -> StreamingResponse:
    """
    이미지에서 개인정보 마스킹 처리 (검은색 박스로 덮기)
    
    - 주민번호 뒷자리 마스킹
    - 주소 뒷부분 마스킹
    - 전화번호 중간 부분 마스킹
    - 마스킹된 이미지 반환
    """
    from app.services.parser_pdf.pii_masking import mask_image_pii
    
    # 파일명 체크
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]):
        raise HTTPException(
            status_code=400,
            detail="이미지 파일만 지원합니다. (jpg, jpeg, png, bmp, tiff, tif)"
        )
    
    # 파일 읽기
    content = await file.read()
    
    # OCR 결과 가져오기 (Clova OCR 사용)
    ocr_result = None
    if CLOVA_OCR_AVAILABLE:
        try:
            from app.services.parser_pdf.naver_clova_ocr import extract_text_from_image_clova
            ocr_result = extract_text_from_image_clova(content, format=file.filename.split('.')[-1].lower())
        except Exception as e:
            print(f"[Mask] OCR 실패, 기본 마스킹 사용: {e}")
    
    try:
        # 마스킹 처리
        masked_image = mask_image_pii(
            image_bytes=content,
            ocr_result=ocr_result,
            mask_resident_numbers=mask_resident_numbers,
            mask_addresses=mask_addresses,
            mask_phone_numbers=mask_phone_numbers,
            address_keep_chars=address_keep_chars
        )
        
        # 마스킹된 이미지 반환
        return StreamingResponse(
            io.BytesIO(masked_image),
            media_type="image/png",
            headers={
                "Content-Disposition": f'attachment; filename="masked_{file.filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"마스킹 처리 실패: {str(e)}")


@app.post("/mask/text")
async def mask_text(
    text: str = Query(..., description="마스킹할 텍스트"),
    mask_resident_numbers: bool = Query(True, description="주민번호 마스킹 여부"),
    mask_addresses: bool = Query(True, description="주소 마스킹 여부"),
    mask_phone_numbers: bool = Query(True, description="전화번호 마스킹 여부"),
    address_keep_chars: int = Query(10, description="주소 앞부분 유지할 문자 수")
) -> Dict[str, Any]:
    """
    텍스트에서 개인정보 마스킹 처리
    
    - 주민번호 뒷자리 마스킹
    - 주소 뒷부분 마스킹
    - 전화번호 중간 부분 마스킹
    """
    from app.services.parser_pdf.pii_masking import mask_text_pii
    
    try:
        masked_text = mask_text_pii(
            text=text,
            mask_resident_numbers=mask_resident_numbers,
            mask_addresses=mask_addresses,
            mask_phone_numbers=mask_phone_numbers,
            address_keep_chars=address_keep_chars
        )
        
        return {
            "original": text,
            "masked": masked_text,
            "masked_resident_numbers": mask_resident_numbers,
            "masked_addresses": mask_addresses,
            "masked_phone_numbers": mask_phone_numbers,
        }
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"마스킹 처리 실패: {str(e)}")


# ============================================================
# ✅ 서버 실행
# ============================================================
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🚀 RentAI Parser API 서버 시작")
    print("=" * 60)
    print(f"📡 서버 주소: http://localhost:8000")
    print(f"📚 API 문서: http://localhost:8000/docs")
    print(f"🔧 Clova OCR: {'✅ 사용 가능' if CLOVA_OCR_AVAILABLE else '❌ API 키 필요'}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)