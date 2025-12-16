# -*- coding: utf-8 -*-
"""
PDF를 이미지로 변환하는 유틸리티
"""
from typing import List, Optional
from PIL import Image
import io
import fitz  # PyMuPDF


def pdf_first_page_to_image(pdf_bytes: bytes, dpi: int = 200) -> Optional[bytes]:
    """
    PDF의 첫 페이지를 이미지로 변환
    
    Args:
        pdf_bytes: PDF 바이너리 데이터
        dpi: 이미지 해상도
    
    Returns:
        PNG 이미지 바이너리 데이터 또는 None
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) == 0:
            doc.close()
            return None
        
        # 첫 페이지 가져오기
        page = doc[0]
        
        # 이미지로 변환
        mat = fitz.Matrix(dpi / 72, dpi / 72)  # DPI 변환
        pix = page.get_pixmap(matrix=mat)
        
        # PIL Image로 변환
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # PNG 바이트로 변환
        output = io.BytesIO()
        img.save(output, format='PNG')
        output_bytes = output.getvalue()
        
        doc.close()
        return output_bytes
        
    except Exception as e:
        print(f"[PDF2Image] 변환 실패: {e}")
        return None
