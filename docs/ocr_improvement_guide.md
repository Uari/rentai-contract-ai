# OCR 한글 인식 정확도 개선 가이드

Tesseract OCR의 한글 인식이 정확하지 않을 때 개선 방법을 안내합니다.

## 🔍 문제 확인

OCR 결과가 다음과 같이 나오는 경우:
```
© eS Hm tA FA
mela el! Awe oek BA) RAO Bo de HOuWeD
```

이는 한글 인식이 제대로 되지 않은 것입니다.

---

## 🛠️ 해결 방법

### 방법 1: 한글 언어 데이터 확인 및 재설치

#### 1단계: 현재 설치된 언어 확인
```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
```

출력 예시:
```
List of available languages in "C:\Program Files\Tesseract-OCR\tessdata/" (3):
eng
kor
osd
```

`kor`(한국어)가 있어야 합니다.

#### 2단계: 한글 데이터가 없다면 다운로드

1. 한글 학습 데이터 다운로드:
   - https://github.com/tesseract-ocr/tessdata_best
   - `kor.traineddata` 파일 다운로드

2. 설치 위치에 복사:
   ```powershell
   # 다운로드한 파일을 Tesseract 폴더로 복사
   Copy-Item kor.traineddata "C:\Program Files\Tesseract-OCR\tessdata\"
   ```

---

### 방법 2: 이미지 전처리로 인식률 향상

이미지 품질을 개선하면 OCR 정확도가 크게 향상됩니다.

#### Python 스크립트로 전처리

```python
from PIL import Image, ImageEnhance, ImageFilter
import io

def preprocess_image(image_bytes):
    """이미지 전처리로 OCR 정확도 향상"""
    image = Image.open(io.BytesIO(image_bytes))
    
    # 1. 그레이스케일 변환
    image = image.convert('L')
    
    # 2. 대비 향상
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    
    # 3. 샤프닝
    image = image.filter(ImageFilter.SHARPEN)
    
    # 4. 이진화 (흑백 변환)
    threshold = 128
    image = image.point(lambda p: p > threshold and 255)
    
    # 5. 해상도 증가 (2배)
    width, height = image.size
    image = image.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
    
    return image
```

---

### 방법 3: DPI 설정 높이기

OCR 시 DPI를 높이면 인식률이 향상됩니다.

```bash
# 기본 (300 DPI)
python tools/extract_text_with_ocr.py scanned.pdf --use-ocr

# 개선안: 스크립트 수정 필요
```

.env 파일에 추가:
```env
OCR_DPI=600  # 기본 300 → 600으로 증가
```

---

### 방법 4: 더 나은 OCR 서비스 사용 (추천)

Tesseract보다 정확한 상용 OCR API를 사용합니다.

#### Google Cloud Vision API
- 정확도: ⭐⭐⭐⭐⭐
- 가격: 월 1,000건 무료
- 설정: https://cloud.google.com/vision/docs/ocr

#### Naver Clova OCR
- 정확도: ⭐⭐⭐⭐⭐ (한글 특화)
- 가격: 월 1,000건 무료
- 설정: https://www.ncloud.com/product/aiService/ocr

#### EasyOCR (오픈소스, GPU 필요)
- 정확도: ⭐⭐⭐⭐
- 설치: `pip install easyocr`
- 장점: 무료, 다국어 지원

---

## 💡 임시 해결: EasyOCR 사용

Tesseract보다 정확한 EasyOCR을 빠르게 사용할 수 있습니다.

### 설치
```bash
pip install easyocr
```

### 사용 예시
```python
import easyocr

# 한국어 + 영어 인식기 초기화 (처음엔 시간 소요)
reader = easyocr.Reader(['ko', 'en'])

# 이미지에서 텍스트 추출
result = reader.readtext('scanned.pdf', detail=0)
text = '\n'.join(result)
print(text)
```

---

## 🔧 프로젝트에 EasyOCR 통합

`backend/app/services/parser_pdf/easyocr_extractor.py` 생성:

```python
"""EasyOCR을 사용한 텍스트 추출 (Tesseract보다 정확)"""
import easyocr
from typing import List, Dict
from PIL import Image
import io

# 전역 reader (재사용)
_reader = None

def get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['ko', 'en'], gpu=False)
    return _reader

def extract_text_from_image_easyocr(image_bytes: bytes) -> str:
    """EasyOCR로 이미지에서 텍스트 추출"""
    reader = get_reader()
    
    # PIL Image로 변환
    image = Image.open(io.BytesIO(image_bytes))
    
    # OCR 수행
    result = reader.readtext(image, detail=0)
    
    # 텍스트 결합
    text = '\n'.join(result)
    return text
```

---

## 📊 OCR 엔진 비교

| OCR 엔진 | 정확도 | 속도 | 가격 | 한글 지원 |
|---------|--------|------|------|----------|
| **Tesseract** | ⭐⭐⭐ | 빠름 | 무료 | 보통 |
| **EasyOCR** | ⭐⭐⭐⭐ | 느림 | 무료 | 좋음 |
| **Google Vision** | ⭐⭐⭐⭐⭐ | 빠름 | 유료 | 매우 좋음 |
| **Naver Clova** | ⭐⭐⭐⭐⭐ | 빠름 | 유료 | 매우 좋음 |

---

## ⚡ 빠른 해결책

### 즉시 사용 가능한 방법

1. **이미지 품질 확인**
   - 스캔 해상도: 최소 300 DPI
   - 파일 형식: PNG > JPEG
   - 선명도: 흐릿하지 않게

2. **한글 데이터 재설치**
   ```powershell
   # tessdata_best에서 더 정확한 데이터 다운로드
   # https://github.com/tesseract-ocr/tessdata_best/raw/main/kor.traineddata
   ```

3. **EasyOCR 사용** (추천)
   ```bash
   pip install easyocr
   python -c "import easyocr; reader = easyocr.Reader(['ko']); print(reader.readtext('scanned.pdf'))"
   ```

---

## 🎯 최종 추천

**단기**: EasyOCR 사용 (정확도 우선)
**장기**: Naver Clova OCR API 사용 (상용 서비스)

현재 Tesseract는 한글 인식률이 낮아 실무 사용에는 한계가 있습니다.

