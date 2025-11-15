"""
PDF, JPG, PNG 등 모든 파일에서 텍스트 추출 (OCR 지원)

사용법:
  # 이미지 파일 OCR
  python tools/extract_text_with_ocr.py image.jpg

  # PDF 파일 OCR (스캔본)
  python tools/extract_text_with_ocr.py scanned.pdf --use-ocr

  # 일반 PDF (텍스트 레이어 있음)
  python tools/extract_text_with_ocr.py document.pdf

  # 파일로 저장
  python tools/extract_text_with_ocr.py image.png --output result.txt
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

# .env 파일 로드 (프로젝트 루트에서)
try:
    from dotenv import load_dotenv
    env_path = ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()  # 기본 위치에서도 시도
except ImportError:
    pass  # dotenv가 없어도 계속 진행

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.services.parser_pdf.ocr_extractor import (
    extract_text_auto,
    extract_text_from_image_file,
    extract_text_from_pdf_file_with_ocr,
    is_image_file,
    is_pdf_file,
    OCR_AVAILABLE,
    PDF2IMAGE_AVAILABLE
)
from app.services.parser_pdf.enhanced_parser import parse_pdf


def main():
    parser = argparse.ArgumentParser(
        description="PDF, 이미지 파일에서 텍스트 추출 (OCR 지원)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 이미지 파일 OCR
  python tools/extract_text_with_ocr.py image.jpg

  # PDF 파일 OCR (스캔본)
  python tools/extract_text_with_ocr.py scanned.pdf --use-ocr

  # 일반 PDF (텍스트 레이어 있음)
  python tools/extract_text_with_ocr.py document.pdf

  # 파일로 저장
  python tools/extract_text_with_ocr.py image.png --output result.txt
        """
    )
    parser.add_argument(
        "file",
        type=str,
        help="추출할 파일 경로 (PDF, JPG, PNG 등)"
    )
    parser.add_argument(
        "--use-ocr",
        action="store_true",
        help="PDF도 OCR로 처리 (스캔본인 경우)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="결과를 파일로 저장"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["full", "pages"],
        default="full",
        help="출력 형식 (기본: full)"
    )
    
    args = parser.parse_args()
    
    # 파일 경로 확인
    file_path = pathlib.Path(args.file)
    if not file_path.is_absolute():
        file_path = ROOT / file_path
    
    if not file_path.exists():
        print(f"[ERROR] 파일을 찾을 수 없습니다: {file_path}")
        return 1
    
    print(f"[INFO] 파일 읽는 중: {file_path.name}")
    print("=" * 60)
    
    # OCR 사용 가능 여부 확인
    if is_image_file(file_path.name) or args.use_ocr:
        if not OCR_AVAILABLE:
            print("[ERROR] pytesseract가 설치되지 않았습니다.")
            print("설치 방법:")
            print("  1. Tesseract OCR 설치: https://github.com/UB-Mannheim/tesseract/wiki")
            print("  2. pip install pytesseract pillow")
            return 1
        
        if is_pdf_file(file_path.name) and not PDF2IMAGE_AVAILABLE:
            print("[ERROR] pdf2image가 설치되지 않았습니다.")
            print("설치 방법: pip install pdf2image")
            print("\nWindows의 경우 Poppler도 필요합니다:")
            print("  https://github.com/oschwartz10612/poppler-windows/releases")
            return 1
    
    try:
        file_bytes = file_path.read_bytes()
        print(f"[INFO] 파일 크기: {len(file_bytes) / 1024:.2f} KB")
    except Exception as e:
        print(f"[ERROR] 파일 읽기 실패: {e}")
        return 1
    
    # 텍스트 추출
    print("[INFO] 텍스트 추출 중...")
    try:
        if is_image_file(file_path.name):
            # 이미지 파일은 항상 OCR 사용
            print("[INFO] 이미지 파일 감지 → OCR 사용")
            result = extract_text_auto(file_bytes, file_path.name, use_ocr=True)
        elif is_pdf_file(file_path.name):
            if args.use_ocr:
                print("[INFO] PDF 파일 → OCR 사용 (스캔본 처리)")
                result = extract_text_auto(file_bytes, file_path.name, use_ocr=True)
            else:
                print("[INFO] PDF 파일 → 일반 파서 사용")
                try:
                    parsed = parse_pdf(file_bytes)
                    result = {
                        "type": "pdf",
                        "pages": parsed["pages"],
                        "text_full": parsed["text_full"],
                        "page_count": parsed["page_count"]
                    }
                except Exception as e:
                    print(f"[WARN] 일반 파서 실패: {e}")
                    print("[INFO] OCR로 재시도...")
                    result = extract_text_auto(file_bytes, file_path.name, use_ocr=True)
        else:
            print(f"[ERROR] 지원하지 않는 파일 형식: {file_path.suffix}")
            return 1
    except Exception as e:
        print(f"[ERROR] 텍스트 추출 실패: {e}")
        print("\n[팁]")
        print("  - 이미지 파일은 자동으로 OCR을 사용합니다")
        print("  - PDF 스캔본인 경우 --use-ocr 옵션을 사용하세요")
        print("  - Tesseract OCR이 설치되어 있는지 확인하세요")
        return 1
    
    # 결과 출력
    print("=" * 60)
    print(f"[결과] 타입: {result['type']}")
    print(f"[결과] 페이지 수: {result['page_count']}페이지")
    print(f"[결과] 전체 텍스트 길이: {len(result['text_full'])}자")
    print("=" * 60)
    
    # 출력 파일 설정
    output_file = None
    if args.output:
        output_path = pathlib.Path(args.output)
        if not output_path.is_absolute():
            output_path = ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_file = output_path
    
    # 형식에 따라 출력
    if args.format == "pages":
        output_text = "\n\n".join([
            f"=== 페이지 {p['page']} ===\n{p['text']}"
            for p in result["pages"]
        ])
    else:  # full
        output_text = result["text_full"]
    
    if output_file:
        output_file.write_text(output_text, encoding="utf-8")
        print(f"\n[저장 완료] {output_file}")
    else:
        print("\n[추출된 텍스트]")
        print("-" * 60)
        # 처음 1000자만 미리보기
        preview = output_text[:1000]
        print(preview)
        if len(output_text) > 1000:
            print(f"\n... (총 {len(output_text)}자 중 1000자만 표시)")
            print(f"\n전체 텍스트를 보려면 --output 옵션으로 파일로 저장하세요")
        print("-" * 60)
    
    print("\n[성공] 텍스트 추출 완료!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

