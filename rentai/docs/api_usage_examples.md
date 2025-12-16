# API 사용 예시

`rentai_prototype` 프로젝트의 주요 API 엔드포인트 사용 방법입니다.

---

## 📡 서버 실행

```bash
cd backend
python fastapi_app.py
```

서버 주소: `http://localhost:8000`

---

## 🎯 API 엔드포인트

### 1. 텍스트 추출 (Naver Clova OCR) - 🌟 권장

**최고 정확도 (95~99%)로 한글 문서 인식**

#### 엔드포인트
```
POST /extract/text/clova
```

#### Python 예시
```python
import requests

url = "http://localhost:8000/extract/text/clova"
files = {"file": open("lease_contract.jpg", "rb")}
params = {
    "format": "full",  # 'full' 또는 'pages'
    "min_confidence": 0.9  # 신뢰도 필터링 (선택)
}

response = requests.post(url, files=files, params=params)
result = response.json()

print(f"추출된 텍스트: {result['text']}")
print(f"텍스트 길이: {result['text_length']}자")
print(f"OCR 엔진: {result['ocr_engine']}")
```

#### cURL 예시
```bash
curl -X POST "http://localhost:8000/extract/text/clova?format=full" \
  -F "file=@lease_contract.jpg"
```

#### 응답 예시
```json
{
  "filename": "lease_contract.jpg",
  "type": "image",
  "page_count": 1,
  "format": "full",
  "text": "부동산 임대차 계약서\n\n임대인: 홍길동\n...",
  "text_length": 3245,
  "ocr_engine": "naver_clova"
}
```

---

### 2. 텍스트 추출 (일반 OCR)

**Tesseract 또는 일반 PDF 파서 사용**

#### 엔드포인트
```
POST /extract/text
```

#### Python 예시
```python
import requests

url = "http://localhost:8000/extract/text"
files = {"file": open("document.pdf", "rb")}
params = {
    "use_ocr": True,  # OCR 사용 여부
    "format": "full"  # 'full' 또는 'pages'
}

response = requests.post(url, files=files, params=params)
result = response.json()

print(f"추출된 텍스트: {result['text']}")
```

---

### 3. PDF 분석 (RAG 기반)

**법률 문서 분석 및 조언 제공**

#### 엔드포인트
```
POST /analyze
```

#### Python 예시
```python
import requests

url = "http://localhost:8000/analyze"
files = {"file": open("lease_contract.pdf", "rb")}
data = {
    "user_question": "이 계약서에 문제가 있나요?"
}

response = requests.post(url, files=files, data=data)
result = response.json()

print(f"분석 결과: {result['answer']}")
print(f"참조 법령: {result['references']}")
```

#### 응답 예시
```json
{
  "answer": "계약서를 검토한 결과...",
  "references": [
    {
      "source": "주택임대차보호법",
      "content": "제3조 (대항력) ...",
      "score": 0.95
    }
  ],
  "page_count": 3,
  "text_length": 2500
}
```

---

### 4. RAG 검색

**법령 데이터베이스에서 관련 조항 검색**

#### 엔드포인트
```
POST /rag/search
```

#### Python 예시
```python
import requests

url = "http://localhost:8000/rag/search"
data = {
    "query": "전월세 계약 시 주의사항",
    "top_k": 5
}

response = requests.post(url, json=data)
results = response.json()

for i, result in enumerate(results['results'], 1):
    print(f"{i}. {result['content']}")
    print(f"   출처: {result['metadata']['source']}")
    print(f"   유사도: {result['score']:.2%}")
```

---

### 5. 벡터 DB 상태 확인

#### 엔드포인트
```
GET /rag/status
```

#### Python 예시
```python
import requests

url = "http://localhost:8000/rag/status"
response = requests.get(url)
status = response.json()

print(f"문서 수: {status['document_count']}")
print(f"컬렉션: {status['collections']}")
```

---

## 🔧 명령줄 도구 사용

### Naver Clova OCR 사용

```bash
# 기본 사용
python tools/extract_with_clova_ocr.py image.jpg --output result.txt

# 신뢰도 필터링
python tools/extract_with_clova_ocr.py image.jpg --min-confidence 0.9

# PDF 파일
python tools/extract_with_clova_ocr.py document.pdf --output result.txt
```

### EasyOCR 사용 (오프라인)

```bash
python tools/extract_with_easyocr.py image.jpg --output result.txt
```

### PDF 텍스트 추출

```bash
python tools/extract_pdf_text.py document.pdf --output result.txt
```

---

## 📊 OCR 엔진 비교

| 기능 | Naver Clova | EasyOCR | Tesseract |
|-----|-------------|---------|-----------|
| **정확도** | ⭐⭐⭐⭐⭐ (95~99%) | ⭐⭐⭐⭐ (85~90%) | ⭐⭐⭐ (70~80%) |
| **한글 지원** | 매우 우수 | 우수 | 보통 |
| **속도** | 빠름 | 보통 | 빠름 |
| **비용** | 월 1000건 무료 | 무료 | 무료 |
| **인터넷** | 필요 | 불필요 | 불필요 |

**결론**: 한글 문서는 **Naver Clova OCR** 추천! 🎯

---

## 🐛 문제 해결

### "Naver Clova OCR이 설정되지 않았습니다" 오류

**해결**:
1. `.env` 파일에 API 키 추가
2. `docs/naver_clova_ocr_setup.md` 참고

### "파일이 너무 큽니다" 오류

**해결**:
1. 파일 크기를 20MB 이하로 줄이기
2. 이미지 해상도 낮추기 (300 DPI 권장)

### "지원하지 않는 파일" 오류

**해결**:
- 지원 파일: PDF, JPG, PNG, BMP, TIFF
- 파일 확장자 확인

---

## 📚 추가 문서

- **Naver Clova OCR 설정**: `docs/naver_clova_ocr_setup.md`
- **법령 데이터 추가**: `docs/how_to_add_law_data.md`
- **환경 설정**: `docs/env_setup_guide.md`

