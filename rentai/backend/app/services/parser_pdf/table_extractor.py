import pdfplumber
from typing import List, Dict, Any
from io import BytesIO

def extract_tables(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    tables_out = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            for tbl in page.extract_tables() or []:
                tables_out.append({
                    "page": page_num,
                    "table": tbl
                })
    return tables_out
