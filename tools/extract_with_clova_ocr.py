"""
Naver Clova OCR을 사용한 텍스트 추출 (최고 정확도)

사용법:
  # 이미지 파일
  python tools/extract_with_clova_ocr.py image.jpg --output result.txt

  # PDF 파일
  python tools/extract_with_clova_ocr.py document.pdf --output result.txt

  # 신뢰도 필터링
  python tools/extract_with_clova_ocr.py image.jpg --min-confidence 0.9 --output result.txt

사전 준비:
  1. Naver Cloud Platform 계정 생성
  2. Clova OCR 서비스 신청
  3. .env 파일에 API 정보 추가:
     NAVER_CLOVA_API_URL=https://...
     NAVER_CLOVA_SECRET_KEY=your_secret_key
"""
import sys
import pathlib
import io
import argparse

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

try:
    from app.services.parser_pdf.naver_clova_ocr import (
        extract_text_auto_clova,
        check_api_credentials
    )
except ImportError as e:
    print(f"[ERROR] 모듈 임포트 실패: {e}")
    print("\n필요한 패키지 설치:")
    print("  pip install requests pdf2image Pillow")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Naver Clova OCR을 사용한 텍스트 추출",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 이미지 파일
  python tools/extract_with_clova_ocr.py image.jpg

  # PDF 파일
  python tools/extract_with_clova_ocr.py document.pdf --output result.txt

  # 신뢰도 필터링 (90% 이상만)
  python tools/extract_with_clova_ocr.py image.jpg --min-confidence 0.9

사전 준비:
  1. Naver Cloud Platform: https://www.ncloud.com
  2. Clova OCR 서비스 신청
  3. .env 파일에 API 정보 추가
        """
    )
    parser.add_argument(
        "file",
        type=str,
        help="추출할 파일 경로 (PDF, JPG, PNG 등)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="결과를 파일로 저장"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="최소 신뢰도 (0.0~1.0, 기본: 0.0 = 필터 안 함)"
    )
    parser.add_argument(
        "--show-confidence",
        action="store_true",
        help="각 텍스트의 신뢰도 표시"
    )
    
    args = parser.parse_args()
    
    # API 인증 정보 확인
    try:
        check_api_credentials()
    except ValueError as e:
        print(f"[ERROR] {e}")
        print("\n설정 방법:")
        print("1. Naver Cloud Platform 접속: https://console.ncloud.com")
        print("2. AI·NAVER API > Clova OCR 선택")
        print("3. 서비스 신청 및 도메인 등록")
        print("4. API Gateway 호출 URL과 Secret Key 확인")
        print("5. .env 파일에 추가:")
        print("   NAVER_CLOVA_API_URL=https://your-api-url")
        print("   NAVER_CLOVA_SECRET_KEY=your_secret_key")
        return 1
    
    # 파일 경로 확인
    file_path = pathlib.Path(args.file)
    if not file_path.is_absolute():
        file_path = ROOT / file_path
    
    if not file_path.exists():
        print(f"[ERROR] 파일을 찾을 수 없습니다: {file_path}")
        return 1
    
    print(f"[INFO] 파일: {file_path.name}")
    print(f"[INFO] 크기: {file_path.stat().st_size / 1024:.2f} KB")
    print("=" * 60)
    
    # 파일 읽기
    try:
        file_bytes = file_path.read_bytes()
    except Exception as e:
        print(f"[ERROR] 파일 읽기 실패: {e}")
        return 1
    
    # OCR 수행
    print("[INFO] Naver Clova OCR 처리 중...")
    print("[INFO] 정확도: 95~99% (한글 특화)")
    try:
        result = extract_text_auto_clova(file_bytes, file_path.name)
    except Exception as e:
        print(f"[ERROR] OCR 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 신뢰도 필터링 (이미지인 경우)
    if result['type'] == 'image' and args.min_confidence > 0:
        filtered_text = []
        for field in result.get('fields', []):
            if field['confidence'] >= args.min_confidence:
                if args.show_confidence:
                    filtered_text.append(f"{field['text']} ({field['confidence']:.2%})")
                else:
                    filtered_text.append(field['text'])
        text = '\n'.join(filtered_text)
        print(f"[INFO] 신뢰도 {args.min_confidence:.0%} 이상 필터링 적용")
    else:
        text = result['text']
    
    # 결과 출력
    print("=" * 60)
    print(f"[결과] 타입: {result['type']}")
    print(f"[결과] 페이지 수: {result['page_count']}")
    print(f"[결과] 텍스트 길이: {len(text)}자")
    print("=" * 60)
    
    # 신뢰도 통계 (이미지인 경우)
    if result['type'] == 'image' and 'fields' in result:
        confidences = [f['confidence'] for f in result['fields']]
        if confidences:
            avg_conf = sum(confidences) / len(confidences)
            min_conf = min(confidences)
            max_conf = max(confidences)
            print(f"[통계] 평균 신뢰도: {avg_conf:.2%}")
            print(f"[통계] 최소 신뢰도: {min_conf:.2%}")
            print(f"[통계] 최대 신뢰도: {max_conf:.2%}")
            print("=" * 60)
    
    # 결과 저장/출력
    if args.output:
        output_path = pathlib.Path(args.output)
        if not output_path.is_absolute():
            output_path = ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding='utf-8')
        print(f"\n[저장 완료] {output_path}")
    else:
        print("\n[추출된 텍스트]")
        print("-" * 60)
        preview = text[:2000]
        print(preview)
        if len(text) > 2000:
            print(f"\n... (총 {len(text)}자 중 2000자만 표시)")
            print(f"\n전체 텍스트를 보려면 --output 옵션 사용")
        print("-" * 60)
    
    print("\n[성공] Naver Clova OCR 완료!")
    print("\n💡 정확도가 매우 높습니다 (95~99%)")
    print("💡 월 1,000건까지 무료입니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())

