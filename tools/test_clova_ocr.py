"""
Naver Clova OCR 빠른 테스트 스크립트

사용법:
  python tools/test_clova_ocr.py
"""
import sys
import pathlib
import io

# Windows 콘솔 인코딩 문제 해결
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

# 경로 추가
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

import os

def main():
    print("=" * 60)
    print("🧪 Naver Clova OCR 테스트")
    print("=" * 60)
    
    # API 키 확인
    api_url = os.getenv("NAVER_CLOVA_API_URL")
    secret_key = os.getenv("NAVER_CLOVA_SECRET_KEY")
    
    print("\n[1] 환경 변수 확인")
    print(f"  NAVER_CLOVA_API_URL: {'✅ 설정됨' if api_url else '❌ 없음'}")
    print(f"  NAVER_CLOVA_SECRET_KEY: {'✅ 설정됨' if secret_key else '❌ 없음'}")
    
    if not api_url or not secret_key:
        print("\n❌ API 키가 설정되지 않았습니다!")
        print("\n📝 설정 방법:")
        print("1. Naver Cloud Platform 접속: https://console.ncloud.com")
        print("2. AI·NAVER API > Clova OCR 선택")
        print("3. 서비스 신청 및 도메인 등록 (localhost)")
        print("4. API Gateway URL과 Secret Key 확인")
        print("5. .env 파일에 다음 추가:")
        print("   NAVER_CLOVA_API_URL=https://your-api-url")
        print("   NAVER_CLOVA_SECRET_KEY=your_secret_key")
        print("\n자세한 가이드: docs/naver_clova_ocr_setup.md")
        return 1
    
    # 모듈 임포트
    try:
        from app.services.parser_pdf.naver_clova_ocr import (
            check_api_credentials,
            extract_text_auto_clova
        )
        print("\n[2] 모듈 임포트: ✅ 성공")
    except ImportError as e:
        print(f"\n[2] 모듈 임포트: ❌ 실패 - {e}")
        print("\n필요한 패키지 설치:")
        print("  pip install requests pdf2image Pillow")
        return 1
    
    # API 인증 확인
    try:
        check_api_credentials()
        print("[3] API 인증: ✅ 정상")
    except Exception as e:
        print(f"[3] API 인증: ❌ 실패 - {e}")
        return 1
    
    # 테스트 파일 확인
    print("\n[4] 테스트 파일 검색")
    test_files = []
    for ext in ['.jpg', '.jpeg', '.png', '.pdf']:
        test_files.extend(list(ROOT.glob(f"*{ext}")))
    
    if not test_files:
        print("  ❌ 테스트할 파일이 없습니다")
        print("\n테스트 방법:")
        print(f"  1. 이미지 또는 PDF 파일을 {ROOT}에 복사")
        print("  2. 다시 실행: python tools/test_clova_ocr.py")
        print("\n또는 직접 사용:")
        print("  python tools/extract_with_clova_ocr.py your_file.jpg")
        return 1
    
    print(f"  ✅ {len(test_files)}개 파일 발견")
    for f in test_files[:5]:
        print(f"    - {f.name}")
    
    # 첫 번째 파일로 테스트
    test_file = test_files[0]
    print(f"\n[5] 테스트 실행: {test_file.name}")
    
    try:
        file_bytes = test_file.read_bytes()
        print(f"  파일 크기: {len(file_bytes) / 1024:.2f} KB")
        
        print("  API 호출 중...")
        result = extract_text_auto_clova(file_bytes, test_file.name)
        
        print(f"  ✅ 성공!")
        print(f"  - 타입: {result['type']}")
        print(f"  - 페이지: {result['page_count']}")
        print(f"  - 텍스트 길이: {len(result['text'])}자")
        
        # 신뢰도 정보 (이미지인 경우)
        if result['type'] == 'image' and 'fields' in result:
            confidences = [f['confidence'] for f in result['fields']]
            if confidences:
                avg_conf = sum(confidences) / len(confidences)
                print(f"  - 평균 신뢰도: {avg_conf:.2%}")
        
        # 미리보기
        print("\n[6] 텍스트 미리보기 (처음 500자)")
        print("-" * 60)
        preview = result['text'][:500]
        print(preview)
        if len(result['text']) > 500:
            print(f"\n... (총 {len(result['text'])}자)")
        print("-" * 60)
        
        print("\n✅ Naver Clova OCR이 정상적으로 작동합니다!")
        print("\n💡 사용 방법:")
        print(f"  python tools/extract_with_clova_ocr.py {test_file.name} --output result.txt")
        
    except Exception as e:
        print(f"  ❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

