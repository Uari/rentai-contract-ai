# Git 사용자 정보 설정 가이드

## 문제
Git 커밋 시 사용자 정보가 설정되지 않아 오류가 발생합니다.

## 해결 방법

### 1. 전역 설정 (모든 Git 저장소에 적용)

```powershell
# 사용자 이름 설정
git config --global user.name "Your Name"

# 이메일 설정 (GitHub 계정 이메일 사용 권장)
git config --global user.email "your.email@example.com"
```

### 2. 현재 저장소만 설정 (이 저장소에만 적용)

```powershell
# 사용자 이름 설정
git config user.name "Your Name"

# 이메일 설정
git config user.email "your.email@example.com"
```

### 3. 설정 확인

```powershell
# 전역 설정 확인
git config --global --list

# 현재 저장소 설정 확인
git config --list
```

## GitHub 사용 시 권장 사항

- **이메일**: GitHub 계정에 등록된 이메일 주소 사용
- GitHub에서 이메일을 비공개로 설정한 경우: `username@users.noreply.github.com` 형식 사용

## 예시

```powershell
# 예시 1: GitHub 계정 이메일 사용
git config --global user.name "홍길동"
git config --global user.email "hong@example.com"

# 예시 2: GitHub 비공개 이메일 사용
git config --global user.name "홍길동"
git config --global user.email "12345678+username@users.noreply.github.com"
```

## 설정 후 커밋

사용자 정보를 설정한 후 다시 커밋을 시도하세요:

```powershell
git commit -m "Initial commit: 임대차 계약서 AI 분석 시스템"
```
