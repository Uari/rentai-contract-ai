import pytesseract
from pdf2image import convert_from_bytes
from typing import List

def ocr_pdf(pdf_bytes: bytes, lang: str = "kor") -> List[str]:
    images = convert_from_bytes(pdf_bytes)
    texts = []
    for img in images:
        txt = pytesseract.image_to_string(img, lang=lang)
        texts.append(txt)
    return texts
