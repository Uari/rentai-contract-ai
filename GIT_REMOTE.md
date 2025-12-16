# Git 원격 저장소 변경 가이드

## 현재 원격 저장소 확인

```powershell
# PATH에 Git 추가
$env:PATH += ";C:\Program Files\Git\bin"

# 원격 저장소 목록 확인
git remote -v
```

## 원격 저장소 추가/변경 방법

### 1. 원격 저장소가 없는 경우 (추가)

```powershell
# 원격 저장소 추가
git remote add origin https://github.com/your-username/rentai_contract_ai.git

# 확인
git remote -v
```

### 2. 원격 저장소가 있는 경우 (변경)

#### 방법 A: 기존 원격 저장소 URL 변경
```powershell
# origin의 URL 변경
git remote set-url origin https://github.com/new-username/new-repo.git

# 확인
git remote -v
```

#### 방법 B: 기존 원격 저장소 삭제 후 새로 추가
```powershell
# 기존 원격 저장소 삭제
git remote remove origin

# 새로운 원격 저장소 추가
git remote add origin https://github.com/new-username/new-repo.git

# 확인
git remote -v
```

### 3. 여러 원격 저장소 관리

```powershell
# 원격 저장소 추가 (다른 이름으로)
git remote add upstream https://github.com/original-owner/repo.git

# 원격 저장소 목록 확인
git remote -v

# 특정 원격 저장소 정보 확인
git remote show origin
```

## GitHub 저장소 URL 형식

### HTTPS (권장)
```
https://github.com/username/repository.git
```

### SSH
```
git@github.com:username/repository.git
```

## 원격 저장소에 푸시

```powershell
# 첫 푸시
git push -u origin main

# 이후 푸시
git push origin main
```

## 원격 저장소에서 가져오기

```powershell
# 원격 저장소 정보 가져오기
git fetch origin

# 원격 저장소에서 가져와서 병합
git pull origin main
```

## 문제 해결

### 인증 오류
- **HTTPS**: Personal Access Token 필요
- **SSH**: SSH 키 설정 필요

### 푸시 거부
```powershell
# 원격 저장소 강제 업데이트 (주의: 기존 내용 덮어씀)
git push -f origin main
```

## 예시

### 예시 1: GitHub 저장소 연결
```powershell
# 원격 저장소 추가
git remote add origin https://github.com/your-username/rentai_contract_ai.git

# 확인
git remote -v
# 출력:
# origin  https://github.com/your-username/rentai_contract_ai.git (fetch)
# origin  https://github.com/your-username/rentai_contract_ai.git (push)

# 푸시
git push -u origin main
```

### 예시 2: 원격 저장소 변경
```powershell
# 기존 URL 확인
git remote -v

# URL 변경
git remote set-url origin https://github.com/new-username/new-repo.git

# 확인
git remote -v
```
