# backend/app/services/rules/rule_engine.py
import yaml
from typing import Dict, Any, List

SEVERITY_SCORE = {"LOW": 1, "MED": 3, "HIGH": 5}

def _get_field_value(extracted: Dict[str, Any], field_path: str, extras: Dict[str, Any]) -> Any:
    # field_path 예: "maintenance_fee.amount" / "signature_detected"
    if field_path in extras:
        return extras[field_path]
    cur = extracted
    for part in field_path.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is None:
            return None
    # {"value": ...} 형태면 value만 반환
    if isinstance(cur, dict) and "value" in cur:
        return cur["value"]
    return cur

def _has_keywords(text: str, kws: List[str]) -> bool:
    blob = text.lower()
    return any(k.lower() in blob for k in kws)

def evaluate_rules(extracted: Dict[str, Any], text_full: str, extras: Dict[str, Any], rules_yml_path: str) -> Dict[str, Any]:
    with open(rules_yml_path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    results, score = [], 0
    for r in spec.get("rules", []):
        when = r.get("when", {})
        ok = False

        if "field" in when:
            val = _get_field_value(extracted, when["field"], extras)
            op = when.get("op", "none")
            if op == "missing":
                ok = (val is None) or (val == "")
            elif op == "none":
                ok = (val is None)
            elif op == "eq":
                ok = (val == when.get("value"))
            elif op == "contains":
                v = when.get("value", "")
                ok = (isinstance(val, str) and v in val)
            else:
                ok = False

        elif "text_kw" in when:
            kws = when["text_kw"]
            op = when.get("op", "missing_kw")
            if op == "missing_kw":
                ok = (not _has_keywords(text_full, kws))
            elif op == "has_kw":
                ok = _has_keywords(text_full, kws)
            else:
                ok = False

        if ok:
            sev = r["severity"].upper()
            score += SEVERITY_SCORE.get(sev, 0)
            results.append({
                "code": r["code"],
                "severity": sev,
                "message": r["message"],
            })

    return {"total_score": score, "issues": results}
