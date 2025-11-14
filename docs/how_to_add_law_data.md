# 법령 데이터 추가 가이드

RentAI 프로토타입에 법령, 법적 근거 데이터를 추가하는 방법을 안내합니다.

## 📁 데이터 저장 위치

법령 데이터는 다음 폴더에 텍스트 파일로 저장합니다:
```
rentai/data/embeddings/
```

지원 형식:
- `.txt` 파일
- `.md` (Markdown) 파일

## 📝 파일 작성 형식

### 기본 형식

각 파일은 법령 내용을 일반 텍스트로 작성합니다:

```text
주택임대차보호법 제3조 (대항력)

임차인이 주택의 인도와 주민등록의 전입신고를 마친 경우에는 그 후에 그 주택에 대하여 소유권을 취득한 제3자에 대하여도 임대차보호법에 따른 권리를 주장할 수 있다.

[출처] 주택임대차보호법 제3조
```

### 권장 구조

법령 문서는 다음과 같은 구조로 작성하면 검색 품질이 향상됩니다:

```text
# 주택임대차보호법 제3조 - 대항력

## 조문
임차인이 주택의 인도와 주민등록의 전입신고를 마친 경우에는 그 후에 그 주택에 대하여 소유권을 취득한 제3자에 대하여도 임대차보호법에 따른 권리를 주장할 수 있다.

## 요약
임차인은 주민등록 전입신고를 하면 제3자에게도 대항할 수 있는 권리를 가집니다.

## 관련 키워드
대항력, 전입신고, 주민등록, 임차권, 우선변제권

## 출처
주택임대차보호법 제3조
```

## 🚀 데이터 추가 방법

### 방법 1: 기본 사용 (모든 파일 추가)

1. 법령 텍스트 파일을 `data/embeddings/` 폴더에 저장
2. ingest 스크립트 실행:

```bash
cd rentai
python tools/ingest.py
```

### 방법 2: 특정 파일만 추가

```bash
python tools/ingest.py --file data/embeddings/주택임대차보호법.txt
```

### 방법 3: 기존 데이터 삭제 후 재추가

기존 벡터스토어를 완전히 삭제하고 새로 생성:

```bash
python tools/ingest.py --clear
```

### 방법 4: 청킹 크기 조정

긴 법령 문서의 경우 청킹 크기를 조정할 수 있습니다:

```bash
python tools/ingest.py --chunk-size 1000 --chunk-overlap 200
```

**파라미터 설명:**
- `--chunk-size`: 각 청크의 최대 문자 수 (기본: 700)
- `--chunk-overlap`: 청크 간 겹치는 부분 (기본: 120)

## 📋 단계별 예시

### 예시 1: 주택임대차보호법 추가

1. **파일 생성**
   ```bash
   # rentai/data/embeddings/housing_lease_law.txt 파일 생성
   ```

2. **내용 작성** (예시)
   ```text
   주택임대차보호법 제1조 (목적)
   이 법은 주택의 임대차에 관하여 민법에 대한 특례를 규정함으로써 임차인의 주거안정을 보장하고 국민주거생활의 안정에 기여함을 목적으로 한다.

   주택임대차보호법 제2조 (적용범위)
   이 법은 주택의 임대차에 적용한다. 다만, 주택의 일부를 임대하는 경우에는 그 임대하는 부분이 독립된 주거생활을 할 수 있는 구조로 된 때에 한한다.
   ```

3. **벡터스토어에 추가**
   ```bash
   python tools/ingest.py
   ```

4. **확인**
   ```bash
   # Python에서 확인
   from app.services.rag.retrieval import kb_status
   print(kb_status())
   # 출력: {"name": "lease-law", "count": 123, "persist_directory": "..."}
   ```

## 🔍 데이터 확인

### 벡터스토어 상태 확인

Python 스크립트로 확인:

```python
from app.services.rag.retrieval import kb_status, search_law

# 상태 확인
status = kb_status()
print(f"문서 수: {status['count']}개")
print(f"저장 위치: {status['persist_directory']}")

# 검색 테스트
results = search_law("확정일자", k=3)
for r in results:
    print(f"점수: {r['score']:.3f}")
    print(f"출처: {r['source']}")
    print(f"내용: {r['text'][:100]}...")
    print()
```

### API로 확인

FastAPI 서버 실행 후:

```bash
# 벡터스토어 상태 확인
curl http://localhost:8000/api/rules/kb-status
```

## ⚠️ 주의사항

1. **중복 추가 방지**
   - 현재 스크립트는 중복을 자동으로 제거하지 않습니다
   - 같은 파일을 여러 번 실행하면 중복이 추가될 수 있습니다
   - 기존 데이터를 완전히 교체하려면 `--clear` 옵션을 사용하세요

2. **파일 인코딩**
   - 반드시 UTF-8 인코딩으로 저장하세요
   - Windows에서 메모장으로 저장할 때 "UTF-8" 인코딩을 선택하세요

3. **청킹 크기**
   - 너무 작으면: 문맥 손실, 검색 품질 저하
   - 너무 크면: 검색 정확도 저하, 임베딩 품질 저하
   - 권장: 500~1000자, overlap 100~200자

4. **메타데이터**
   - 현재는 `source` (파일 경로)만 저장됩니다
   - 향후 법령명, 조문 번호 등을 메타데이터로 추가할 수 있습니다

## 🔧 고급 사용법

### 여러 법령 파일을 한 번에 추가

```bash
# data/embeddings/ 폴더에 여러 파일 추가
# 예: housing_lease_law.txt, commercial_lease_law.txt, etc.

# 모든 파일을 한 번에 처리
python tools/ingest.py
```

### 특정 법령만 업데이트

```bash
# 특정 파일만 다시 추가 (기존 데이터는 유지)
python tools/ingest.py --file data/embeddings/housing_lease_law.txt
```

## 📚 추천 데이터 소스

1. **법제처 국가법령정보센터**
   - https://www.law.go.kr
   - 법령 전문 다운로드 가능

2. **대법원 판례**
   - https://glaw.scourt.go.kr
   - 관련 판례 추가 시 검색 품질 향상

3. **법률 해설서**
   - 전문가가 작성한 해설서는 검색 품질에 도움

## 🐛 문제 해결

### "파일을 찾을 수 없습니다" 오류

- 파일 경로가 올바른지 확인
- `data/embeddings/` 폴더가 존재하는지 확인

### "빈 파일" 경고

- 파일에 내용이 있는지 확인
- 인코딩이 UTF-8인지 확인

### 검색 결과가 나오지 않음

- 벡터스토어에 데이터가 추가되었는지 확인: `kb_status()` 호출
- 검색어를 더 구체적으로 작성
- `k` 값을 늘려서 더 많은 결과 확인

## 📞 추가 도움

문제가 발생하면 다음을 확인하세요:
1. `vectorstore/chroma/` 폴더가 올바르게 생성되었는지
2. 임베딩 모델이 올바르게 로드되는지
3. ChromaDB 버전 호환성

