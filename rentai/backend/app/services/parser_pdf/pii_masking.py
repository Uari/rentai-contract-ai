# -*- coding: utf-8 -*-
"""
개인정보 마스킹 처리 모듈

주민번호 뒷자리, 주소 뒷부분 등을 검은색 박스로 마스킹 처리
"""
import re
from typing import List, Tuple, Optional, Dict, Any
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import io


def detect_resident_number(text: str) -> List[Tuple[str, int, int]]:
    """
    주민번호 패턴 감지
    
    Returns:
        List[Tuple[pattern, start_pos, end_pos]]: 감지된 주민번호 패턴과 위치
    """
    patterns = [
        r'\d{6}[-]\d{7}',  # 123456-1234567
        r'\d{6}[-]\d{1}\*{6}',  # 이미 일부 마스킹된 경우
        r'\d{6}[-]\d{1}\*{5}\d{1}',  # 부분 마스킹
    ]
    
    results = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            results.append((match.group(), match.start(), match.end()))
    
    return results


def detect_phone_number(text: str) -> List[Tuple[str, int, int]]:
    """
    전화번호 패턴 감지
    
    Returns:
        List[Tuple[pattern, start_pos, end_pos]]: 감지된 전화번호 패턴과 위치
    """
    patterns = [
        r'\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{4}',  # 010-1234-5678, 02-123-4567
        r'\(\d{2,3}\)\s?\d{3,4}[-.\s]?\d{4}',  # (02) 123-4567
        r'\d{10,11}',  # 01012345678
    ]
    
    results = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            results.append((match.group(), match.start(), match.end()))
    
    return results


def detect_address(text: str) -> List[Tuple[str, int, int]]:
    """
    주소 패턴 감지 (뒷부분 마스킹 대상)
    
    주소는 다양한 형식이 있으므로, 일반적인 패턴을 감지
    예: "서울특별시 강남구 테헤란로 123", "경기도 성남시 분당구 정자동 123-45"
    
    Returns:
        List[Tuple[address, start_pos, end_pos]]: 감지된 주소와 위치
    """
    # 주소 패턴 (시/도, 시/군/구, 동/읍/면, 상세주소)
    address_patterns = [
        r'(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)[\s\S]{0,100}?(?:동|읍|면|리|번지|로|길)[\s\S]{0,50}',
        r'[가-힣]{2,}(?:시|도)[\s\S]{0,100}?(?:동|읍|면|리|번지|로|길)[\s\S]{0,50}',
    ]
    
    results = []
    for pattern in address_patterns:
        for match in re.finditer(pattern, text):
            addr = match.group().strip()
            # 최소 길이 체크 (너무 짧으면 제외)
            if len(addr) > 10:
                results.append((addr, match.start(), match.end()))
    
    return results


def mask_resident_number(text: str, mask_last_digits: int = 7) -> str:
    """
    주민번호 뒷자리 마스킹 (텍스트)
    
    Args:
        text: 원본 텍스트
        mask_last_digits: 마스킹할 뒷자리 개수 (기본 7자리)
    
    Returns:
        마스킹된 텍스트
    """
    pattern = r'(\d{6})[-](\d{7})'
    
    def replace_func(match):
        front = match.group(1)  # 앞 6자리
        back = match.group(2)   # 뒤 7자리
        # 뒷자리 마스킹
        masked_back = back[:1] + '*' * (len(back) - 1)  # 첫 자리만 남기고 나머지 마스킹
        return f"{front}-{masked_back}"
    
    return re.sub(pattern, replace_func, text)


def mask_address(text: str, keep_chars: int = 10) -> str:
    """
    주소 뒷부분 마스킹 (텍스트)
    
    Args:
        text: 원본 텍스트
        keep_chars: 앞부분 유지할 문자 수
    
    Returns:
        마스킹된 텍스트
    """
    addresses = detect_address(text)
    result = text
    
    # 뒤에서부터 처리 (인덱스 유지)
    for addr, start, end in reversed(addresses):
        if len(addr) > keep_chars:
            # 앞부분 유지, 뒷부분 마스킹
            masked = addr[:keep_chars] + '*' * (len(addr) - keep_chars)
            result = result[:start] + masked + result[end:]
    
    return result


def find_text_in_pdf(pdf_bytes: bytes, search_text: str) -> List[Dict[str, Any]]:
    """
    PDF에서 텍스트 위치 찾기
    
    Args:
        pdf_bytes: PDF 바이너리 데이터
        search_text: 찾을 텍스트
    
    Returns:
        List[Dict]: 각 페이지에서 찾은 텍스트의 위치 정보
        [{"page": int, "rects": [fitz.Rect, ...]}, ...]
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    results = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        # 텍스트 검색 (대소문자 구분 없이, 부분 일치)
        text_instances = page.search_for(search_text, flags=fitz.TEXT_DEHYPHENATE)
        
        if text_instances:
            results.append({
                "page": page_num,
                "rects": text_instances
            })
    
    doc.close()
    return results


def mask_pdf_pii(
    pdf_bytes: bytes,
    mask_resident_numbers: bool = True,
    mask_addresses: bool = True,
    address_keep_chars: int = 10
) -> bytes:
    """
    PDF에서 개인정보 마스킹 처리 (검은색 박스로 덮기)
    
    Args:
        pdf_bytes: 원본 PDF 바이너리 데이터
        mask_resident_numbers: 주민번호 마스킹 여부
        mask_addresses: 주소 마스킹 여부
        address_keep_chars: 주소 앞부분 유지할 문자 수
    
    Returns:
        마스킹된 PDF 바이너리 데이터
    """
    # PDF 열기 (복사본 생성)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # 먼저 텍스트 추출하여 마스킹 대상 찾기
    full_text = ""
    for page_num in range(len(doc)):
        page = doc[page_num]
        full_text += page.get_text()
    
    # 주민번호 마스킹
    if mask_resident_numbers:
        resident_numbers = detect_resident_number(full_text)
        for rn, start_pos, end_pos in resident_numbers:
            # 원본 주민번호와 마스킹된 버전 모두 검색
            # 예: "123456-1234567" 또는 "123456-1******"
            for page_num in range(len(doc)):
                page = doc[page_num]
                # 정확한 텍스트 검색
                text_instances = page.search_for(rn)
                for rect in text_instances:
                    # 뒷자리 부분만 마스킹 (앞 6자리 + 하이픈은 유지)
                    # 주민번호 형식: 123456-1234567
                    # 뒷자리 시작 위치 계산 (대략적으로)
                    x0, y0, x1, y1 = rect
                    width = x1 - x0
                    # 뒷자리 시작 위치 (대략 40% 지점부터)
                    mask_x0 = x0 + width * 0.4
                    mask_rect = fitz.Rect(mask_x0, y0, x1, y1)
                    # 검은색 박스로 덮기
                    page.draw_rect(mask_rect, color=(0, 0, 0), fill=(0, 0, 0), width=0)
    
    # 주소 마스킹
    if mask_addresses:
        addresses = detect_address(full_text)
        for addr, start_pos, end_pos in addresses:
            if len(addr) > address_keep_chars:
                # 뒷부분만 마스킹
                mask_part = addr[address_keep_chars:]
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text_instances = page.search_for(mask_part)
                    for rect in text_instances:
                        # 검은색 박스로 덮기
                        page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0), width=0)
    
    # 마스킹된 PDF를 바이트로 반환
    output_bytes = doc.tobytes()
    doc.close()
    
    return output_bytes


def mask_text_pii(
    text: str,
    mask_resident_numbers: bool = True,
    mask_addresses: bool = True,
    mask_phone_numbers: bool = True,
    address_keep_chars: int = 10
) -> str:
    """
    텍스트에서 개인정보 마스킹 처리
    
    Args:
        text: 원본 텍스트
        mask_resident_numbers: 주민번호 마스킹 여부
        mask_addresses: 주소 마스킹 여부
        mask_phone_numbers: 전화번호 마스킹 여부
        address_keep_chars: 주소 앞부분 유지할 문자 수
    
    Returns:
        마스킹된 텍스트
    """
    result = text
    
    if mask_resident_numbers:
        result = mask_resident_number(result)
    
    if mask_addresses:
        result = mask_address(result, keep_chars=address_keep_chars)
    
    if mask_phone_numbers:
        result = mask_phone_number(result)
    
    return result


def mask_phone_number(text: str) -> str:
    """
    전화번호 마스킹 (텍스트)
    
    Args:
        text: 원본 텍스트
    
    Returns:
        마스킹된 텍스트
    """
    patterns = [
        (r'(\d{2,3})[-.\s]?(\d{3,4})[-.\s]?(\d{4})', r'\1-****-\3'),  # 010-1234-5678 -> 010-****-5678
        (r'\((\d{2,3})\)\s?(\d{3,4})[-.\s]?(\d{4})', r'(\1) ****-\3'),  # (02) 123-4567 -> (02) ****-4567
        (r'(\d{3})(\d{4})(\d{4})', r'\1-****-\3'),  # 01012345678 -> 010-****-5678
    ]
    
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result)
    
    return result


def mask_image_pii(
    image_bytes: bytes,
    ocr_result: Optional[Dict[str, Any]] = None,
    mask_resident_numbers: bool = True,
    mask_addresses: bool = True,
    mask_phone_numbers: bool = True,
    address_keep_chars: int = 10
) -> bytes:
    """
    이미지에서 개인정보 마스킹 처리 (Clova OCR 결과 활용)
    
    Args:
        image_bytes: 원본 이미지 바이너리 데이터
        ocr_result: Clova OCR 결과 (텍스트 위치 정보 포함)
        mask_resident_numbers: 주민번호 마스킹 여부
        mask_addresses: 주소 마스킹 여부
        mask_phone_numbers: 전화번호 마스킹 여부
        address_keep_chars: 주소 앞부분 유지할 문자 수
    
    Returns:
        마스킹된 이미지 바이너리 데이터
    """
    try:
        # 이미지 열기
        image = Image.open(io.BytesIO(image_bytes))
        draw = ImageDraw.Draw(image)
        
        # OCR 결과가 없으면 텍스트 추출 시도
        if ocr_result is None:
            try:
                from app.services.parser_pdf.naver_clova_ocr import extract_text_from_image_clova
                ocr_result = extract_text_from_image_clova(image_bytes, format="jpg")
            except Exception as e:
                print(f"[Mask] OCR 실패, 텍스트 기반 마스킹 불가: {e}")
                return image_bytes
        
        # OCR 필드 정보에서 텍스트 위치 추출
        # Clova OCR 형식: fields는 리스트, 각 필드에 'bounding_box' (또는 'boundingPoly')와 'text' 포함
        fields = ocr_result.get('fields', [])
        if not fields:
            # fields가 없으면 raw에서 추출 시도
            raw = ocr_result.get('raw', {})
            if 'images' in raw and len(raw['images']) > 0:
                raw_fields = raw['images'][0].get('fields', [])
                # raw 형식으로 변환
                fields = [{'text': f.get('inferText', ''), 'bounding_box': f.get('boundingPoly', {})} for f in raw_fields]
        
        if fields:
            full_text = ocr_result.get('text', '')
            
            # 주민번호 마스킹
            if mask_resident_numbers:
                resident_numbers = detect_resident_number(full_text)
                for rn, start_pos, end_pos in resident_numbers:
                    # OCR 필드에서 해당 텍스트 찾기
                    for field in fields:
                        field_text = field.get('text', '') or field.get('inferText', '')
                        if rn in field_text:
                            # bounding_box 또는 boundingPoly에서 좌표 추출
                            bounding_box = field.get('bounding_box', {})
                            bounding_poly = bounding_box.get('boundingPoly', bounding_box) if isinstance(bounding_box, dict) else {}
                            vertices = bounding_poly.get('vertices', []) or bounding_poly.get('value', [])
                            
                            if len(vertices) >= 4:
                                # 좌표 추출
                                x_coords = [v.get('x', 0) for v in vertices if isinstance(v, dict)]
                                y_coords = [v.get('y', 0) for v in vertices if isinstance(v, dict)]
                                
                                if x_coords and y_coords and len(x_coords) == len(y_coords):
                                    x0, y0 = min(x_coords), min(y_coords)
                                    x1, y1 = max(x_coords), max(y_coords)
                                    
                                    # 뒷자리 부분만 마스킹 (대략 40% 지점부터)
                                    mask_x0 = x0 + int((x1 - x0) * 0.4)
                                    draw.rectangle([mask_x0, y0, x1, y1], fill=(0, 0, 0))
            
            # 주소 마스킹
            if mask_addresses:
                addresses = detect_address(full_text)
                for addr, start_pos, end_pos in addresses:
                    if len(addr) > address_keep_chars:
                        # 뒷부분만 마스킹
                        mask_part = addr[address_keep_chars:]
                        for field in fields:
                            field_text = field.get('text', '') or field.get('inferText', '')
                            if mask_part in field_text:
                                bounding_box = field.get('bounding_box', {})
                                bounding_poly = bounding_box.get('boundingPoly', bounding_box) if isinstance(bounding_box, dict) else {}
                                vertices = bounding_poly.get('vertices', []) or bounding_poly.get('value', [])
                                
                                if len(vertices) >= 4:
                                    x_coords = [v.get('x', 0) for v in vertices if isinstance(v, dict)]
                                    y_coords = [v.get('y', 0) for v in vertices if isinstance(v, dict)]
                                    
                                    if x_coords and y_coords and len(x_coords) == len(y_coords):
                                        x0, y0 = min(x_coords), min(y_coords)
                                        x1, y1 = max(x_coords), max(y_coords)
                                        
                                        # 뒷부분 시작 위치 계산
                                        text_start = field_text.find(mask_part)
                                        if text_start >= 0:
                                            ratio = text_start / len(field_text) if field_text else 0
                                            mask_x0 = x0 + int((x1 - x0) * ratio)
                                            draw.rectangle([mask_x0, y0, x1, y1], fill=(0, 0, 0))
            
            # 전화번호 마스킹
            if mask_phone_numbers:
                phone_numbers = detect_phone_number(full_text)
                for phone, start_pos, end_pos in phone_numbers:
                    for field in fields:
                        field_text = field.get('text', '') or field.get('inferText', '')
                        if phone in field_text:
                            bounding_box = field.get('bounding_box', {})
                            bounding_poly = bounding_box.get('boundingPoly', bounding_box) if isinstance(bounding_box, dict) else {}
                            vertices = bounding_poly.get('vertices', []) or bounding_poly.get('value', [])
                            
                            if len(vertices) >= 4:
                                x_coords = [v.get('x', 0) for v in vertices if isinstance(v, dict)]
                                y_coords = [v.get('y', 0) for v in vertices if isinstance(v, dict)]
                                
                                if x_coords and y_coords and len(x_coords) == len(y_coords):
                                    x0, y0 = min(x_coords), min(y_coords)
                                    x1, y1 = max(x_coords), max(y_coords)
                                    
                                    # 중간 부분 마스킹 (앞 3자리, 뒤 4자리 유지)
                                    mask_x0 = x0 + int((x1 - x0) * 0.3)
                                    mask_x1 = x0 + int((x1 - x0) * 0.7)
                                    draw.rectangle([mask_x0, y0, mask_x1, y1], fill=(0, 0, 0))
        
        # 이미지를 바이트로 변환
        output = io.BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()
        
    except Exception as e:
        print(f"[Mask] 이미지 마스킹 실패: {e}")
        import traceback
        traceback.print_exc()
        return image_bytes
