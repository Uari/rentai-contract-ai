# LangGraph 워크플로우 모듈

## 📁 파일 구조

```
workflow/
├── __init__.py          # 모듈 초기화
├── state.py             # 상태 정의 (AnalysisState)
├── nodes.py             # 노드 함수들 (각 처리 단계)
├── graph.py             # 그래프 구성 및 실행
├── example_usage.py     # 사용 예시
└── README.md            # 이 파일
```

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
pip install langgraph
```

### 2. 기본 사용법

```python
from app.services.workflow.graph import run_analysis

# 파일 읽기
with open("contract.pdf", "rb") as f:
    content = f.read()

# 분석 실행
result = await run_analysis(
    file_content=content,
    filename="contract.pdf",
    use_ocr=False,
    k=3
)

print(result)
```

### 3. FastAPI 통합

```python
from fastapi import FastAPI, UploadFile, File
from app.services.workflow.graph import run_analysis

app = FastAPI()

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    content = await file.read()
    result = await run_analysis(
        file_content=content,
        filename=file.filename,
        use_ocr=False,
        k=3
    )
    return result
```

## 📊 워크플로우 구조

```
START
  ↓
[validate_file] - 파일 검증
  ↓
[determine_file_type] - 파일 타입 판별
  ↓
[조건 분기]
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
[process_issues] - 이슈 처리 (RAG + LLM)
  ↓
[format_result] - 결과 포맷팅
  ↓
END
```

## 🔧 노드 함수 설명

### validate_file
- 파일 확장자 검증
- 파일 크기 검증

### determine_file_type
- 이미지/PDF 파일 타입 판별

### extract_with_ocr
- Clova OCR을 사용한 텍스트 추출

### extract_with_parser
- 일반 PDF 파서를 사용한 텍스트 추출

### check_scan
- 스캔본 감지 (텍스트가 적으면 OCR로 재시도)

### prepare_sentences
- 텍스트를 문장 단위로 분리

### extract_fields
- 계약서 필드 추출 (확정일자, 전입신고 등)

### extract_tables
- 표 추출

### detect_signature
- 서명 감지

### evaluate_rules
- 룰 엔진으로 위험 요소 평가

### process_issues
- 각 이슈별로 RAG 검색 및 LLM 가이드 생성

### format_result
- 최종 결과를 API 응답 형식으로 포맷팅

## 🎯 장점

1. **명확한 구조**: 각 단계가 독립적인 노드로 분리
2. **시각화**: LangGraph Studio로 워크플로우 시각화 가능
3. **테스트 용이**: 각 노드를 독립적으로 테스트 가능
4. **디버깅**: 각 단계의 상태를 확인 가능
5. **확장성**: 새로운 노드 추가가 쉬움
6. **에러 복구**: Durable Execution으로 중단 지점부터 재개 가능

## 🔄 기존 코드와의 통합

기존 `fastapi_app.py`의 `/analyze/pdf` 엔드포인트를 점진적으로 LangGraph로 마이그레이션할 수 있습니다:

1. **옵션 1**: 새로운 엔드포인트 추가 (`/analyze/pdf/langgraph`)
2. **옵션 2**: 기존 엔드포인트를 LangGraph로 교체
3. **옵션 3**: A/B 테스트로 두 방식 모두 유지

## 📈 향후 개선 사항

- [ ] Human-in-the-Loop (이슈 승인)
- [ ] 병렬 처리 최적화
- [ ] Durable Execution (장애 복구)
- [ ] 스트리밍 응답
- [ ] 캐싱
- [ ] 모니터링 및 로깅

## 🐛 문제 해결

### ImportError: cannot import name 'StateGraph'
- `langgraph` 패키지가 설치되지 않았습니다. `pip install langgraph` 실행

### CLOVA_OCR_AVAILABLE 관련 에러
- Clova OCR은 선택적 기능입니다. 없어도 일반 PDF 파싱은 동작합니다.

### 비동기 함수 에러
- `process_issues` 노드는 비동기 함수입니다. `await`를 사용해야 합니다.
