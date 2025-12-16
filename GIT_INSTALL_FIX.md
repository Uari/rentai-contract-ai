# Git 설치 및 PATH 설정 가이드

## 문제 상황
Git이 설치되어 있지만 PowerShell에서 인식되지 않는 경우입니다.

## 해결 방법

### 방법 1: PowerShell 재시작 (가장 간단)
1. 현재 PowerShell 창을 닫습니다
2. 새로운 PowerShell 창을 엽니다
3. Git이 자동으로 인식됩니다

### 방법 2: 현재 세션에서 PATH 추가
PowerShell에서 다음 명령어를 실행하세요:

```powershell
# Git 경로를 현재 세션의 PATH에 추가
$env:PATH += ";C:\Program Files\Git\bin"

# 확인
git --version
```

### 방법 3: 영구적으로 PATH 추가
1. **시스템 환경 변수 편집**:
   - Windows 키 + R → `sysdm.cpl` 입력 → Enter
   - **고급** 탭 → **환경 변수** 클릭
   - **시스템 변수**에서 `Path` 선택 → **편집** 클릭
   - **새로 만들기** 클릭
   - 다음 경로 추가:
     ```
     C:\Program Files\Git\bin
     ```
   - **확인** 클릭하여 모든 창 닫기

2. **PowerShell 재시작**

### 방법 4: Git 전체 경로로 실행
임시로 전체 경로를 사용할 수 있습니다:

```powershell
& "C:\Program Files\Git\bin\git.exe" --version
& "C:\Program Files\Git\bin\git.exe" init
```

### 방법 5: Git 재설치 (최후의 수단)
1. [Git 공식 사이트](https://git-scm.com/downloads)에서 Git 다운로드
2. 설치 시 **"Add Git to PATH"** 옵션 선택
3. 설치 완료 후 PowerShell 재시작

## 빠른 해결 (권장)

현재 PowerShell 세션에서 다음 명령어를 실행하세요:

```powershell
# PATH에 Git 추가
$env:PATH += ";C:\Program Files\Git\bin"

# Git 확인
git --version

# Git 초기화
git init
```

## 확인 방법

다음 명령어로 Git이 제대로 인식되는지 확인하세요:

```powershell
git --version
```

정상적으로 작동하면 다음과 같은 출력이 나옵니다:
```
git version 2.x.x
```
