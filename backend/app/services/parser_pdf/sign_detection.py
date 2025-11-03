from typing import Dict, List

SIGN_KEYWORDS = ["서명", "날인", "sign", "signature", "도장"]

def detect_signature(sentences: List[Dict]) -> bool:
    blob = " ".join(s["text"] for s in sentences)
    blob_lower = blob.lower()
    # 한글/영문 키워드 모두 검사
    return any(k in blob or k in blob_lower for k in SIGN_KEYWORDS)
