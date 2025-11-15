"""
OCR을 사용한 텍스트 추출 모듈
- 이미지 파일 (JPG, PNG) 지원
- 스캔된 PDF 지원
- pytesseract 사용
"""
import os
import io
import logging
import re
import unicodedata
from typing import List, Dict, Optional, Union
from pathlib import Path

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv가 없어도 계속 진행

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logging.warning("pytesseract 또는 Pillow가 설치되지 않았습니다. OCR 기능을 사용할 수 없습니다.")

try:
    from pdf2image import convert_from_path, convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logging.warning("pdf2image가 설치되지 않았습니다. PDF OCR 기능을 사용할 수 없습니다.")

logger = logging.getLogger(__name__)

# 환경 변수 설정
TESSERACT_CMD = os.getenv("TESSERACT_CMD")  # Windows: r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if TESSERACT_CMD and OCR_AVAILABLE:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

POPPLER_PATH = os.getenv("POPPLER_PATH")  # Windows: r"C:\tools\poppler-24.02.0\Library\bin"

# OCR 언어 설정 (한국어 + 영어)
OCR_LANG = os.getenv("OCR_LANG", "kor+eng")

# 텍스트가 거의 없는 경우 OCR 시도 (문자 수 기준)
OCR_TRIGGER_LEN = int(os.getenv("OCR_TRIGGER_LEN", "25"))


def _normalize_text(txt: str) -> str:
    """텍스트 정규화 (한글/기호 정규화 + 공백/줄바꿈 정리)"""
    if not txt:
        return ""
    txt = unicodedata.normalize("NFKC", txt)
    txt = txt.replace("\u00A0", " ")  # non-breaking space
    txt = re.sub(r"[ \t]+", " ", txt)  # 다중 공백 -> 한 칸
    txt = re.sub(r"\n{3,}", "\n\n", txt)  # 3개 이상 연속 개행 -> 2개
    return txt.strip()


def extract_text_from_image(image_bytes: bytes, lang: str = OCR_LANG) -> str:
    """
    이미지 파일에서 텍스트 추출 (OCR)
    
    Args:
        image_bytes: 이미지 파일의 바이트 데이터
        lang: OCR 언어 (기본: "kor+eng")
    
    Returns:
        추출된 텍스트
    """
    if not OCR_AVAILABLE:
        raise ImportError("pytesseract가 설치되지 않았습니다. pip install pytesseract pillow")
    
    try:
        # PIL Image로 변환
        image = Image.open(io.BytesIO(image_bytes))
        
        # OCR 수행
        text = pytesseract.image_to_string(image, lang=lang)
        
        return _normalize_text(text)
    except Exception as e:
        logger.error(f"이미지 OCR 실패: {e}")
        raise


def extract_text_from_image_file(file_path: Union[str, Path], lang: str = OCR_LANG) -> str:
    """
    이미지 파일 경로에서 텍스트 추출
    
    Args:
        file_path: 이미지 파일 경로
        lang: OCR 언어
    
    Returns:
        추출된 텍스트
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    
    image_bytes = path.read_bytes()
    return extract_text_from_image(image_bytes, lang)


def extract_text_from_pdf_with_ocr(
    pdf_bytes: bytes,
    lang: str = OCR_LANG,
    dpi: int = 300,
    first_page: Optional[int] = None,
    last_page: Optional[int] = None
) -> List[Dict[str, any]]:
    """
    스캔된 PDF에서 OCR로 텍스트 추출
    
    Args:
        pdf_bytes: PDF 파일의 바이트 데이터
        lang: OCR 언어
        dpi: 이미지 해상도 (기본: 300)
        first_page: 시작 페이지 (1-based, None이면 처음부터)
        last_page: 끝 페이지 (1-based, None이면 끝까지)
    
    Returns:
        [{"page": 1, "text": "..."}, ...] 형식의 리스트
    """
    if not PDF2IMAGE_AVAILABLE:
        raise ImportError("pdf2image가 설치되지 않았습니다. pip install pdf2image")
    
    if not OCR_AVAILABLE:
        raise ImportError("pytesseract가 설치되지 않았습니다. pip install pytesseract pillow")
    
    try:
        # PDF를 이미지로 변환
        # poppler_path가 None이면 환경 변수에서 자동으로 찾음
        kwargs = {
            "dpi": dpi,
        }
        if first_page:
            kwargs["first_page"] = first_page
        if last_page:
            kwargs["last_page"] = last_page
        if POPPLER_PATH:
            kwargs["poppler_path"] = POPPLER_PATH
        
        images = convert_from_bytes(pdf_bytes, **kwargs)
        
        results = []
        start_page = (first_page or 1)
        
        for idx, image in enumerate(images):
            page_num = start_page + idx
            
            # OCR 수행
            text = pytesseract.image_to_string(image, lang=lang)
            normalized_text = _normalize_text(text)
            
            results.append({
                "page": page_num,
                "text": normalized_text
            })
            
            logger.info(f"페이지 {page_num} OCR 완료 ({len(normalized_text)}자)")
        
        return results
    except Exception as e:
        logger.error(f"PDF OCR 실패: {e}")
        raise


def extract_text_from_pdf_file_with_ocr(
    pdf_path: Union[str, Path],
    lang: str = OCR_LANG,
    dpi: int = 300,
    first_page: Optional[int] = None,
    last_page: Optional[int] = None
) -> List[Dict[str, any]]:
    """
    PDF 파일 경로에서 OCR로 텍스트 추출
    
    Args:
        pdf_path: PDF 파일 경로
        lang: OCR 언어
        dpi: 이미지 해상도
        first_page: 시작 페이지
        last_page: 끝 페이지
    
    Returns:
        [{"page": 1, "text": "..."}, ...] 형식의 리스트
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {pdf_path}")
    
    pdf_bytes = path.read_bytes()
    return extract_text_from_pdf_with_ocr(pdf_bytes, lang, dpi, first_page, last_page)


def is_image_file(filename: str) -> bool:
    """파일명이 이미지 파일인지 확인"""
    ext = Path(filename).suffix.lower()
    return ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']


def is_pdf_file(filename: str) -> bool:
    """파일명이 PDF 파일인지 확인"""
    return Path(filename).suffix.lower() == '.pdf'


def extract_text_auto(
    file_bytes: bytes,
    filename: str,
    use_ocr: bool = True,
    lang: str = OCR_LANG
) -> Dict[str, any]:
    """
    파일 타입을 자동 감지하여 텍스트 추출
    
    Args:
        file_bytes: 파일의 바이트 데이터
        filename: 파일명 (확장자로 타입 판단)
        use_ocr: OCR 사용 여부 (이미지/스캔본인 경우)
        lang: OCR 언어
    
    Returns:
        {
            "type": "image" | "pdf",
            "pages": [{"page": 1, "text": "..."}, ...],
            "text_full": "전체 텍스트",
            "page_count": 1
        }
    """
    if is_image_file(filename):
        if not use_ocr:
            raise ValueError("이미지 파일은 OCR이 필요합니다. use_ocr=True로 설정하세요.")
        
        text = extract_text_from_image(file_bytes, lang)
        return {
            "type": "image",
            "pages": [{"page": 1, "text": text}],
            "text_full": text,
            "page_count": 1
        }
    
    elif is_pdf_file(filename):
        if use_ocr:
            # OCR로 추출
            pages = extract_text_from_pdf_with_ocr(file_bytes, lang)
            full_text = "\n\n".join(p["text"] for p in pages)
            return {
                "type": "pdf_ocr",
                "pages": pages,
                "text_full": full_text,
                "page_count": len(pages)
            }
        else:
            # 일반 PDF 파서 사용 (enhanced_parser)
            from app.services.parser_pdf.enhanced_parser import parse_pdf
            parsed = parse_pdf(file_bytes)
            return {
                "type": "pdf",
                "pages": parsed["pages"],
                "text_full": parsed["text_full"],
                "page_count": parsed["page_count"]
            }
    
    else:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {filename}")

