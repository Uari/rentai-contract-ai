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

# ============================================================
# ✅ 앱 설정
# ============================================================
MAX_FILE_MB = 20
ALLOWED_SUFFIX = (".pdf",)

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
async def analyze_pdf(file: UploadFile = File(...)) -> Dict[str, Any]:
    # 🔍 파일명 체크
    if not file.filename.lower().endswith(ALLOWED_SUFFIX):
        raise HTTPException(status_code=400, detail="PDF만 업로드 해주세요.")

    # 🔍 용량 제한
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(status_code=413, detail=f"파일 용량 초과(최대 {MAX_FILE_MB}MB)")

    # 🔍 PDF 파싱
    try:
        parsed = parse_pdf(content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"텍스트 파싱 실패: {e}")

    extracted = extract_all(parsed["text_full"], parsed["sentences"])

    # 표 추출
    try:
        tables = extract_tables(content)
    except Exception:
        tables = []

    # 서명 감지
    try:
        signature = detect_signature(parsed["sentences"])
    except Exception:
        signature = False

    # ✅ 룰 평가
    extras = {"signature_detected": signature, "tables_found": len(tables)}
    risk = evaluate_rules(extracted, parsed["text_full"], extras, RULES_PATH)

    # 룰 엔진 결과에 법령 근거 인용 붙이기
    issues = risk.get("issues", [])
    all_rag_refs = []  # 모든 RAG 참조 수집
    for issue in issues:
        # 기본 질의: 룰 메시지 + 맥락 키워드
        base_q = issue.get("message", "") or issue.get("title", "")
        # 필요 시 필드보강 (extracted 필드 일부를 질의에 추가)
        hint = ""
        conf_date_val = extracted.get("confirmation_date", {}).get("value")
        if conf_date_val:
            hint += f" 확정일자:{conf_date_val}"
        rr_val = extracted.get("resident_reported", {}).get("value")
        if rr_val is not None:
            hint += f" 전입신고:{rr_val}"

        query = f"{base_q} {hint} 임대차보호법 근거"
        refs = law_search(query, k=3)  # [{"text","source","score"}…]
        issue["references"] = refs
        all_rag_refs.extend(refs)

    # 프론트엔드 기대 형식으로 변환
    # 1. summary 생성
    summary = {
        "filename": file.filename,
        "pages": parsed["page_count"],
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
    
    for key, label in field_mapping.items():
        node = extracted.get(key, {})
        if isinstance(node, dict):
            value = node.get("value")
            if value is not None:
                # 중첩 구조 처리 (rent, period, maintenance_fee)
                if isinstance(value, dict):
                    if key == "rent":
                        val_str = f"보증금: {value.get('deposit', '')}, 월세: {value.get('monthly_rent', '')}"
                    elif key == "period":
                        val_str = f"{value.get('start', '')} ~ {value.get('end', '')}"
                    elif key == "maintenance_fee":
                        included = value.get("included")
                        amount = value.get("amount")
                        val_str = f"포함: {included}, 금액: {amount}" if amount else f"포함: {included}"
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
        "page_count": parsed["page_count"],
        "sentence_count": parsed["sentence_count"],
        "tables_found": len(tables),
        "signature_detected": signature,
        "preview_sentences": parsed["sentences"][:5],
        "extracted_fields": extracted,
        "risk": risk,
    }

# ============================================================
# ✅ PDF 리포트 생성 + 다운로드
# ============================================================
@app.post("/report/pdf")
async def report_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF만 업로드 해주세요.")
    content = await file.read()

    try:
        parsed = parse_pdf(content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"텍스트 파싱 실패: {e}")

    try:
        tables = extract_tables(content)
    except Exception:
        tables = []
    try:
        signature = detect_signature(parsed["sentences"])
    except Exception:
        signature = False

    extracted = extract_all(parsed["text_full"], parsed["sentences"])

    extras = {"signature_detected": signature, "tables_found": len(tables)}
    risk = evaluate_rules(extracted, parsed["text_full"], extras, RULES_PATH)

    context = {
        "file": file.filename,
        "page_count": parsed["page_count"],
        "sentence_count": parsed["sentence_count"],
        "tables_found": len(tables),
        "signature_detected": signature,
        "extracted_fields": extracted,
        "preview_sentences": parsed["sentences"][:5],
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
