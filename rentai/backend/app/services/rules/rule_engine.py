# -*- coding: utf-8 -*-
"""
rules_v2.yml 스키마 대응 룰 엔진
- 각 rule: {code, severity(HIGH/MED/LOW), message, when{field|text_kw, op, value}}
- op:
  * missing / none         : 필드가 비어있으면 트리거
  * contains               : 필드 문자열에 value 포함되면 트리거
  * eq                     : 필드 값 == value 이면 트리거
  * missing_kw             : 본문(text_full)에 text_kw 중 하나도 없으면 트리거
- 필드 경로: "a.b.c" -> dict 중첩 조회 지원
- 점수: severity→weight 매핑(HIGH:20/MED:15/LOW:10)
- RAG 근거: 가능 시 첨부(없으면 빈 리스트)
반환 포맷:
{
  "total_score": int,
  "issues": [
     {"id","title","severity","weight","score","reasons":[...],
      "references":[{"text","source","score"}...]}
  ]
}
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import re

from .loader import load_rules

# (선택) RAG 검색 붙이기
try:
    from app.services.rag.retrieval import search as rag_search, RULE_HINTS  # noqa: F401
except Exception:
    rag_search = None
    RULE_HINTS = {}

_SEVERITY_WEIGHT = {"HIGH": 20, "MED": 15, "LOW": 10}
_LEVEL_PRIORITY = {"safe": 0, "warning": 1, "critical": 2}

# 필드 경로를 사용자 친화적인 메시지로 변환
_FIELD_PATH_TO_MESSAGE = {
    "confirmation_date": "확정일자",
    "resident_reported": "전입신고 여부",
    "maintenance_fee.included": "관리비 포함/별도",
    "maintenance_fee.amount": "관리비 금액",
    "maintenance_fee.settlement": "관리비 정산 방식",
    "restoration_clause": "원상복구 조항",
    "termination_penalty": "위약 조항",
    "rent.deposit": "보증금",
    "rent.monthly_rent": "월세",
    "period.start": "계약기간 시작일",
    "period.end": "계약기간 종료일",
    "address": "주소",
    "contract_type": "계약 유형",
    "signature_detected": "서명/날인",
}

def _get_user_friendly_reason(field_path: str, op: str, value: Any = None) -> str:
    """
    필드 경로를 사용자 친화적인 메시지로 변환
    
    Args:
        field_path: 필드 경로 (예: "maintenance_fee.amount")
        op: 연산자 (예: "none", "missing", "contains", "eq")
        value: 값 (선택적)
    
    Returns:
        사용자 친화적인 메시지
    """
    field_name = _FIELD_PATH_TO_MESSAGE.get(field_path, field_path)
    
    if op in ("missing", "none"):
        return f"{field_name} 명시되지 않음"
    elif op == "contains":
        return f"{field_name}에 '{value}' 포함됨"
    elif op == "eq":
        return f"{field_name}이(가) '{value}'와(과) 일치함"
    else:
        return f"{field_name} 확인 필요"

def _severity_to_level(rule: Dict[str, Any]) -> str:
    level = (rule.get("level") or "").strip().lower()
    if level in ("critical", "warning", "safe"):
        return level
    severity = str(rule.get("severity") or "").upper()
    if severity == "HIGH":
        return "critical"
    if severity in ("MED", "LOW"):
        return "warning"
    return "safe"

def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", ("" if s is None else str(s))).strip()

def _norm_lc(s: Any) -> str:
    return _norm(s).lower()

def _get_nested(d: Dict[str, Any], path: str) -> Any:
    """
    중첩된 딕셔너리에서 값 추출
    - "value" 키가 있으면 자동으로 건너뜀
    - 예: rent.deposit → rent["value"]["deposit"] 자동 처리
    """
    cur: Any = d
    for key in path.split("."):
        if not isinstance(cur, dict):
            return None
        
        # 키가 직접 없으면 "value" 키를 통해 접근 시도
        if key not in cur:
            # "value" 키가 있고, 그 안에 원하는 키가 있으면 사용
            if "value" in cur and isinstance(cur["value"], dict):
                cur = cur["value"]
                if key not in cur:
                    return None
            else:
                return None
        
        cur = cur[key]
    
    return cur

def _is_empty(v: Any) -> bool:
    return v in (None, "", [], {}, ())

def _contains(hay: Any, needle: Any) -> bool:
    return _norm_lc(needle) in _norm_lc(hay)

def _attach_refs(rule_code: str, title: str, k: int = 3) -> List[Dict[str, Any]]:
    if rag_search is None:
        return []
    hints = RULE_HINTS.get(rule_code) or RULE_HINTS.get(title) or [title]
    q = " ".join(hints)
    try:
        hits = rag_search(q, k=k)
        out = []
        for h in hits:
            out.append({
                "text": (_norm(h.get("text"))[:500]),
                "source": _norm(h.get("source")),
                "score": h.get("score"),
            })
        return out
    except Exception:
        return []

def _match(rule: Dict[str, Any], extracted: Dict[str, Any], full_text: str, extras: Dict[str, Any]) -> List[str]:
    """매치되면 이유 목록 반환, 아니면 빈 리스트"""
    w: Dict[str, Any] = rule.get("when", {}) or {}
    op = (w.get("op") or "").strip()
    reasons: List[str] = []

    def _resolve_field_value(path: Optional[str]) -> Any:
        if not path:
            return None
        val = _get_nested(extras, path)
        if val is None:
            val = _get_nested(extracted, path)
        return val

    only_field = w.get("only_if_field")
    if only_field:
        only_val = _resolve_field_value(only_field)
        only_target = w.get("only_if_value")
        if only_target is None:
            if _is_empty(only_val):
                return []
        else:
            if _norm_lc(only_val) != _norm_lc(only_target):
                return []

    unless_field = w.get("unless_field")
    if unless_field:
        unless_val = _resolve_field_value(unless_field)
        unless_target = w.get("unless_value")
        if unless_target is None:
            if not _is_empty(unless_val):
                return []
        else:
            if _norm_lc(unless_val) == _norm_lc(unless_target):
                return []

    # 1) field 기반 연산
    field_path = w.get("field")
    if field_path:
        # extracted + extras 둘 다 조회 시도 (extras 먼저 조회)
        val = _get_nested(extras, field_path)
        if val is None:
            val = _get_nested(extracted, field_path)

        if op in ("missing", "none"):
            if _is_empty(val):
                reason_msg = _get_user_friendly_reason(field_path, op)
                reasons.append(reason_msg)
                return reasons

        elif op == "contains":
            if _contains(val, w.get("value")):
                reason_msg = _get_user_friendly_reason(field_path, op, w.get("value"))
                reasons.append(reason_msg)
                return reasons

        elif op == "eq":
            if str(val) == str(w.get("value")):
                reason_msg = _get_user_friendly_reason(field_path, op, w.get("value"))
                reasons.append(reason_msg)
                return reasons

        # field가 있는데도 매치 안 됨 → 빈 리스트 반환
        return []

    # 2) 텍스트 키워드 기반
    text_kw = w.get("text_kw") or []
    if op == "missing_kw":
        # text_kw 중 하나라도 본문에 있으면 '경고 아님' → 매치 실패
        hay = _norm_lc(full_text)
        found = any((_norm_lc(k) in hay) for k in text_kw)
        if not found:
            reasons.append(f"본문에 키워드 미존재: {', '.join(text_kw)}")
            return reasons
        return []

    # 정의되지 않은 op → 매치 실패
    return []

def evaluate_rules(
    extracted: Dict[str, Any],
    full_text: str,
    extras: Optional[Dict[str, Any]] = None,
    rules_path: Optional[str] = None,
) -> Dict[str, Any]:
    extras = extras or {}
    _ver, rules = load_rules(rules_path)

    issues: List[Dict[str, Any]] = []
    total = 0
    overall_level = "safe"

    for r in rules:
        code = str(r.get("code") or "")
        message = r.get("message") or code or "규칙"
        severity = str(r.get("severity") or "MED").upper()
        weight = int(_SEVERITY_WEIGHT.get(severity, 10))
        level = _severity_to_level(r)

        reasons = _match(r, extracted, full_text, extras)
        if not reasons:
            continue

        issue = {
            "id": code,
            "title": message,
            "severity": severity,
            "weight": weight,
            "score": weight,
             "level": level,
            "reasons": reasons,
            "references": _attach_refs(code, message, k=3),
        }
        issues.append(issue)
        total += weight
        if _LEVEL_PRIORITY.get(level, 0) > _LEVEL_PRIORITY.get(overall_level, 0):
            overall_level = level

    return {"total_score": total, "issues": issues, "level": overall_level}
