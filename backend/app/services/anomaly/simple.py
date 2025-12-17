# ⚠️ 레거시 이상 탐지 - analyze_pipeline.py에서만 사용 (현재 미사용)

from app.models.contract_schema import LeaseDoc

def anomaly_score(doc: LeaseDoc) -> float:
    if doc.deposit <= 0:
        return 0.2
    ratio = doc.monthly_rent / max(1, doc.deposit/100)
    return min(1.0, ratio / 5.0)
