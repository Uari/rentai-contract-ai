# backend/app/services/extractors/lease_fields.py
import re
from typing import Dict, Any, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────
# 공통 유틸
# ─────────────────────────────────────────────────────────────────
DatePatts = [
    r"\b(20\d{2})[-\.\/](\d{1,2})[-\.\/](\d{1,2})\b",                        # 2025-01-01 / 2025.1.1
    r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일"                       # 2025년 1월 1일
]

def _norm_date(y: str, m: str, d: str) -> str:
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

def _to_int(s: str) -> Optional[int]:
    try:
        return int(re.sub(r"[^\d]", "", s))
    except Exception:
        return None

def _pick_evidence(sentences: List[Dict[str, Any]], keywords: List[str], limit: int = 3) -> List[Dict[str, Any]]:
    out = []
    kw_lower = [k.lower() for k in keywords]
    for s in sentences:
        txt = s["text"]
        blob = txt.lower().replace(" ", "")
        if any(k.replace(" ", "").lower() in blob for k in kw_lower):
            out.append({"id": s["id"], "page": s["page"], "text": txt})
            if len(out) >= limit:
                break
    return out

# ─────────────────────────────────────────────────────────────────
# 개별 필드 추출기 (확장)
# ─────────────────────────────────────────────────────────────────
def extract_confirmation_date(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    evid = _pick_evidence(sentences, ["확정일자", "확정 일자", "확정"])
    for p in DatePatts:
        m = re.search(p, text)
        if m:
            y, mo, d = m.groups()
            return _norm_date(y, mo, d), evid
    return None, evid

def extract_resident_reported(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Optional[bool], List[Dict[str, Any]]]:
    evid = _pick_evidence(sentences, ["전입신고", "전입 신고"])
    blob = text.replace(" ", "").lower()
    if "전입신고" in text or "전입 신고" in text:
        negative = any(x in blob for x in ["미이행", "미실시", "하지않", "아직안", "불가"])
        positive = any(x in blob for x in ["완료", "예정", "진행", "실시", "신고함"])
        if negative and not positive:
            return False, evid
        if positive and not negative:
            return True, evid
        return True, evid  # 언급되면 기본 긍정으로 추정
    return None, evid

def extract_maintenance_fee(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """관리비 포함/별도 및 금액"""
    result = {"included": None, "amount": None, "settlement": None}
    evid = _pick_evidence(sentences, ["관리비", "공용관리비", "공과금", "정산"])
    blob = text.replace(" ", "").lower()
    if "관리비별도" in blob or "관리비미포함" in blob or "별도정산" in blob:
        result["included"] = False
    elif "관리비" in blob and "포함" in blob:
        result["included"] = True
    # 금액
    m = re.search(r"(관리비|공용관리비|관리비금액|관리비는)\s*[:：]?\s*([\d,]+)\s*원", text)
    if m:
        result["amount"] = _to_int(m.group(2))
    # 정산 방식
    if "정산" in text:
        if "월별" in text or "매월" in text:
            result["settlement"] = "월별"
        elif "분기" in text:
            result["settlement"] = "분기별"
        elif "연" in text:
            result["settlement"] = "연간"
        else:
            result["settlement"] = "기재"
    return result, evid

def extract_restoration_clause(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    evid = _pick_evidence(sentences, ["원상복구", "복구", "훼손", "수선"])
    harsh = ["모든훼손은임차인부담", "전액임차인", "일체임차인부담"]
    blob = text.replace(" ", "")
    if any(k in blob for k in harsh):
        return "과도한 부담 가능성(임차인 전액/일체 부담 문구)", evid
    if "원상복구" in text or "원상 회복" in text:
        return "원상복구 조항 존재", evid
    return None, evid

def extract_termination_penalty(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    evid = _pick_evidence(sentences, ["중도해지", "위약", "위약금", "해지수수료"])
    blob = text.replace(" ", "")
    if any(k in blob for k in ["잔여월세전액", "남은월세전액", "잔금전액"]):
        return "과도한 위약 가능성(잔여월세 전액)", evid
    if any(k in text for k in ["위약", "중도해지", "해지수수료", "違約"]):
        m = re.search(r"(위약금|해지수수료)\s*[:：]?\s*([\d,]+)\s*원", text)
        if m:
            return f"{m.group(1)} {m.group(2)}원", evid
        m2 = re.search(r"(위약금|해지수수료)\s*[:：]?\s*(\d{1,2})\s*%", text)
        if m2:
            return f"{m2.group(1)} {m2.group(2)}%", evid
        return "위약 관련 조항 존재", evid
    return None, evid

def extract_deposit_and_rent(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """보증금/월세/관리비 구분 금액 추출"""
    evid = _pick_evidence(sentences, ["보증금", "월세", "차임", "임대료"])
    out = {"deposit": None, "monthly_rent": None}
    m1 = re.search(r"(보증금)\s*[:：]?\s*([\d,]+)\s*원", text)
    if m1:
        out["deposit"] = _to_int(m1.group(2))
    m2 = re.search(r"(월세|차임|임대료)\s*[:：]?\s*([\d,]+)\s*원", text)
    if m2:
        out["monthly_rent"] = _to_int(m2.group(2))
    return out, evid

def extract_term_period(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """계약기간 (시작~종료) / 총 개월수 추정"""
    evid = _pick_evidence(sentences, ["계약기간", "기간", "임대기간"])
    out = {"start": None, "end": None}
    # 2025-01-01 ~ 2026-01-01
    p = re.search(r"(20\d{2}[-\.\/]\d{1,2}[-\.\/]\d{1,2})\s*[~\-–]\s*(20\d{2}[-\.\/]\d{1,2}[-\.\/]\d{1,2})", text)
    if p:
        s, e = p.groups()
        def norm(d: str) -> str:
            d = d.replace(".", "-").replace("/", "-")
            y, m, d2 = d.split("-")
            return _norm_date(y, m, d2)
        out["start"] = norm(s)
        out["end"] = norm(e)
    return out, evid

def extract_address(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """주소(지번/도로명) 키워드 근처 라인 요약"""
    evid = _pick_evidence(sentences, ["소재지", "주소", "지번", "도로명"])
    # 간단 추론: '소재지:' 또는 '주소:' 라인
    m = re.search(r"(소재지|주소)\s*[:：]\s*([^\n\r]+)", text)
    if m:
        return m.group(2).strip(), evid
    return None, evid

# ─────────────────────────────────────────────────────────────────
# 종합 추출
# ─────────────────────────────────────────────────────────────────
def extract_all(text_full: str, sentences: List[Dict[str, Any]]) -> Dict[str, Any]:
    conf_date, conf_e = extract_confirmation_date(text_full, sentences)
    rr, rr_e = extract_resident_reported(text_full, sentences)
    mfee, mf_e = extract_maintenance_fee(text_full, sentences)
    resto, re_e = extract_restoration_clause(text_full, sentences)
    term, te_e = extract_termination_penalty(text_full, sentences)
    rent, rent_e = extract_deposit_and_rent(text_full, sentences)
    period, period_e = extract_term_period(text_full, sentences)
    addr, addr_e = extract_address(text_full, sentences)

    return {
        "confirmation_date": {"value": conf_date, "evidence": conf_e},
        "resident_reported": {"value": rr, "evidence": rr_e},
        "maintenance_fee": {"value": mfee, "evidence": mf_e},
        "restoration_clause": {"value": resto, "evidence": re_e},
        "termination_penalty": {"value": term, "evidence": te_e},
        "rent": {"value": rent, "evidence": rent_e},            # deposit / monthly_rent
        "period": {"value": period, "evidence": period_e},      # start / end
        "address": {"value": addr, "evidence": addr_e},
    }
