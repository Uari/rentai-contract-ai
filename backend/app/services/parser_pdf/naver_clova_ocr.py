"""
Naver Clova OCR API를 사용한 텍스트 추출
- 한글 인식 정확도 95~99%
- Tesseract/EasyOCR보다 훨씬 정확
"""
import os
import json
import uuid
import time
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 환경 변수에서 API 키 가져오기
NAVER_CLOVA_API_URL = os.getenv("NAVER_CLOVA_API_URL")
NAVER_CLOVA_SECRET_KEY = os.getenv("NAVER_CLOVA_SECRET_KEY")


def check_api_credentials():
    """API 인증 정보 확인"""
    if not NAVER_CLOVA_API_URL:
        raise ValueError(
            "NAVER_CLOVA_API_URL이 설정되지 않았습니다.\n"
            ".env 파일에 다음을 추가하세요:\n"
            "NAVER_CLOVA_API_URL=https://...\n"
            "NAVER_CLOVA_SECRET_KEY=your_secret_key"
        )
    if not NAVER_CLOVA_SECRET_KEY:
        raise ValueError(
            "NAVER_CLOVA_SECRET_KEY가 설정되지 않았습니다.\n"
            ".env 파일에 Secret Key를 추가하세요."
        )


def extract_text_from_image_clova(image_bytes: bytes, format: str = "jpg") -> Dict[str, Any]:
    """
    Naver Clova OCR로 이미지에서 텍스트 추출
    
    Args:
        image_bytes: 이미지 파일의 바이트 데이터
        format: 이미지 형식 (jpg, png 등)
    
    Returns:
        {
            "text": "추출된 전체 텍스트",
            "fields": [{"text": "...", "confidence": 0.98, ...}, ...],
            "raw": {...}  # 원본 API 응답
        }
    """
    check_api_credentials()
    
    # API 요청 데이터
    request_json = {
        'images': [
            {
                'format': format,
                'name': 'demo'
            }
        ],
        'requestId': str(uuid.uuid4()),
        'version': 'V2',
        'timestamp': int(round(time.time() * 1000))
    }
    
    payload = {'message': json.dumps(request_json).encode('UTF-8')}
    files = [
        ('file', image_bytes)
    ]
    headers = {
        'X-OCR-SECRET': NAVER_CLOVA_SECRET_KEY,
    }
    
    try:
        logger.info(f"[Naver Clova OCR] API 호출 중...")
        response = requests.post(
            NAVER_CLOVA_API_URL,
            headers=headers,
            data=payload,
            files=files,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"[Naver Clova OCR] 응답 수신: {response.status_code}")
        
        # 텍스트 추출
        text_lines = []
        fields = []
        
        if 'images' in result and len(result['images']) > 0:
            image_result = result['images'][0]
            if 'fields' in image_result:
                for field in image_result['fields']:
                    text = field.get('inferText', '')
                    confidence = field.get('inferConfidence', 0)
                    
                    text_lines.append(text)
                    fields.append({
                        'text': text,
                        'confidence': confidence,
                        'bounding_box': field.get('boundingPoly', {})
                    })
        
        full_text = '\n'.join(text_lines)
        
        return {
            'text': full_text,
            'fields': fields,
            'raw': result
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"[Naver Clova OCR] API 호출 실패: {e}")
        raise Exception(f"Naver Clova OCR API 호출 실패: {e}")


def extract_text_from_pdf_clova(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    PDF를 이미지로 변환 후 Naver Clova OCR로 텍스트 추출
    
    Args:
        pdf_bytes: PDF 파일의 바이트 데이터
    
    Returns:
        {
            "text": "전체 텍스트",
            "pages": [{"page": 1, "text": "...", "fields": [...]}, ...],
            "page_count": 5
        }
    """
    try:
        from pdf2image import convert_from_bytes
        from PIL import Image
        import io
    except ImportError:
        raise ImportError("pdf2image와 Pillow가 필요합니다: pip install pdf2image Pillow")
    
    # Poppler 경로
    poppler_path = os.getenv('POPPLER_PATH')
    
    # PDF를 이미지로 변환
    logger.info("[Naver Clova OCR] PDF를 이미지로 변환 중...")
    kwargs = {'dpi': 300}
    if poppler_path:
        kwargs['poppler_path'] = poppler_path
    
    images = convert_from_bytes(pdf_bytes, **kwargs)
    logger.info(f"[Naver Clova OCR] {len(images)}개 페이지 변환 완료")
    
    # 각 페이지 OCR
    pages_result = []
    all_text = []
    
    for i, image in enumerate(images, 1):
        logger.info(f"[Naver Clova OCR] 페이지 {i}/{len(images)} 처리 중...")
        
        # PIL Image를 JPEG bytes로 변환
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=95)
        image_bytes = buffer.getvalue()
        
        # OCR 수행
        result = extract_text_from_image_clova(image_bytes, format='jpg')
        
        pages_result.append({
            'page': i,
            'text': result['text'],
            'fields': result['fields']
        })
        all_text.append(result['text'])
        
        logger.info(f"[Naver Clova OCR] 페이지 {i} 완료 ({len(result['text'])}자)")
    
    return {
        'text': '\n\n'.join(all_text),
        'pages': pages_result,
        'page_count': len(images)
    }


def extract_text_auto_clova(
    file_bytes: bytes,
    filename: str
) -> Dict[str, Any]:
    """
    파일 타입 자동 감지하여 Naver Clova OCR로 텍스트 추출
    
    Args:
        file_bytes: 파일의 바이트 데이터
        filename: 파일명 (확장자로 타입 판단)
    
    Returns:
        {
            "type": "image" | "pdf",
            "text": "전체 텍스트",
            "pages": [...],  # PDF인 경우
            "fields": [...],  # 이미지인 경우
            "page_count": 1
        }
    """
    ext = Path(filename).suffix.lower()
    
    if ext == '.pdf':
        logger.info(f"[Naver Clova OCR] PDF 파일 감지: {filename}")
        result = extract_text_from_pdf_clova(file_bytes)
        return {
            'type': 'pdf',
            'text': result['text'],
            'pages': result['pages'],
            'page_count': result['page_count']
        }
    
    elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
        logger.info(f"[Naver Clova OCR] 이미지 파일 감지: {filename}")
        
        # 이미지 형식 변환
        format_map = {
            '.jpg': 'jpg',
            '.jpeg': 'jpg',
            '.png': 'png',
            '.bmp': 'bmp',
            '.tiff': 'tiff',
            '.tif': 'tiff'
        }
        format = format_map.get(ext, 'jpg')
        
        result = extract_text_from_image_clova(file_bytes, format=format)
        return {
            'type': 'image',
            'text': result['text'],
            'fields': result['fields'],
            'page_count': 1
        }
    
    else:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")

