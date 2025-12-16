# -*- coding: utf-8 -*-
"""
주소 보정 모듈

OCR 오류로 인해 잘못 추출된 주소를 LLM을 사용하여 보정
"""
import json
import re
from typing import Optional, Dict, Any
from app.services.llm.gemini_wrapper import get_gemini


async def correct_address_async(
    extracted_address: str,
    context_text: Optional[str] = None
) -> Optional[str]:
    """
    LLM을 사용하여 주소를 보정합니다.
    
    Args:
        extracted_address: 추출된 주소 (예: "지 경기도 광명시 지 목 대")
        context_text: 주소 주변 컨텍스트 텍스트 (선택적)
    
    Returns:
        보정된 주소 (예: "경기도 광명시 하안동") 또는 None
    """
    llm = get_gemini()
    
    # Dummy 클래스 체크 (API 키 없는 경우)
    if hasattr(llm, 'invoke') and not hasattr(llm, 'ainvoke'):
        # Dummy wrapper case - 원본 반환
        return extracted_address
    
    # 컨텍스트가 있으면 포함
    context_part = ""
    if context_text:
        # 주소 주변 200자만 사용
        context_snippet = context_text[:200] if len(context_text) > 200 else context_text
        context_part = f"\n\n[계약서 주변 텍스트]\n{context_snippet}"
    
    prompt = f"""
당신은 한국 주소 전문가입니다. OCR 오류로 인해 잘못 추출된 주소를 올바른 주소로 보정해주세요.

[추출된 주소 (OCR 오류 포함 가능)]
{extracted_address}

{context_part}

위 추출된 주소는 OCR 오류로 인해 일부 문자가 잘못 인식되었을 수 있습니다.
다음 규칙에 따라 올바른 한국 주소 형식으로 보정해주세요:

1. **주소 형식**: 시/도 → 시/군/구 → 동/읍/면/리 순서
2. **일반적인 오류 패턴**:
   - "지" → 제거 (OCR 오인식)
   - "지 목 대" → "하안동" (음성 유사성)
   - "목" → "동" (OCR 오인식)
   - 불필요한 공백 제거
3. **보정 예시**:
   - "지 경기도 광명시 지 목 대" → "경기도 광명시 하안동"
   - "서울특별시 강남구 테헤란로 123" → "서울특별시 강남구 테헤란로 123"
   - "경기도 성남시 분당구 정자동 456" → "경기도 성남시 분당구 정자동 456"

**중요**: 
- 반드시 유효한 JSON 형식만 출력하세요. Markdown 코드블록(```json)을 사용하지 마세요.
- 보정이 불가능하거나 주소가 아닌 경우 null을 반환하세요.
- 보정된 주소만 반환하세요 (설명 없이).

응답 형식 (JSON):
{{
    "corrected_address": "보정된 주소 또는 null"
}}
"""
    
    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        # JSON 파싱 전처리 (혹시 모를 마크다운 제거)
        if content.startswith("```"):
            lines = content.split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        
        data = json.loads(content)
        corrected = data.get("corrected_address")
        
        # null이거나 빈 문자열이면 원본 반환
        if not corrected or corrected == "null":
            return extracted_address
        
        return corrected
        
    except Exception as e:
        error_str = str(e)
        # 할당량 초과 또는 API 에러인 경우
        if "quota" in error_str.lower() or "429" in error_str or "rate limit" in error_str.lower():
            print(f"[AddressCorrector] Gemini API 할당량 초과 또는 Rate Limit - 기본 보정 사용")
        else:
            print(f"[AddressCorrector] 주소 보정 실패: {error_str[:200]}")  # 에러 메시지 일부만 출력
        # 에러 발생 시 원본 반환 (기본 정규식 보정은 이미 extract_all에서 수행됨)
        return extracted_address


def correct_address_sync(
    extracted_address: str,
    context_text: Optional[str] = None
) -> str:
    """
    동기 버전 (LLM 사용 안 함, 기본 정규식 보정만)
    
    Args:
        extracted_address: 추출된 주소
        context_text: 주소 주변 컨텍스트 텍스트 (선택적)
    
    Returns:
        기본 보정된 주소
    """
    if not extracted_address:
        return extracted_address
    
    # 기본 정규식 보정
    corrected = extracted_address
    
    # 앞뒤 불필요한 문자 제거
    corrected = re.sub(r'^[지\s]+', '', corrected)  # 앞의 "지" 제거
    corrected = re.sub(r'\s+', ' ', corrected)  # 연속 공백 제거
    corrected = corrected.strip()
    
    # 일반적인 OCR 오류 패턴 보정
    corrections = {
        r'지\s*목\s*대': '하안동',  # "지 목 대" → "하안동"
        r'지\s*목': '동',  # "지 목" → "동"
        r'\s+목\s+': ' 동 ',  # " 목 " → " 동 "
    }
    
    for pattern, replacement in corrections.items():
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
    
    return corrected
