# OCR 텍스트 추출 가이드

PDF, JPG, PNG 등 이미지 파일에서 텍스트를 추출하는 방법을 안내합니다.

## 📋 지원 파일 형식

- **PDF**: `.pdf` (텍스트 레이어 있음 / 스캔본 모두 지원)
- **이미지**: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.tif`

## 🔧 사전 준비

### 1. Tesseract OCR 설치

OCR 기능을 사용하려면 Tesseract OCR이 필요합니다.

#### Windows
1. 다운로드: https://github.com/UB-Mannheim/tesseract/wiki
2. 설치 후 환경 변수 설정 (또는 경로 지정)
   ```bash
   # 환경 변수로 설정하거나
   set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   
   # 또는 .env 파일에 추가
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-kor  # 한국어 지원
```

#### macOS
```bash
brew install tesseract
brew install tesseract-lang  # 언어 지원
```

### 2. Poppler 설치 (PDF OCR용, Windows만)

Windows에서 PDF를 이미지로 변환하려면 Poppler가 필요합니다.

1. 다운로드: https://github.com/oschwartz10612/poppler-windows/releases
2. 압축 해제 후 경로 설정
   ```bash
   # .env 파일에 추가
   POPPLER_PATH=C:\tools\poppler-24.02.0\Library\bin
   ```

### 3. Python 패키지 설치

```bash
cd rentai/backend
pip install -r requirements.txt
```

필요한 패키지:
- `pytesseract` - Tesseract OCR Python 래퍼
- `Pillow` - 이미지 처리
- `pdf2image` - PDF를 이미지로 변환

## 🚀 사용 방법

### 방법 1: 스크립트 사용 (추천)

#### 이미지 파일 OCR
```bash
cd rentai
python tools/extract_text_with_ocr.py image.jpg
```

#### PDF 스캔본 OCR
```bash
python tools/extract_text_with_ocr.py scanned.pdf --use-ocr
```

#### 일반 PDF (텍스트 레이어 있음)
```bash
python tools/extract_text_with_ocr.py document.pdf
```

#### 결과를 파일로 저장
```bash
python tools/extract_text_with_ocr.py image.png --output result.txt
```

#### 페이지별로 출력
```bash
python tools/extract_text_with_ocr.py scanned.pdf --use-ocr --format pages
```

### 방법 2: API 사용

#### 이미지 파일 업로드
```bash
curl -X POST "http://localhost:8000/extract/text" \
  -F "file=@image.jpg"
```

#### PDF 스캔본 OCR
```bash
curl -X POST "http://localhost:8000/extract/text?use_ocr=true" \
  -F "file=@scanned.pdf"
```

#### Python으로 사용
```python
import requests

# 이미지 파일 OCR
with open("image.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/extract/text",
        files={"file": f}
    )
    
result = response.json()
print(result["text"])  # 추출된 텍스트
```

## 📝 예시

### 예시 1: 스캔된 계약서 이미지 OCR

```bash
# JPG 파일 OCR
python tools/extract_text_with_ocr.py contract.jpg --output contract_text.txt
```

### 예시 2: 스캔된 PDF 계약서

```bash
# PDF 스캔본 OCR
python tools/extract_text_with_ocr.py scanned_contract.pdf --use-ocr --output contract_text.txt
```

### 예시 3: 일반 PDF (텍스트 레이어 있음)

```bash
# 일반 PDF는 OCR 없이 빠르게 처리
python tools/extract_text_with_ocr.py document.pdf
```

## ⚙️ 환경 변수 설정

`.env` 파일에 다음을 추가할 수 있습니다:

```env
# Tesseract OCR 경로 (Windows)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Poppler 경로 (Windows, PDF OCR용)
POPPLER_PATH=C:\tools\poppler-24.02.0\Library\bin

# OCR 언어 설정 (기본: kor+eng)
OCR_LANG=kor+eng

# OCR 트리거 길이 (텍스트가 이보다 적으면 OCR 시도)
OCR_TRIGGER_LEN=25
```

## 🔍 OCR 언어 설정

기본적으로 한국어(`kor`)와 영어(`eng`)를 지원합니다.

다른 언어를 사용하려면:
1. 해당 언어의 Tesseract 언어 데이터 설치
2. `OCR_LANG` 환경 변수 설정

예시:
```bash
# 한국어 + 영어 + 일본어
OCR_LANG=kor+eng+jpn

# 영어만
OCR_LANG=eng
```

## ⚠️ 주의사항

1. **OCR 정확도**
   - 이미지 품질이 좋을수록 정확도가 높습니다
   - 해상도가 낮거나 흐릿한 이미지는 정확도가 떨어질 수 있습니다
   - 스캔본은 300 DPI 이상을 권장합니다

2. **처리 속도**
   - OCR은 일반 텍스트 추출보다 느립니다
   - 큰 이미지나 많은 페이지는 시간이 걸릴 수 있습니다

3. **메모리 사용**
   - PDF를 이미지로 변환할 때 메모리를 많이 사용할 수 있습니다
   - 큰 파일은 페이지 단위로 나누어 처리하는 것을 권장합니다

## 🐛 문제 해결

### "TesseractNotFoundError" 오류

**원인**: Tesseract OCR이 설치되지 않았거나 경로를 찾을 수 없음

**해결**:
1. Tesseract OCR 설치 확인
2. 환경 변수 `TESSERACT_CMD` 설정
3. Windows의 경우 전체 경로 지정 필요

### "pdf2image.exceptions.PDFInfoNotInstalledError" 오류

**원인**: Poppler가 설치되지 않음 (Windows)

**해결**:
1. Poppler 다운로드 및 설치
2. 환경 변수 `POPPLER_PATH` 설정

### OCR 결과가 부정확함

**원인**: 이미지 품질 문제

**해결**:
1. 더 높은 해상도로 스캔
2. 이미지 전처리 (밝기 조정, 대비 향상 등)
3. 다른 OCR 엔진 시도 (Google Cloud Vision API 등)

### 메모리 부족 오류

**원인**: 큰 PDF 파일 처리 시 메모리 부족

**해결**:
1. 페이지 단위로 나누어 처리
2. DPI 값 낮추기 (기본 300 → 200)
3. 더 많은 메모리 할당

## 📚 추가 리소스

- [Tesseract OCR 공식 문서](https://tesseract-ocr.github.io/)
- [pytesseract 문서](https://pypi.org/project/pytesseract/)
- [pdf2image 문서](https://github.com/Belval/pdf2image)

## 💡 팁

1. **일반 PDF는 OCR 사용 안 함**: 텍스트 레이어가 있는 PDF는 OCR 없이 빠르게 처리됩니다
2. **이미지는 자동 OCR**: 이미지 파일은 자동으로 OCR을 사용합니다
3. **스캔본은 명시적으로 OCR 사용**: PDF 스캔본은 `--use-ocr` 옵션을 사용하세요
4. **결과 검증**: OCR 결과는 항상 검증하는 것을 권장합니다

