"""
PDF 파일에서 텍스트를 추출하여 조회하는 스크립트

사용법:
  # 전체 텍스트 출력
  python tools/extract_pdf_text.py sample.pdf

  # 페이지별로 출력
  python tools/extract_pdf_text.py sample.pdf --format pages

  # 문장별로 출력
  python tools/extract_pdf_text.py sample.pdf --format sentences

  # 파일로 저장
  python tools/extract_pdf_text.py sample.pdf --output extracted_text.txt
"""
import argparse
import pathlib
import sys
from typing import Dict, Any

# 프로젝트 경로 설정
ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.services.parser_pdf.enhanced_parser import parse_pdf


def print_full_text(parsed: Dict[str, Any], output_file: pathlib.Path = None):
    """전체 텍스트 출력"""
    text = parsed["text_full"]
    
    if output_file:
        output_file.write_text(text, encoding="utf-8")
        print(f"[저장 완료] {output_file}")
    else:
        print("=" * 60)
        print("전체 텍스트")
        print("=" * 60)
        print(text)
        print("=" * 60)
        print(f"총 {len(text)}자, {parsed['page_count']}페이지, {parsed['sentence_count']}문장")


def print_pages(parsed: Dict[str, Any], output_file: pathlib.Path = None):
    """페이지별 텍스트 출력"""
    pages = parsed["pages"]
    
    if output_file:
        lines = []
        for p in pages:
            lines.append(f"\n{'='*60}")
            lines.append(f"페이지 {p['page']}")
            lines.append(f"{'='*60}\n")
            lines.append(p["text"])
            lines.append("")
        output_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"[저장 완료] {output_file}")
    else:
        for p in pages:
            print(f"\n{'='*60}")
            print(f"페이지 {p['page']}")
            print(f"{'='*60}")
            print(p["text"])


def print_sentences(parsed: Dict[str, Any], output_file: pathlib.Path = None):
    """문장별 텍스트 출력"""
    sentences = parsed["sentences"]
    
    if output_file:
        lines = []
        for s in sentences:
            lines.append(f"[{s['id']}] (페이지 {s['page']}) {s['text']}")
        output_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"[저장 완료] {output_file}")
    else:
        for s in sentences:
            print(f"[{s['id']}] (페이지 {s['page']}) {s['text']}")


def main():
    parser = argparse.ArgumentParser(
        description="PDF 파일에서 텍스트 추출",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 전체 텍스트 출력
  python tools/extract_pdf_text.py sample.pdf

  # 페이지별로 출력
  python tools/extract_pdf_text.py sample.pdf --format pages

  # 문장별로 출력
  python tools/extract_pdf_text.py sample.pdf --format sentences

  # 파일로 저장
  python tools/extract_pdf_text.py sample.pdf --output result.txt
        """
    )
    parser.add_argument(
        "pdf_file",
        type=str,
        help="PDF 파일 경로"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["full", "pages", "sentences"],
        default="full",
        help="출력 형식 (기본: full)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="결과를 파일로 저장 (지정하지 않으면 화면에 출력)"
    )
    
    args = parser.parse_args()
    
    # PDF 파일 경로 확인
    pdf_path = pathlib.Path(args.pdf_file)
    if not pdf_path.is_absolute():
        pdf_path = ROOT / pdf_path
    
    if not pdf_path.exists():
        print(f"[ERROR] 파일을 찾을 수 없습니다: {pdf_path}")
        return 1
    
    # PDF 읽기
    print(f"[INFO] PDF 파일 읽는 중: {pdf_path.name}")
    try:
        pdf_bytes = pdf_path.read_bytes()
    except Exception as e:
        print(f"[ERROR] 파일 읽기 실패: {e}")
        return 1
    
    # 텍스트 추출
    print("[INFO] 텍스트 추출 중...")
    try:
        parsed = parse_pdf(pdf_bytes)
    except Exception as e:
        print(f"[ERROR] PDF 파싱 실패: {e}")
        return 1
    
    print(f"[INFO] 추출 완료: {parsed['page_count']}페이지, {parsed['sentence_count']}문장")
    
    # 출력 파일 경로 설정
    output_file = None
    if args.output:
        output_path = pathlib.Path(args.output)
        if not output_path.is_absolute():
            output_path = ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_file = output_path
    
    # 형식에 따라 출력
    if args.format == "pages":
        print_pages(parsed, output_file)
    elif args.format == "sentences":
        print_sentences(parsed, output_file)
    else:  # full
        print_full_text(parsed, output_file)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

