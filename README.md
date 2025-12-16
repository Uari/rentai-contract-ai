# 임대차 계약서 AI 분석 시스템

전세/월세 계약서를 자동으로 분석하여 위험 요소를 감지하고 법적 근거를 제공하는 AI 시스템입니다.

## 주요 기능

- 📄 PDF/이미지 계약서 자동 분석
- 🔍 개인정보 마스킹 처리
- ⚠️ 계약서 위험 요소 자동 감지
- 📚 법적 근거 자동 검색 (RAG)
- 📊 분석 결과 리포트 생성
- 🤖 LLM 기반 주소 보정
- 🔄 LangGraph 기반 워크플로우 관리

## 기술 스택

### Backend
- **FastAPI** - RESTful API 서버
- **LangChain** - LLM 애플리케이션 프레임워크
- **LangGraph** - 상태 기반 워크플로우 관리
- **ChromaDB** - 벡터 데이터베이스 (RAG)
- **Google Gemini API** - LLM
- **Naver Clova OCR** - OCR 엔진
- **PyMuPDF** - PDF 처리

### Frontend
- **Streamlit** - 웹 UI

## 설치 방법

### 1. 저장소 클론
```bash
git clone https://github.com/your-username/rentai_contract_ai.git
cd rentai_contract_ai
```

### 2. 가상 환경 생성 및 활성화
```bash
cd rentai/backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정
`rentai/.env` 파일을 생성하고 다음 변수들을 설정하세요:

```env
# Google Gemini API (필수)
GOOGLE_API_KEY=your_gemini_api_key

# Naver Clova OCR (선택사항, 이미지 OCR용)
NAVER_CLOVA_API_URL=your_clova_api_url
NAVER_CLOVA_SECRET_KEY=your_clova_secret_key

# Poppler (PDF 처리용, Windows)
POPPLER_PATH=C:\path\to\poppler\bin
```

### 5. 백엔드 서버 실행
```bash
cd rentai/backend
uvicorn fastapi_app:app --reload --host 0.0.0.0 --port 8000
```

### 6. 프론트엔드 실행
```bash
cd rentai/frontend
streamlit run app.py
```

또는

```bash
cd rentai
streamlit run app_streamlit.py
```

## API 엔드포인트

### 분석
- `POST /analyze/pdf` - 계약서 분석
- `POST /analyze/pdf/langgraph` - LangGraph 기반 분석

### 리포트
- `POST /report/pdf` - PDF 리포트 생성

### 마스킹
- `POST /mask/pdf` - PDF 개인정보 마스킹
- `POST /mask/image` - 이미지 개인정보 마스킹
- `POST /mask/text` - 텍스트 개인정보 마스킹

### 텍스트 추출
- `POST /extract/text` - PDF/이미지에서 텍스트 추출

## 프로젝트 구조

```
rentai_contract_ai/
├── rentai/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── services/
│   │   │   │   ├── extractors/      # 필드 추출
│   │   │   │   ├── llm/             # LLM 서비스
│   │   │   │   ├── parser_pdf/      # PDF 파싱 및 OCR
│   │   │   │   ├── rules/           # 룰 엔진
│   │   │   │   └── workflow/        # LangGraph 워크플로우
│   │   │   └── ...
│   │   ├── fastapi_app.py           # FastAPI 메인 앱
│   │   └── requirements.txt
│   ├── frontend/
│   │   └── app.py                   # Streamlit 프론트엔드
│   └── app_streamlit.py             # Streamlit 데모 UI
├── rules/
│   └── rules_v2.yml                 # 분석 룰셋
└── README.md
```

## 사용 방법

1. 웹 브라우저에서 Streamlit 앱 접속 (기본: http://localhost:8501)
2. PDF 또는 이미지 파일 업로드
3. "분석 실행" 버튼 클릭
4. 분석 결과 확인 및 리포트 다운로드

## 주요 기능 설명

### 1. 계약서 분석
- PDF/이미지 파일에서 텍스트 추출
- OCR 지원 (스캔본 처리)
- 계약서 필드 자동 추출 (임대인, 임대차 목적물, 보증금, 월세 등)

### 2. 위험 요소 감지
- 룰 기반 위험 요소 분석
- 위험도 평가 (Critical, Warning, Safe)
- 이슈별 상세 정보 제공

### 3. 법적 근거 검색 (RAG)
- ChromaDB 벡터 검색
- 관련 법률 조항 자동 검색
- 주의사항 및 대처방안 제공

### 4. 개인정보 마스킹
- 주민번호 뒷자리 마스킹
- 주소 상세주소 마스킹
- 전화번호 마스킹

## 개발 가이드

### 룰 추가 방법
`rules/rules_v2.yml` 파일에 새로운 룰을 추가할 수 있습니다.

### 법률 데이터 추가 방법
`rentai/data/embeddings/lease_law_samples.txt` 파일에 법률 관련 텍스트를 추가하고, 벡터 DB를 재생성하세요.

자세한 내용은 `rentai/docs/` 디렉토리의 문서를 참고하세요.

## 라이선스

[라이선스 정보를 여기에 추가하세요]

## 기여

이슈 및 Pull Request를 환영합니다!
