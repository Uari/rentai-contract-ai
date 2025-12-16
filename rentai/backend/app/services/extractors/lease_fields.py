# backend/app/services/extractors/lease_fields.py
import re
import calendar
from datetime import date
from typing import Dict, Any, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────
# 공통 유틸
# ─────────────────────────────────────────────────────────────────
DatePatts = [
    r"\b(20\d{2})[-\.\/](\d{1,2})[-\.\/](\d{1,2})\b",                        # 2025-01-01 / 2025.1.1
    r"(20\d{2})[\s\n]*년[\s\n]*(\d{1,2})[\s\n]*월[\s\n]*(\d{1,2})[\s\n]*일"   # 2025년 1월 1일 (줄바꿈 포함)
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
    if "원상복구" in text or "원상 회복" in text or "원상회복" in text:
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
    
    # 보증금 추출 (다양한 형식 지원)
    # 형식 1: 보증금: 175,000,000원 (줄바꿈 포함)
    m1 = re.search(r"(보증금)[\s\n]*[:：]?[\s\n]*([\d,]+)[\s\n]*원", text)
    if m1:
        out["deposit"] = _to_int(m1.group(2))
    # 형식 2: (₩175,000,000) - OCR 결과에서 흔한 형식 (줄바꿈 포함)
    if not out["deposit"]:
        m1_alt = re.search(r"보증금[^\d₩\n]*[\(（]?[\s\n]*[₩＄$]?[\s\n]*([\d,]+)[\s\n]*[\)）]?", text)
        if m1_alt:
            out["deposit"] = _to_int(m1_alt.group(1))
    
    # 월세 추출 (다양한 형식 지원, 줄바꿈 포함)
    m2 = re.search(r"(월세|차임|임대료)[\s\n]*[:：]?[\s\n]*([\d,]+)[\s\n]*원", text)
    if m2:
        out["monthly_rent"] = _to_int(m2.group(2))
    # 형식 2: (₩금액)
    if not out["monthly_rent"]:
        m2_alt = re.search(r"(월세|차임|임대료)[^\d₩\n]*[\(（]?[\s\n]*[₩＄$]?[\s\n]*([\d,]+)[\s\n]*[\)）]?", text)
        if m2_alt:
            out["monthly_rent"] = _to_int(m2_alt.group(2))
    
    return out, evid


def detect_contract_type(
    text: str,
    sentences: List[Dict[str, Any]],
    rent_value: Dict[str, Any]
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """전세/월세 유형 추정"""
    keywords = ["전세", "전세계약", "전세금", "월세", "차임", "보증부월세", "반전세"]
    evid = _pick_evidence(sentences, keywords, limit=3)
    blob = text.replace(" ", "")
    monthly = None
    if isinstance(rent_value, dict):
        monthly = rent_value.get("monthly_rent")
    jeonse_kw = ["전세", "전세계약", "전세금"]
    wolse_kw = ["월세", "차임", "보증부월세", "반전세"]
    has_jeonse = any(k in blob for k in jeonse_kw)
    has_wolse = any(k in blob for k in wolse_kw)
    if monthly and monthly > 0:
        return "wolse", evid
    if has_wolse and not has_jeonse:
        return "wolse", evid
    if has_jeonse and not has_wolse and not monthly:
        return "jeonse", evid
    return None, evid

def extract_term_period(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """계약기간 (시작~종료) / 총 개월수 추정"""
    evid = _pick_evidence(sentences, ["계약기간", "기간", "임대기간", "인도일", "개월", "까지"])
    out = {"start": None, "end": None}

    date_entries: List[Tuple[int, Tuple[int, int, int]]] = []

    dot_pattern = re.compile(r"(20\d{2})[-\.\/](\d{1,2})[-\.\/](\d{1,2})")
    kr_pattern = re.compile(r"(20\d{2})[\s\n]*년[\s\n]*(\d{1,2})[\s\n]*월[\s\S]{0,80}?(\d{1,2})[\s\n]*일")

    for pattern in (dot_pattern, kr_pattern):
        for m in pattern.finditer(text):
            try:
                tup = tuple(map(int, m.groups()))
                date_entries.append((m.start(), tup))
            except ValueError:
                continue

    date_entries.sort(key=lambda x: x[0])

    start_keywords = ["인도", "부터", "사용", "개시", "입주", "전입"]
    end_keywords = ["까지", "만료", "종료", "만기", "수익"]
    skip_keywords = ["계약서", "계약체결", "계약서작성"]

    def pick_by_keywords(entries, keywords, reverse=False, skip=None):
        iterable = reversed(entries) if reverse else entries
        for pos, tup in iterable:
            ctx = text[max(0, pos - 80): pos + 120]
            if skip and any(sk in ctx for sk in skip):
                continue
            if any(kw in ctx for kw in keywords):
                return tup
        return None

    start_tuple = pick_by_keywords(date_entries, start_keywords, skip=skip_keywords)
    end_tuple = pick_by_keywords(date_entries, end_keywords, reverse=True)

    if end_tuple is None and date_entries:
        end_tuple = max(date_entries, key=lambda x: x[1])[1]
    if start_tuple is None and date_entries:
        start_tuple = min(date_entries, key=lambda x: x[1])[1]

    dur_match = re.search(r"(\d{1,2})\s*개월", text)
    duration_months = int(dur_match.group(1)) if dur_match else None

    def _subtract_months(tup: Tuple[int, int, int], months: int) -> Tuple[int, int, int]:
        y, m, d = tup
        total_months = y * 12 + (m - 1) - months
        if total_months < 0:
            total_months = 0
        new_y = total_months // 12
        new_m = total_months % 12 + 1
        last_day = calendar.monthrange(new_y, new_m)[1]
        new_d = min(d, last_day)
        return new_y, new_m, new_d

    def _add_months(tup: Tuple[int, int, int], months: int) -> Tuple[int, int, int]:
        y, m, d = tup
        total_months = y * 12 + (m - 1) + months
        new_y = total_months // 12
        new_m = total_months % 12 + 1
        last_day = calendar.monthrange(new_y, new_m)[1]
        new_d = min(d, last_day)
        return new_y, new_m, new_d

    if end_tuple and duration_months and (start_tuple is None or start_tuple == end_tuple):
        start_tuple = _subtract_months(end_tuple, duration_months)

    if start_tuple and duration_months:
        expected_end = _add_months(start_tuple, duration_months)
        adjust = False
        if end_tuple is None:
            adjust = True
        else:
            try:
                diff_days = abs((date(*end_tuple) - date(*start_tuple)).days)
            except ValueError:
                diff_days = 0
            if diff_days < duration_months * 20:
                adjust = True
        if adjust:
            end_tuple = expected_end

    if start_tuple:
        out["start"] = _norm_date(str(start_tuple[0]), str(start_tuple[1]), str(start_tuple[2]))
    if end_tuple:
        out["end"] = _norm_date(str(end_tuple[0]), str(end_tuple[1]), str(end_tuple[2]))

    pattern_ctx = re.compile(r"(20\d{2})[\s\n]*년[\s\n]*(\d{1,2})[\s\n]*월[\s\S]{0,120}?(\d{1,2})[\s\n]*일")
    ctx_matches = list(pattern_ctx.finditer(text))
    if ctx_matches:
        for m in ctx_matches:
            tup = tuple(map(int, m.groups()))
            ctx = text[max(0, m.start() - 80): m.start() + 120]
            if (out["end"] is None) and any(kw in ctx for kw in end_keywords):
                out["end"] = _norm_date(*map(str, tup))
            if (out["start"] is None) and any(kw in ctx for kw in start_keywords):
                out["start"] = _norm_date(*map(str, tup))

    if (out["start"] is None or out["end"] is None) and ctx_matches:
        parsed = []
        for m in ctx_matches:
            try:
                tup = tuple(map(int, m.groups()))
                parsed.append((m.start(), tup))
            except ValueError:
                continue
        if len(parsed) >= 2:
            parsed.sort(key=lambda item: item[0])
            first = parsed[0][1]
            last = parsed[-1][1]
            try:
                gap = (date(*last) - date(*first)).days
            except ValueError:
                gap = 0
            if gap >= 200:
                if out["start"] is None:
                    out["start"] = _norm_date(*map(str, first))
                if out["end"] is None:
                    out["end"] = _norm_date(*map(str, last))

    return out, evid

def extract_address(text: str, sentences: List[Dict[str, Any]]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """주소(지번/도로명) 키워드 근처 라인 요약"""
    evid = _pick_evidence(sentences, ["소재지", "주소", "지번", "도로명", "동", "호"])
    
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if "소재지" in line or "주소" in line:
            chunk = " ".join(lines[idx:idx + 6])
            chunk = re.sub(r"(소재지|주소)\s*[:：]?", "", chunk)
            chunk = re.sub(r"\s+", " ", chunk).strip()
            if chunk:
                return chunk, evid
    
    addr_pattern = re.compile(
        r"(서울|부산|대구|인천|광주|대전|울산|세종|경기도|강원도|충청북도|충청남도|전라북도|전라남도|경상북도|경상남도|제주)"
        r"[\s\S]{0,20}?(시|군|구)"
        r"[\s\S]{0,25}?(동|읍|면|리)"
        r"[\s\S]{0,40}?(\d+[-\d]*번지|\d+동\s*\d+호|\d+동|\d+호)"
    )
    match = addr_pattern.search(text)
    if match:
        addr_text = match.group(0)
        addr_text = re.sub(r"\s+", " ", addr_text).strip()
        return addr_text, evid
    
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
    if rent.get("deposit") is None:
        m_dep = re.search(r"보증금[\s\S]{0,120}?([\d,]{3,})", text_full)
        if m_dep:
            rent["deposit"] = _to_int(m_dep.group(1))
        else:
            m_dep2 = re.search(r"\([\s\n]*[₩＄$]?[\s\n]*([\d,]{3,})[\s\n]*\)", text_full)
            if m_dep2:
                val = _to_int(m_dep2.group(1))
                if val and val >= 100000:
                    rent["deposit"] = val
    if rent.get("monthly_rent") is None:
        m_rent = re.search(r"(월세|차임|임대료)[\s\S]{0,80}?([\d,]{3,})", text_full)
        if m_rent:
            rent["monthly_rent"] = _to_int(m_rent.group(2))
    rent_value = rent.get("value") or {}
    contract_type, ct_e = detect_contract_type(text_full, sentences, rent_value)
    period, period_e = extract_term_period(text_full, sentences)
    addr, addr_e = extract_address(text_full, sentences)
    
    # 주소 기본 보정 (동기 버전 - 정규식 기반)
    if addr:
        from app.services.llm.address_corrector import correct_address_sync
        addr = correct_address_sync(addr, context_text=text_full)

    return {
        "confirmation_date": {"value": conf_date, "evidence": conf_e},
        "resident_reported": {"value": rr, "evidence": rr_e},
        "maintenance_fee": {"value": mfee, "evidence": mf_e},
        "restoration_clause": {"value": resto, "evidence": re_e},
        "termination_penalty": {"value": term, "evidence": te_e},
        "rent": {"value": rent, "evidence": rent_e},            # deposit / monthly_rent
        "period": {"value": period, "evidence": period_e},      # start / end
        "address": {"value": addr, "evidence": addr_e},
        "contract_type": {"value": contract_type, "evidence": ct_e},
    }
