"""
PDF 파일 읽기 테스트 스크립트

사용법:
  python tools/test_pdf_read.py sample.pdf
"""
import sys
import pathlib
import io

# Windows 콘솔 인코딩 문제 해결
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.services.parser_pdf.enhanced_parser import parse_pdf


def main():
    if len(sys.argv) < 2:
        print("사용법: python tools/test_pdf_read.py <PDF파일경로>")
        print("\n예시:")
        print("  python tools/test_pdf_read.py sample.pdf")
        print("  python tools/test_pdf_read.py data/contracts/eval/sample.pdf")
        return 1
    
    pdf_path = pathlib.Path(sys.argv[1])
    if not pdf_path.is_absolute():
        pdf_path = ROOT / pdf_path
    
    if not pdf_path.exists():
        print(f"[ERROR] 파일을 찾을 수 없습니다: {pdf_path}")
        return 1
    
    print(f"[INFO] PDF 파일 읽는 중: {pdf_path.name}")
    print("=" * 60)
    
    try:
        pdf_bytes = pdf_path.read_bytes()
        print(f"[INFO] 파일 크기: {len(pdf_bytes) / 1024:.2f} KB")
    except Exception as e:
        print(f"[ERROR] 파일 읽기 실패: {e}")
        return 1
    
    print("[INFO] 텍스트 추출 중...")
    try:
        parsed = parse_pdf(pdf_bytes)
    except Exception as e:
        print(f"[ERROR] PDF 파싱 실패: {e}")
        print("\n[팁] 스캔된 PDF인 경우 OCR이 필요할 수 있습니다.")
        return 1
    
    print("=" * 60)
    print(f"[결과] 페이지 수: {parsed['page_count']}페이지")
    print(f"[결과] 문장 수: {parsed['sentence_count']}문장")
    print(f"[결과] 전체 텍스트 길이: {len(parsed['text_full'])}자")
    print("=" * 60)
    
    # 텍스트 미리보기
    if parsed['text_full'].strip():
        print("\n[텍스트 미리보기 (처음 500자)]")
        print("-" * 60)
        print(parsed['text_full'][:500])
        if len(parsed['text_full']) > 500:
            print("...")
        print("-" * 60)
        
        # 페이지별 미리보기
        print("\n[페이지별 요약]")
        for page in parsed['pages'][:3]:  # 처음 3페이지만
            text_preview = page['text'][:100].replace('\n', ' ')
            print(f"  페이지 {page['page']}: {text_preview}...")
        
        if len(parsed['pages']) > 3:
            print(f"  ... 외 {len(parsed['pages']) - 3}페이지")
    else:
        print("\n[경고] 텍스트를 추출할 수 없습니다!")
        print("이 PDF는 스캔된 이미지일 수 있습니다.")
        print("OCR 기능이 필요할 수 있습니다.")
        return 1
    
    print("\n[성공] PDF 텍스트 추출 완료!")
    print("\n전체 텍스트를 보려면:")
    print(f"  python tools/extract_pdf_text.py {sys.argv[1]}")
    print("\n파일로 저장하려면:")
    print(f"  python tools/extract_pdf_text.py {sys.argv[1]} --output result.txt")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

