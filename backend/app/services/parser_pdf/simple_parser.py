# ⚠️ 레거시 파서 - analyze_pipeline.py에서만 사용 (현재 미사용)
# 메인 파서는 enhanced_parser.py 사용

import fitz  # PyMuPDF
from typing import Dict, List

def pdf_bytes_to_pages_text(pdf_bytes: bytes) -> List[str]:
    pages = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            pages.append(page.get_text("text"))
    return pages

def naive_extract_fields(pages: List[str]) -> Dict:
    full = "\n".join(pages)
    def find(keyword, default=""):
        import re
        m = re.search(rf"{keyword}\s*[:：]\s*(.+)", full)
        return m.group(1).strip() if m else default

    return {
        "lessor": find("임대인", ""),
        "lessee": find("임차인", ""),
        "address": find("주소", ""),
        "deposit": 0,
        "monthly_rent": 0,
        "period_months": 12,
        "special_terms": find("특약", ""),
        "pages": pages
    }
