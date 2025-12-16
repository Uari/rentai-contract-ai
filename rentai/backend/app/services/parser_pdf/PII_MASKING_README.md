# 개인정보 마스킹 기능

## 📋 개요

주민번호 뒷자리와 주소 뒷부분을 검은색 박스로 마스킹 처리하는 기능입니다.

## 🎯 기능

### 1. 주민번호 마스킹
- **형식**: `123456-1234567`
- **마스킹**: 뒷자리 7자리 중 첫 자리만 남기고 나머지 마스킹
- **결과**: `123456-1******`

### 2. 주소 마스킹
- **형식**: `서울특별시 강남구 테헤란로 123`
- **마스킹**: 앞부분 일부만 유지하고 뒷부분 마스킹
- **결과**: `서울특별시 강남구 테헤란로 ***` (기본 10자 유지)

## 🚀 사용 방법

### API 엔드포인트

#### 1. PDF 마스킹 (`/mask/pdf`)
```bash
POST /mask/pdf
Content-Type: multipart/form-data

파라미터:
- file: PDF 파일
- mask_resident_numbers: 주민번호 마스킹 여부 (기본: true)
- mask_addresses: 주소 마스킹 여부 (기본: true)
- address_keep_chars: 주소 앞부분 유지할 문자 수 (기본: 10)
```

**예시:**
```python
import requests

files = {"file": open("contract.pdf", "rb")}
params = {
    "mask_resident_numbers": True,
    "mask_addresses": True,
    "address_keep_chars": 10
}

response = requests.post("http://localhost:8000/mask/pdf", files=files, params=params)
with open("masked_contract.pdf", "wb") as f:
    f.write(response.content)
```

#### 2. 텍스트 마스킹 (`/mask/text`)
```bash
POST /mask/text

파라미터:
- text: 마스킹할 텍스트
- mask_resident_numbers: 주민번호 마스킹 여부 (기본: true)
- mask_addresses: 주소 마스킹 여부 (기본: true)
- address_keep_chars: 주소 앞부분 유지할 문자 수 (기본: 10)
```

**예시:**
```python
import requests

params = {
    "text": "주민번호: 123456-1234567, 주소: 서울특별시 강남구 테헤란로 123",
    "mask_resident_numbers": True,
    "mask_addresses": True,
    "address_keep_chars": 10
}

response = requests.post("http://localhost:8000/mask/text", params=params)
result = response.json()
print(result["masked"])
# 출력: 주민번호: 123456-1******, 주소: 서울특별시 강남구 테헤란로 ***
```

### Python 코드에서 직접 사용

```python
from app.services.parser_pdf.pii_masking import (
    mask_pdf_pii,
    mask_text_pii,
    mask_resident_number,
    mask_address
)

# PDF 마스킹
with open("contract.pdf", "rb") as f:
    pdf_bytes = f.read()

masked_pdf = mask_pdf_pii(
    pdf_bytes=pdf_bytes,
    mask_resident_numbers=True,
    mask_addresses=True,
    address_keep_chars=10
)

with open("masked_contract.pdf", "wb") as f:
    f.write(masked_pdf)

# 텍스트 마스킹
text = "주민번호: 123456-1234567, 주소: 서울특별시 강남구 테헤란로 123"
masked_text = mask_text_pii(
    text=text,
    mask_resident_numbers=True,
    mask_addresses=True,
    address_keep_chars=10
)
print(masked_text)
```

## ⚙️ 설정 옵션

### 주소 마스킹 문자 수 조정
- `address_keep_chars=10`: 기본값 (앞 10자 유지)
- `address_keep_chars=15`: 앞 15자 유지
- `address_keep_chars=5`: 앞 5자만 유지

### 선택적 마스킹
- `mask_resident_numbers=False`: 주민번호 마스킹 안 함
- `mask_addresses=False`: 주소 마스킹 안 함

## 🔍 감지 패턴

### 주민번호
- `123456-1234567` 형식
- 이미 일부 마스킹된 경우도 감지

### 주소
- 시/도로 시작하는 주소
- 동/읍/면/리/번지/로/길 포함
- 최소 10자 이상

## ⚠️ 주의사항

1. **PDF 마스킹의 한계**
   - PDF 내부 텍스트와 OCR로 추출한 텍스트가 다를 수 있음
   - 스캔본 PDF의 경우 정확도가 낮을 수 있음
   - 텍스트가 이미지로 삽입된 경우 마스킹이 어려울 수 있음

2. **주소 감지**
   - 주소 패턴이 다양하여 일부 주소는 감지되지 않을 수 있음
   - 정확도를 높이려면 `address_keep_chars` 값을 조정하세요

3. **성능**
   - 대용량 PDF의 경우 처리 시간이 오래 걸릴 수 있음
   - 여러 페이지에 걸친 주소는 각 페이지별로 처리됨

## 🐛 문제 해결

### 마스킹이 안 되는 경우
1. 텍스트가 이미지로 삽입된 경우 → OCR 후 마스킹 필요
2. 폰트가 특수한 경우 → PDF 내부 텍스트 추출 확인
3. 주소 형식이 비표준인 경우 → 패턴 추가 필요

### 마스킹이 너무 많이 되는 경우
- `address_keep_chars` 값을 늘려서 앞부분을 더 많이 유지

## 📝 예시

### 입력 텍스트
```
임대인: 홍길동
주민번호: 123456-1234567
주소: 서울특별시 강남구 테헤란로 123번지
임차인: 김철수
주민번호: 987654-1234567
주소: 경기도 성남시 분당구 정자동 456-789
```

### 마스킹 결과
```
임대인: 홍길동
주민번호: 123456-1******
주소: 서울특별시 강남구 테헤란로 ***
임차인: 김철수
주민번호: 987654-1******
주소: 경기도 성남시 분당구 정자동 ***
```
