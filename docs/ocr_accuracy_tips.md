# OCR 정확도 개선 가이드

EasyOCR 또는 Tesseract의 한글 인식 정확도를 높이는 방법을 안내합니다.

## 🎯 정확도 향상 방법 (효과 순)

### 1. 이미지 전처리 ⭐⭐⭐⭐⭐ (가장 효과적)

이미지 품질을 개선하면 OCR 정확도가 크게 향상됩니다.

#### 적용 방법

```powershell
# 기본 전처리
python tools/extract_with_easyocr_enhanced.py image.jpg --output result.txt

# 강력한 전처리 (정확도 최대화)
python tools/extract_with_easyocr_enhanced.py image.jpg --preprocess aggressive --output result.txt
```

#### 전처리 기법

| 기법 | 설명 | 효과 |
|-----|------|------|
| **그레이스케일 변환** | 색상 제거, 텍스트에 집중 | ⭐⭐⭐ |
| **대비 향상 (CLAHE)** | 텍스트와 배경 구분 명확 | ⭐⭐⭐⭐ |
| **노이즈 제거** | bilateral filter로 잡음 제거 | ⭐⭐⭐⭐ |
| **이진화 (Otsu)** | 흑백으로 명확하게 | ⭐⭐⭐⭐⭐ |
| **해상도 증가** | 2배 업스케일링 | ⭐⭐⭐⭐ |
| **모폴로지 연산** | 작은 노이즈 제거 | ⭐⭐⭐ |

---

### 2. 원본 이미지 품질 개선 ⭐⭐⭐⭐⭐

#### 스캔/사진 촬영 시 주의사항

**해상도**
- 최소 300 DPI 이상
- 권장: 400~600 DPI
- PDF 변환 시 DPI 설정 높이기

**조명**
- 밝고 균일한 조명
- 그림자 없이
- 반사 방지

**각도**
- 정면에서 촬영
- 기울어지지 않게
- 왜곡 없이

**선명도**
- 초점 정확히
- 흐릿하지 않게
- 손떨림 방지

---

### 3. PDF 변환 시 DPI 높이기 ⭐⭐⭐⭐

```python
# DPI를 400으로 증가 (기본 300)
images = convert_from_path('file.pdf', dpi=400)
```

`.env` 파일 설정:
```env
OCR_DPI=400  # 또는 600
```

---

### 4. EasyOCR 파라미터 조정 ⭐⭐⭐

#### paragraph 옵션
```python
# 문단 단위로 인식 (더 정확)
result = reader.readtext(image, paragraph=True)
```

#### 신뢰도 필터링
```python
# detail=1로 신뢰도 확인
result = reader.readtext(image, detail=1)
for (bbox, text, confidence) in result:
    if confidence > 0.5:  # 신뢰도 50% 이상만
        print(text)
```

---

### 5. 더 나은 OCR 엔진 사용 ⭐⭐⭐⭐⭐

| OCR 엔진 | 한글 정확도 | 속도 | 비용 |
|---------|-----------|------|------|
| Tesseract | ⭐⭐ | 빠름 | 무료 |
| EasyOCR | ⭐⭐⭐⭐ | 보통 | 무료 |
| **Naver Clova OCR** | ⭐⭐⭐⭐⭐ | 빠름 | 월 1000건 무료 |
| Google Cloud Vision | ⭐⭐⭐⭐⭐ | 빠름 | 월 1000건 무료 |
| Azure Computer Vision | ⭐⭐⭐⭐⭐ | 빠름 | 월 5000건 무료 |

---

## 📊 실전 비교

### Before (전처리 없음)
```
© eS Hm tA FA
mela el! Awe oek BA) RAO
```
정확도: 약 30%

### After (강력한 전처리)
```
부동산 임대차 계약서
임대인과 임차인은 다음과 같이 계약한다.
```
정확도: 약 85~95%

---

## 🛠️ 실전 사용법

### 단계별 개선 과정

#### 1단계: 기본 EasyOCR
```bash
python tools/extract_with_easyocr.py image.jpg --output result1.txt
```

#### 2단계: 기본 전처리 추가
```bash
python tools/extract_with_easyocr_enhanced.py image.jpg --output result2.txt
```

#### 3단계: 강력한 전처리
```bash
python tools/extract_with_easyocr_enhanced.py image.jpg --preprocess aggressive --output result3.txt
```

#### 4단계: 원본 이미지 개선 후 재시도
- 스캔 DPI 높이기
- 조명 개선
- 다시 스캔

---

## 💡 상황별 추천

### 경우 1: 선명한 인쇄물
- 전처리: `basic` 또는 `none`
- DPI: 300
- OCR: EasyOCR 기본 설정

### 경우 2: 오래된 문서
- 전처리: `aggressive` ✅
- DPI: 400~600
- 노이즈 제거 중요

### 경우 3: 손글씨
- OCR 엔진: Google Cloud Vision 또는 Naver Clova
- 전처리: `aggressive`
- EasyOCR은 손글씨 인식률 낮음

### 경우 4: 저화질 스캔본
- 전처리: `aggressive` ✅
- 원본 재스캔 권장
- DPI 최대한 높이기

### 경우 5: 사진 촬영본
- 전처리: `aggressive` ✅
- 기울기 보정 추가 권장
- 그림자/반사 주의

---

## 🔧 고급 전처리 기법

### 기울기 보정 (Deskewing)

```python
import cv2
import numpy as np

def deskew(image):
    """기울어진 이미지 보정"""
    # 이진화
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # 기울기 계산
    coords = np.column_stack(np.where(binary > 0))
    angle = cv2.minAreaRect(coords)[-1]
    
    # 보정
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    # 회전
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated
```

### 그림자 제거

```python
def remove_shadow(image):
    """그림자 제거"""
    rgb_planes = cv2.split(image)
    result_planes = []
    
    for plane in rgb_planes:
        dilated = cv2.dilate(plane, np.ones((7, 7), np.uint8))
        bg = cv2.medianBlur(dilated, 21)
        diff = 255 - cv2.absdiff(plane, bg)
        result_planes.append(diff)
    
    return cv2.merge(result_planes)
```

---

## 📈 정확도 측정

### Before/After 비교

```python
# 정확도 계산 (참조 텍스트가 있을 때)
def calculate_accuracy(ocr_text, reference_text):
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, ocr_text, reference_text).ratio()
    return similarity * 100

# 사용 예
ocr_result = "부동산 입대차 계약서"  # OCR 결과
correct_text = "부동산 임대차 계약서"  # 실제 텍스트
accuracy = calculate_accuracy(ocr_result, correct_text)
print(f"정확도: {accuracy:.1f}%")
```

---

## 🎯 최종 권장 사항

### 일반 문서 (인쇄물)
1. EasyOCR + 기본 전처리
2. DPI 300~400
3. 정확도 목표: 90% 이상

### 저화질/오래된 문서
1. EasyOCR + 강력한 전처리 (`aggressive`)
2. DPI 400~600
3. 원본 개선 우선

### 최고 정확도 필요 시
1. Naver Clova OCR API (상용)
2. 원본 이미지 최적화
3. 전처리 + 후처리 결합

---

## 💰 비용 대비 효과

| 방법 | 비용 | 정확도 향상 | 추천도 |
|-----|------|-----------|--------|
| **이미지 전처리** | 무료 | +30~50% | ⭐⭐⭐⭐⭐ |
| 원본 재스캔 | 시간 | +20~40% | ⭐⭐⭐⭐ |
| EasyOCR | 무료 | 기준 | ⭐⭐⭐⭐ |
| Naver Clova OCR | 1000건 무료 | +10~20% | ⭐⭐⭐⭐⭐ |
| Google Cloud Vision | 1000건 무료 | +10~20% | ⭐⭐⭐⭐⭐ |

**결론**: 이미지 전처리가 가장 비용 효율적!

