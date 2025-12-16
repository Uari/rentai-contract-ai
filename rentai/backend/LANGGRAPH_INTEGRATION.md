# LangGraph 통합 방안

## 📋 개요

현재 프로젝트의 계약서 분석 워크플로우를 LangGraph로 구조화하여 더 명확하고 유지보수 가능한 시스템으로 개선합니다.

## 🎯 통합 목표

1. **워크플로우 시각화**: 복잡한 분석 프로세스를 그래프로 명확하게 표현
2. **상태 관리**: 각 단계의 상태를 명시적으로 관리
3. **조건부 분기**: OCR 필요 여부, 이슈 존재 여부 등 동적 분기 처리
4. **에러 복구**: Durable Execution으로 중단 지점부터 재개 가능
5. **확장성**: 새로운 분석 단계 추가 용이

## 🔄 현재 워크플로우 분석

```
1. 파일 업로드 및 검증
   ↓
2. 파일 타입 판별 (이미지/PDF)
   ↓
3. 텍스트 추출
   ├─ 이미지 → Clova OCR
   ├─ PDF (일반) → parse_pdf
   └─ PDF (스캔본) → Clova OCR (fallback)
   ↓
4. 문장 분리
   ↓
5. 필드 추출 (extract_all)
   ↓
6. 표 추출 (extract_tables)
   ↓
7. 서명 감지 (detect_signature)
   ↓
8. 룰 평가 (evaluate_rules)
   ↓
9. 이슈별 처리 (반복)
   ├─ RAG 검색
   └─ LLM 가이드 생성
   ↓
10. 결과 포맷팅 및 반환
```

## 🏗️ LangGraph 구조 설계

### 상태 (State) 정의

```python
from typing import TypedDict, List, Dict, Any, Optional
from typing_extensions import Annotated
from operator import add

class AnalysisState(TypedDict):
    # 입력
    file_content: bytes
    filename: str
    use_ocr: bool
    k: int  # RAG 검색 개수
    
    # 중간 결과
    file_type: Optional[str]  # "image" | "pdf" | None
    text_full: str
    page_count: int
    sentences: List[Dict[str, Any]]
    
    # 추출 결과
    extracted_fields: Dict[str, Any]
    tables: List[Any]
    signature_detected: bool
    
    # 분석 결과
    risk: Dict[str, Any]
    issues: List[Dict[str, Any]]
    all_rag_refs: Annotated[List[Dict[str, Any]], add]  # 자동 병합
    
    # 최종 결과
    result: Optional[Dict[str, Any]]
    error: Optional[str]
```

### 그래프 구조

```
START
  ↓
[validate_file] - 파일 검증
  ↓
[determine_file_type] - 파일 타입 판별
  ↓
[extract_text] - 텍스트 추출
  ├─→ [extract_with_ocr] (이미지 또는 OCR 필요)
  └─→ [extract_with_parser] (일반 PDF)
       └─→ [check_scan] - 스캔본 감지
            └─→ [extract_with_ocr] (텍스트 부족 시)
  ↓
[prepare_sentences] - 문장 분리
  ↓
[extract_fields] - 필드 추출
  ↓
[extract_tables] - 표 추출
  ↓
[detect_signature] - 서명 감지
  ↓
[evaluate_rules] - 룰 평가
  ↓
[process_issues] - 이슈 처리
  ├─→ [rag_search] (각 이슈별)
  └─→ [generate_guide] (각 이슈별)
  ↓
[format_result] - 결과 포맷팅
  ↓
END
```

## 📦 구현 계획

### Phase 1: 기본 구조 (현재)
- 상태 클래스 정의
- 기본 노드 함수 구현
- 그래프 구성

### Phase 2: 고급 기능
- Human-in-the-Loop (이슈 승인)
- 병렬 처리 (이슈별 RAG/LLM)
- 에러 복구 (Durable Execution)

### Phase 3: 최적화
- 캐싱
- 스트리밍 응답
- 모니터링 및 로깅

## 🔧 사용 예시

### 기존 방식
```python
@app.post("/analyze/pdf")
async def analyze_pdf(file: UploadFile, ...):
    # 모든 로직이 하나의 함수에...
    content = await file.read()
    # ... 300줄의 코드
```

### LangGraph 방식
```python
from app.services.workflow.contract_analyzer import create_analysis_graph

@app.post("/analyze/pdf")
async def analyze_pdf(file: UploadFile, use_ocr: bool = False, k: int = 3):
    graph = create_analysis_graph()
    
    initial_state = {
        "file_content": await file.read(),
        "filename": file.filename,
        "use_ocr": use_ocr,
        "k": k,
    }
    
    result = await graph.ainvoke(initial_state)
    return result["result"]
```

## 📊 장점

1. **가독성**: 각 단계가 명확히 분리됨
2. **테스트 용이**: 각 노드를 독립적으로 테스트 가능
3. **디버깅**: 각 단계의 상태를 확인 가능
4. **확장성**: 새로운 노드 추가가 쉬움
5. **재사용성**: 다른 워크플로우에서 노드 재사용 가능
6. **시각화**: LangGraph Studio로 워크플로우 시각화 가능

## 🚀 다음 단계

1. `app/services/workflow/` 디렉토리 생성
2. 상태 클래스 및 노드 함수 구현
3. 그래프 구성 및 통합
4. 기존 API 엔드포인트에 통합
5. 테스트 및 검증
