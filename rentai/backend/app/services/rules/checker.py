# ⚠️ 레거시 룰 체커 - analyze_pipeline.py에서만 사용 (현재 미사용)
# 메인 룰 엔진은 rule_engine.py 사용

from typing import List, Dict, Any
from app.models.contract_schema import LeaseDoc

def run_rules(doc: LeaseDoc, rules: dict) -> List[Dict[str, Any]]:
    issues = []
    special = (doc.special_terms or "").lower()
    kw_sets = rules.get("keyword_rules", [])
    for r in kw_sets:
        required_all = [k.lower() for k in r.get("must_include_all", [])]
        if required_all and not all(k in special for k in required_all):
            issues.append({
                "severity": r.get("severity", "MED"),
                "code": r.get("code", "KW-001"),
                "msg": r.get("message", "특약 키워드 누락 가능"),
                "evidence": f"required_all={required_all} not satisfied"
            })
    numeric = rules.get("numeric_rules", [])
    for r in numeric:
        if r.get("code") == "NR-001":
            if doc.period_months < r.get("min_period", 6) and doc.monthly_rent > 0:
                issues.append({
                    "severity": "MED",
                    "code": "NR-001",
                    "msg": "단기 월세 계약 – 중도해지/위약 조항 확인 필요",
                    "evidence": f"기간 {doc.period_months}개월"
                })
    return issues
