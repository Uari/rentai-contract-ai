# GitHub 연동 가이드

이 가이드는 프로젝트를 GitHub에 연동하는 방법을 설명합니다.

## 1. GitHub 저장소 생성

1. [GitHub](https://github.com)에 로그인
2. 우측 상단의 **+** 버튼 클릭 → **New repository** 선택
3. 저장소 정보 입력:
   - **Repository name**: `rentai_contract_ai` (또는 원하는 이름)
   - **Description**: "임대차 계약서 AI 분석 시스템"
   - **Visibility**: Public 또는 Private 선택
   - **Initialize this repository with**: 체크하지 않음 (이미 로컬에 파일이 있으므로)
4. **Create repository** 클릭

## 2. Git 초기화 및 첫 커밋

### Git 설치 확인
```bash
git --version
```

Git이 설치되어 있지 않다면 [Git 공식 사이트](https://git-scm.com/downloads)에서 다운로드하세요.

### 로컬 저장소 초기화
```powershell
# 프로젝트 디렉토리로 이동
cd d:\park\rentai_contract_ai

# Git 저장소 초기화
git init

# 기본 브랜치 이름을 main으로 설정
git branch -M main

# 모든 파일 추가
git add .

# 첫 커밋
git commit -m "Initial commit: 임대차 계약서 AI 분석 시스템"
```

## 3. GitHub 원격 저장소 연결

GitHub에서 생성한 저장소의 URL을 복사한 후:

```powershell
# 원격 저장소 추가 (HTTPS)
git remote add origin https://github.com/your-username/rentai_contract_ai.git

# 또는 SSH (SSH 키가 설정되어 있는 경우)
git remote add origin git@github.com:your-username/rentai_contract_ai.git

# 원격 저장소 확인
git remote -v
```

## 4. 코드 푸시

```powershell
# 원격 저장소에 푸시
git push -u origin main
```

첫 푸시 시 GitHub 인증이 필요할 수 있습니다:
- **HTTPS**: Personal Access Token 사용
- **SSH**: SSH 키 사용

## 5. Personal Access Token 생성 (HTTPS 사용 시)

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. **Generate new token (classic)** 클릭
3. 권한 선택:
   - `repo` (전체 저장소 권한)
4. **Generate token** 클릭
5. 생성된 토큰을 복사 (한 번만 표시됨)
6. Git 푸시 시 비밀번호 대신 이 토큰 사용

## 6. SSH 키 설정 (SSH 사용 시)

### SSH 키 생성
```powershell
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### SSH 키를 GitHub에 추가
1. 생성된 공개 키 복사:
   ```powershell
   cat ~/.ssh/id_ed25519.pub
   ```
2. GitHub → Settings → SSH and GPG keys → New SSH key
3. 키 붙여넣기 및 저장

## 7. 일반적인 Git 워크플로우

### 변경사항 확인
```powershell
git status
```

### 변경사항 스테이징
```powershell
# 특정 파일만
git add <파일명>

# 모든 변경사항
git add .
```

### 커밋
```powershell
git commit -m "커밋 메시지"
```

### 원격 저장소에 푸시
```powershell
git push origin main
```

### 원격 저장소에서 가져오기
```powershell
git pull origin main
```

## 8. 브랜치 전략

### 새 기능 브랜치 생성
```powershell
# 새 브랜치 생성 및 전환
git checkout -b feature/새기능명

# 작업 후 커밋
git add .
git commit -m "새 기능 추가"

# 원격에 푸시
git push -u origin feature/새기능명
```

### Pull Request 생성
1. GitHub 저장소 페이지에서 **Compare & pull request** 클릭
2. PR 제목 및 설명 작성
3. **Create pull request** 클릭

## 9. .gitignore 확인

프로젝트 루트의 `.gitignore` 파일이 다음 항목들을 제외합니다:
- 가상 환경 (`.venv/`, `venv/`)
- Python 캐시 (`__pycache__/`, `*.pyc`)
- 환경 변수 파일 (`.env`)
- 벡터 DB 및 임시 파일
- IDE 설정 파일
- 테스트 파일 및 샘플 파일

## 10. GitHub Actions (CI/CD)

프로젝트에 GitHub Actions 워크플로우가 포함되어 있습니다:
- `.github/workflows/python-app.yml`: Python 애플리케이션 테스트

## 문제 해결

### 인증 오류
- HTTPS: Personal Access Token 확인
- SSH: SSH 키 설정 확인 (`ssh -T git@github.com`)

### 푸시 거부
```powershell
# 원격 저장소 강제 업데이트 (주의: 기존 원격 내용 덮어씀)
git push -f origin main
```

### 원격 저장소 URL 변경
```powershell
git remote set-url origin https://github.com/new-username/new-repo.git
```

## 유용한 명령어

```powershell
# 커밋 히스토리 확인
git log --oneline

# 변경사항 비교
git diff

# 원격 저장소 정보 업데이트
git fetch origin

# 브랜치 목록
git branch -a
```

## 참고 자료

- [Git 공식 문서](https://git-scm.com/doc)
- [GitHub 가이드](https://guides.github.com/)
- [GitHub CLI](https://cli.github.com/) (선택사항)
