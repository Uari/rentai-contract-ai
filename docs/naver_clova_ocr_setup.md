# Naver Clova OCR 설정 가이드

Naver Clova OCR은 한글 인식에 최적화된 OCR 서비스입니다.

## 📊 특징

- **정확도**: 95~99% (Tesseract: 70~80%, EasyOCR: 85~90%)
- **속도**: 빠름 (평균 1~2초/페이지)
- **가격**: 월 1,000건 무료
- **한글 특화**: 한글 인식 최적화

---

## 🚀 설정 방법

### 1단계: Naver Cloud Platform 계정 생성

1. https://www.ncloud.com 접속
2. 회원가입 (무료)
3. 로그인

### 2단계: Clova OCR 서비스 신청

1. **콘솔 접속**: https://console.ncloud.com
2. **Services > AI·NAVER API** 선택
3. **Clova OCR** 선택
4. **이용 신청하기** 클릭
5. **약관 동의** 및 **서비스 이용 신청**

### 3단계: 도메인 등록

1. **Clova OCR 콘솔**에서 **Domain** 탭 선택
2. **도메인 등록** 클릭
3. 도메인 입력:
   - 로컬 테스트: `localhost` 또는 `127.0.0.1`
   - 운영 서버: 실제 도메인 입력
4. **등록** 클릭

### 4단계: API 키 확인

1. **Clova OCR 콘솔**에서 **API Gateway** 탭 선택
2. 다음 정보 확인:
   - **API Gateway 호출 URL**: `https://**********.apigw.ntruss.com/custom/v1/*****/document`
   - **Secret Key**: `***********************`

### 5단계: 프로젝트에 API 키 설정

`.env` 파일에 다음 내용을 추가:

```env
# Naver Clova OCR
NAVER_CLOVA_API_URL=https://**********.apigw.ntruss.com/custom/v1/*****/document
NAVER_CLOVA_SECRET_KEY=***********************
```

**주의**: 
- `NAVER_CLOVA_API_URL`은 전체 URL 복사
- `NAVER_CLOVA_SECRET_KEY`는 Secret Key 값만 복사

---

## 💡 사용 방법

### 기본 사용

```bash
# 이미지 파일
python tools/extract_with_clova_ocr.py image.jpg --output result.txt

# PDF 파일
python tools/extract_with_clova_ocr.py document.pdf --output result.txt
```

### 고급 옵션

```bash
# 신뢰도 필터링 (90% 이상만)
python tools/extract_with_clova_ocr.py image.jpg --min-confidence 0.9

# 신뢰도 표시
python tools/extract_with_clova_ocr.py image.jpg --show-confidence
```

---

## 📝 예시

### 입력
```bash
python tools/extract_with_clova_ocr.py lease_contract.jpg --output clova_result.txt
```

### 출력
```
[INFO] 파일: lease_contract.jpg
[INFO] 크기: 2323.28 KB
============================================================
[INFO] Naver Clova OCR 처리 중...
[INFO] 정확도: 95~99% (한글 특화)
[Naver Clova OCR] 이미지 파일 감지: lease_contract.jpg
[Naver Clova OCR] API 호출 중...
[Naver Clova OCR] 응답 수신: 200
============================================================
[결과] 타입: image
[결과] 페이지 수: 1
[결과] 텍스트 길이: 3245자
============================================================
[통계] 평균 신뢰도: 98.5%
[통계] 최소 신뢰도: 92.3%
[통계] 최대 신뢰도: 99.9%
============================================================

[저장 완료] clova_result.txt

[성공] Naver Clova OCR 완료!

💡 정확도가 매우 높습니다 (95~99%)
💡 월 1,000건까지 무료입니다
```

---

## 🔧 API 통합 (코드)

### Python 코드에서 사용

```python
from app.services.parser_pdf.naver_clova_ocr import extract_text_auto_clova

# 파일 읽기
with open("image.jpg", "rb") as f:
    file_bytes = f.read()

# OCR 수행
result = extract_text_auto_clova(file_bytes, "image.jpg")

# 결과 확인
print(result['text'])  # 추출된 텍스트
print(f"정확도: {result['type']}")  # image 또는 pdf
```

### FastAPI 엔드포인트에서 사용

```python
from fastapi import FastAPI, UploadFile, File
from app.services.parser_pdf.naver_clova_ocr import extract_text_auto_clova

app = FastAPI()

@app.post("/ocr/clova")
async def ocr_with_clova(file: UploadFile = File(...)):
    content = await file.read()
    result = extract_text_auto_clova(content, file.filename)
    return {
        "text": result['text'],
        "type": result['type'],
        "page_count": result['page_count']
    }
```

---

## 💰 가격 정책

| 구분 | 건수 | 가격 |
|-----|------|------|
| **무료** | 월 1,000건 | 무료 |
| 추가 | 1,000건당 | 약 10,000원 |

**참고**: 1건 = 1개 이미지 또는 PDF 1페이지

---

## ⚠️ 주의사항

### 1. 도메인 제한
- 등록된 도메인에서만 API 호출 가능
- 로컬 테스트: `localhost` 등록 필요

### 2. 파일 크기 제한
- 최대 파일 크기: **10MB**
- 권장: 5MB 이하

### 3. 이미지 형식
- 지원: JPG, PNG, BMP, TIFF
- 권장: JPG (용량 대비 품질 우수)

### 4. API 호출 제한
- 초당 최대 호출: **10회**
- 1분당 최대 호출: **1,000회**

---

## 🐛 문제 해결

### "API 키가 설정되지 않았습니다" 오류

**원인**: `.env` 파일에 API 키가 없음

**해결**:
1. `.env` 파일 확인
2. `NAVER_CLOVA_API_URL`과 `NAVER_CLOVA_SECRET_KEY` 추가
3. 값이 올바른지 확인

### "도메인이 등록되지 않았습니다" 오류

**원인**: 현재 도메인이 Clova OCR 콘솔에 등록되지 않음

**해결**:
1. Clova OCR 콘솔 > Domain 탭
2. `localhost` 또는 사용 중인 도메인 등록

### "월 사용량을 초과했습니다" 오류

**원인**: 무료 한도(1,000건) 초과

**해결**:
1. 다음 달까지 대기 (무료)
2. 또는 유료 전환

### API 응답이 느림

**원인**: 이미지 크기가 너무 큼

**해결**:
1. 이미지 크기 줄이기 (5MB 이하 권장)
2. 해상도 낮추기 (300 DPI 정도면 충분)

---

## 📚 추가 리소스

- **Naver Cloud Platform**: https://www.ncloud.com
- **Clova OCR 문서**: https://www.ncloud.com/product/aiService/ocr
- **API 가이드**: https://api.ncloud-docs.com/docs/ai-naver-clovaocr

---

## 🎯 다른 OCR과 비교

| OCR 엔진 | 정확도 | 속도 | 한글 지원 | 가격 |
|---------|--------|------|----------|------|
| Tesseract | 70~80% | 빠름 | 보통 | 무료 |
| EasyOCR | 85~90% | 보통 | 좋음 | 무료 |
| **Naver Clova** | **95~99%** | **빠름** | **매우 좋음** | **1000건 무료** |
| Google Cloud Vision | 95~98% | 빠름 | 좋음 | 1000건 무료 |

**결론**: 한글 문서는 Naver Clova OCR이 최고!

