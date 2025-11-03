import fitz
import re
from typing import List, Dict

def extract_pages(pdf_bytes: bytes) -> List[Dict]:
    pages = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for idx, page in enumerate(doc, start=1):
            text = page.get_text("text")
            pages.append({"page": idx, "text": text})
    return pages

def split_sentences(pages: List[Dict]) -> List[Dict]:
    results = []
    splitter = re.compile(r'(?<=[.!?。\n])\s+')
    for p in pages:
        raw = splitter.split(p["text"])
        for i, sent in enumerate(raw):
            s = sent.strip()
            if not s:
                continue
            results.append({
                "id": f"p{p['page']}_s{i+1}",
                "page": p["page"],
                "text": s
            })
    return results

def parse_pdf(pdf_bytes: bytes) -> Dict:
    pages = extract_pages(pdf_bytes)
    sentences = split_sentences(pages)
    full_text = "\n".join(s["text"] for s in sentences)
    return {
        "pages": pages,
        "sentences": sentences,
        "text_full": full_text,
        "page_count": len(pages),
        "sentence_count": len(sentences)
    }
