# 환경 변수 설정 가이드

Windows에서 환경 변수를 설정하는 방법을 안내합니다.

## 🎯 방법 1: .env 파일 사용 (추천)

프로젝트 루트에 `.env` 파일을 만들어서 설정하는 방법입니다. 가장 간단하고 프로젝트별로 관리할 수 있습니다.

### 1단계: .env 파일 생성

프로젝트 루트(`rentai/`)에 `.env` 파일을 만듭니다:

```bash
cd c:\python\rentai_prototype\rentai
copy .env.example .env
```

또는 직접 만들기:

```bash
# PowerShell에서
New-Item -Path .env -ItemType File
```

### 2단계: .env 파일 편집

`.env` 파일을 열고 다음 내용을 추가/수정합니다:

```env
# Tesseract OCR 경로 (Windows)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Poppler 경로 (Windows, PDF OCR용)
POPPLER_PATH=C:\tools\poppler-24.02.0\Library\bin

# OCR 언어 설정
OCR_LANG=kor+eng

# Gemini API Key (필요한 경우)
GEMINI_API_KEY=your_api_key_here
```

### 3단계: 실제 경로 확인

#### Tesseract OCR 경로 확인

1. Tesseract가 설치되어 있는지 확인:
   ```powershell
   # PowerShell에서
   Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe"
   ```

2. 다른 위치에 설치되어 있다면 해당 경로 사용:
   ```env
   TESSERACT_CMD=C:\Users\YourName\AppData\Local\Programs\Tesseract-OCR\tesseract.exe
   ```

#### Poppler 경로 확인

1. Poppler를 다운로드하고 압축 해제:
   - 다운로드: https://github.com/oschwartz10612/poppler-windows/releases
   - 예: `C:\tools\poppler-24.02.0\Library\bin`

2. `bin` 폴더 안에 `pdftoppm.exe` 파일이 있는지 확인:
   ```powershell
   Test-Path "C:\tools\poppler-24.02.0\Library\bin\pdftoppm.exe"
   ```

### 4단계: 테스트

```bash
python tools/extract_text_with_ocr.py scanned.pdf --use-ocr
```

---

## 🎯 방법 2: 시스템 환경 변수 설정 (영구적)

Windows 시스템 환경 변수로 설정하면 모든 프로그램에서 사용할 수 있습니다.

### GUI로 설정하기

1. **시스템 속성 열기**
   - `Win + R` → `sysdm.cpl` 입력 → Enter
   - 또는: 제어판 → 시스템 → 고급 시스템 설정

2. **환경 변수 버튼 클릭**

3. **사용자 변수 또는 시스템 변수에 추가**
   - **새로 만들기** 클릭
   - 변수 이름: `TESSERACT_CMD`
   - 변수 값: `C:\Program Files\Tesseract-OCR\tesseract.exe`
   - 확인 클릭

4. **Poppler도 동일하게 추가**
   - 변수 이름: `POPPLER_PATH`
   - 변수 값: `C:\tools\poppler-24.02.0\Library\bin`

5. **새 터미널 열기** (변경사항 적용)

### PowerShell로 설정하기

```powershell
# 사용자 환경 변수 설정
[System.Environment]::SetEnvironmentVariable("TESSERACT_CMD", "C:\Program Files\Tesseract-OCR\tesseract.exe", "User")
[System.Environment]::SetEnvironmentVariable("POPPLER_PATH", "C:\tools\poppler-24.02.0\Library\bin", "User")

# 새 터미널에서 확인
$env:TESSERACT_CMD
$env:POPPLER_PATH
```

---

## 🎯 방법 3: 명령 프롬프트에서 임시 설정

현재 세션에서만 유효한 임시 설정입니다.

### PowerShell

```powershell
# 현재 세션에만 적용
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
$env:POPPLER_PATH = "C:\tools\poppler-24.02.0\Library\bin"

# 확인
echo $env:TESSERACT_CMD
echo $env:POPPLER_PATH
```

### CMD

```cmd
set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
set POPPLER_PATH=C:\tools\poppler-24.02.0\Library\bin

# 확인
echo %TESSERACT_CMD%
echo %POPPLER_PATH%
```

---

## 🔍 환경 변수 확인 방법

### Python에서 확인

```python
import os
print("TESSERACT_CMD:", os.getenv("TESSERACT_CMD"))
print("POPPLER_PATH:", os.getenv("POPPLER_PATH"))
```

### PowerShell에서 확인

```powershell
# .env 파일이 로드되었는지 확인
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('TESSERACT_CMD:', os.getenv('TESSERACT_CMD'))"
```

---

## 📝 .env 파일 위치

`.env` 파일은 프로젝트 루트에 있어야 합니다:

```
rentai/
├── .env              ← 여기에!
├── backend/
├── tools/
└── ...
```

프로젝트 코드에서 `load_dotenv()`를 호출하면 자동으로 `.env` 파일을 찾아서 로드합니다.

---

## ⚠️ 주의사항

1. **.env 파일은 Git에 올리지 마세요**
   - `.gitignore`에 추가되어 있는지 확인
   - 민감한 정보(API 키 등)가 포함될 수 있습니다

2. **경로에 공백이 있으면 따옴표 사용**
   ```env
   # 잘못된 예
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   
   # 올바른 예 (Windows에서는 보통 따옴표 불필요)
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

3. **경로 구분자는 백슬래시(`\`) 사용**
   - Windows: `C:\Program Files\...`
   - Linux/Mac: `/usr/bin/...`

4. **변경 후 재시작**
   - 환경 변수 변경 후에는 터미널/IDE를 재시작해야 합니다

---

## 🐛 문제 해결

### "TesseractNotFoundError" 오류

**원인**: Tesseract 경로를 찾을 수 없음

**해결**:
1. Tesseract가 설치되어 있는지 확인
2. `.env` 파일에 올바른 경로 설정
3. 경로에 `tesseract.exe` 파일이 있는지 확인

### "Unable to get page count. Is poppler installed and in PATH?" 오류

**원인**: Poppler 경로를 찾을 수 없음

**해결**:
1. Poppler 다운로드 및 압축 해제
2. `.env` 파일에 `POPPLER_PATH` 설정
3. `bin` 폴더 경로가 올바른지 확인

### 환경 변수가 적용되지 않음

**해결**:
1. 터미널/IDE 재시작
2. `.env` 파일이 프로젝트 루트에 있는지 확인
3. 파일명이 정확히 `.env`인지 확인 (`.env.txt` 아님)

---

## 💡 추천 방법

**프로젝트별 설정**: `.env` 파일 사용 (방법 1)
- 프로젝트별로 다른 설정 가능
- Git에 올리지 않아 안전
- 팀원마다 다른 경로 설정 가능

**전역 설정**: 시스템 환경 변수 (방법 2)
- 모든 프로젝트에서 동일한 설정 사용
- 한 번만 설정하면 됨

