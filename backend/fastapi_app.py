# fastapi_app.py

import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent / "backend"))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
from app.services.parser_pdf.enhanced_parser import parse_pdf
from app.services.parser_pdf.table_extractor import extract_tables
from app.services.parser_pdf.sign_detection import detect_signature
from app.services.extractors.lease_fields import extract_all
from app.services.rules.rule_engine import evaluate_rules

MAX_FILE_MB = 20
ALLOWED_SUFFIX = (".pdf",)

app = FastAPI(title="RentAI Parser API", version="0.1.0")

# CORS: 이후 Streamlit 연동 대비, 전체 허용 (필요 시 도메인 제한)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}

@app.post("/analyze/pdf")
async def analyze_pdf(file: UploadFile = File(...)) -> Dict[str, Any]:
    # 1) 간단한 유효성 체크
    name_lower = file.filename.lower()
    if not name_lower.endswith(ALLOWED_SUFFIX):
        raise HTTPException(status_code=400, detail="PDF만 업로드 해주세요.")

    # 2) 크기 제한 (메모리 사용 보호)
    #    UploadFile은 스트림이지만, 단순화를 위해 max MB 기준으로 제한
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(status_code=413, detail=f"파일 용량 초과(최대 {MAX_FILE_MB}MB)")

    # 3) 파싱
    try:
        parsed = parse_pdf(content)  # {pages, sentences, text_full, page_count, sentence_count}
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"텍스트 파싱 실패: {e}")

    # 필드 추출 ✅
    extracted = extract_all(parsed["text_full"], parsed["sentences"])

    # 4) 표 추출 (스캔 PDF 등에서 실패할 수 있어도 무시하고 진행)
    try:
        tables = extract_tables(content)
    except Exception:
        tables = []

    # 5) 서명/날인 키워드 감지 (간단판)
    try:
        signature = detect_signature(parsed["sentences"])
    except Exception:
        signature = False

    # 3) 룰 평가 (extras로 비구조 필드 전달)
    project_root = pathlib.Path(__file__).resolve().parent
    rules_path = str(project_root.parent / "rules" / "rules_v2.yml")
    extras = {
        "signature_detected": signature,
        "tables_found": len(tables),
    }
    risk = evaluate_rules(extracted, parsed["text_full"], extras, rules_path)

    # 6) 응답 (미리보기 + 개요)
    return {
        "file": file.filename,
        "size_mb": round(size_mb, 2),
        "page_count": parsed["page_count"],
        "sentence_count": parsed["sentence_count"],
        "tables_found": len(tables),
        "signature_detected": signature,
        "preview_sentences": parsed["sentences"][:5],   # 앞부분 5개만
        "extracted_fields": extracted,
        "risk": risk,  # ✅ {total_score, issues[]}
    }