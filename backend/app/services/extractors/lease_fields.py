# backend/app/services/extractors/lease_fields.py
import re
from typing import Dict, Any, List, Optional, Tuple

DatePatts = [
    r"\b(20\d{2})[-\.\/](\d{1,2})[-\.\/](\d{1,2})\b",                    # 2025-01-01, 2025.1.1
    r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일",                 # 2025년 1월 1일
]

def _norm_date(y: str, m: str, d: str) -> str:
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

def _pick_evidence(sentences: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
    out = []
    kw_lower = [k.lower() for k in keywords]
    for s in sentences:
        txt = s["text"]
        blob = txt.lower()
        if any(k in blob for k in kw_lower):
            out.append({"id": s["id"], "page": s["page"], "text": txt})
    return out[:3]  # 상위 3개까지만

def extract_confirmation_date(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    for p in DatePatts:
        m = re.search(p, text)
        if m:
            y, mo, d = m.groups()
            return _norm_date(y, mo, d), _pick_evidence(sentences, ["확정일자", "확정 일자", "확정"])
    return None, _pick_evidence(sentences, ["확정일자", "확정 일자", "확정"])

def extract_resident_reported(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Optional[bool], List[Dict[str, Any]]]:
    evid = _pick_evidence(sentences, ["전입신고", "전입 신고"])
    blob = text.lower()
    if "전입신고" in text or "전입 신고" in text:
        if any(x in blob for x in ["미이행", "미실시", "하지 않", "아직 안", "불가"]):
            return False, evid
        if any(x in blob for x in ["완료", "할 예정", "진행", "실시"]):
            return True, evid
        return True, evid
    return None, evid

def extract_maintenance_fee(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    result = {"included": None, "amount": None}
    evid = _pick_evidence(sentences, ["관리비", "공용관리비", "공과금"])
    blob = text.replace(" ", "").lower()
    if "관리비별도" in blob or "관리비미포함" in blob or "별도정산" in blob:
        result["included"] = False
    elif ("관리비" in blob) and ("포함" in blob):
        result["included"] = True
    m = re.search(r"(관리비|공용관리비|관리비금액)[:：]?\s*([\d,]+)\s*원", text)
    if m:
        result["amount"] = int(m.group(2).replace(",", ""))
    return result, evid

def extract_restoration_clause(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    evid = _pick_evidence(sentences, ["원상복구", "복구", "훼손", "수선"])
    if any(k in text for k in ["모든 훼손은 임차인 부담", "전액 임차인", "일체 임차인 부담"]):
        return "과도한 부담 가능성(임차인 전액 부담 문구)", evid
    if "원상복구" in text:
        return "원상복구 조항 존재", evid
    return None, evid

def extract_termination_penalty(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    evid = _pick_evidence(sentences, ["중도해지", "위약", "위약금"])
    if any(k in text for k in ["잔여월세 전액", "남은 월세 전액", "잔금 전액"]):
        return "과도한 위약 가능성(잔여월세 전액)", evid
    if ("위약" in text) or ("중도해지" in text):
        m = re.search(r"(위약금)\s*[:：]?\s*([\d,]+)\s*원", text)
        if m:
            return f"{m.group(1)} {m.group(2)}원", evid
        m2 = re.search(r"(위약금|해지수수료)\s*[:：]?\s*(\d{1,2})\s*%", text)
        if m2:
            return f"{m2.group(1)} {m2.group(2)}%", evid
        return "위약 관련 조항 존재", evid
    return None, evid

def extract_all(text_full: str, sentences: List[Dict[str, Any]]) -> Dict[str, Any]:
    conf_date, conf_e = extract_confirmation_date(text_full, sentences)
    rr, rr_e = extract_resident_reported(text_full, sentences)
    mfee, mf_e = extract_maintenance_fee(text_full, sentences)
    resto, re_e = extract_restoration_clause(text_full, sentences)
    term, te_e = extract_termination_penalty(text_full, sentences)
    return {
        "confirmation_date": {"value": conf_date, "evidence": conf_e},
        "resident_reported": {"value": rr, "evidence": rr_e},
        "maintenance_fee": {"value": mfee, "evidence": mf_e},
        "restoration_clause": {"value": resto, "evidence": re_e},
        "termination_penalty": {"value": term, "evidence": te_e},
    }
