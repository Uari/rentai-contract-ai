import json
from typing import Dict, Any, Optional
from app.services.llm.gemini_wrapper import get_gemini

async def generate_issue_guide_async(title: str, description: str) -> Optional[Dict[str, Any]]:
    """
    LLM을 사용하여 이슈에 대한 맞춤형 가이드(주의사항, 대처법, 법적근거)를 생성합니다.
    """
    llm = get_gemini()
    # Dummy 클래스 체크 (API 키 없는 경우)
    if hasattr(llm, 'invoke') and not hasattr(llm, 'ainvoke'):
        # Dummy wrapper case
        return None

    prompt = f"""
    당신은 한국의 주택 임대차 계약 법률 전문가입니다.
    계약서 분석 시스템이 계약서에서 다음과 같은 잠재적 위험 요소를 감지했습니다.

    [감지된 이슈]
    - 이슈 제목: {title}
    - 상세 내용: {description}

    이 상황에 처한 임차인(세입자)을 위해 다음 3가지 항목으로 구성된 실질적인 조언을 JSON 형식으로 작성해주세요.
    법률 용어를 쉽게 풀어서 설명하고, 임차인이 당장 취해야 할 행동을 구체적으로 제시해야 합니다.

    응답 형식 (JSON):
    {{
        "caution": "이 문제가 방치될 경우 임차인이 겪을 수 있는 금전적 손해나 법적 불이익 (경각심을 주는 어조, 1~2문장)",
        "action": [
            "구체적인 대처 방안 1 (예: 등기부등본의 어디를 확인하라)",
            "구체적인 대처 방안 2 (예: 특약사항에 '~~' 문구를 추가하라)",
            "구체적인 대처 방안 3"
        ],
        "law": "이 이슈와 직접적으로 관련된 '주택임대차보호법' 또는 '민법' 조항 번호와 핵심 내용 요약"
    }}

    주의사항:
    1. 반드시 유효한 JSON 형식만 출력하세요. Markdown 코드블록(```json)을 사용하지 마세요.
    2. 내용은 한국어로 작성하세요.
    3. '관리비', '수선유지', '계약해지', '보증금반환', '근저당' 등 이슈의 성격에 맞는 정확한 법적 근거를 제시하세요.
    """
    
    try:
        # ChatGoogleGenerativeAI는 ainvoke 지원
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        # JSON 파싱 전처리 (혹시 모를 마크다운 제거)
        if content.startswith("```"):
            # 첫 줄에 ```json 또는 ```이 있을 수 있음
            lines = content.split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
            
        data = json.loads(content)
        return data
    except Exception as e:
        # 로그는 찍되, 전체 로직을 방해하지 않도록 None 반환
        print(f"[IssueAdvisor] 가이드 생성 실패: {e}")
        return None
