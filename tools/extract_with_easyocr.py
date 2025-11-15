"""
EasyOCR을 사용한 텍스트 추출 (Tesseract보다 정확)

사용법:
  # 이미지 파일
  python tools/extract_with_easyocr.py image.jpg

  # PDF 파일 (자동으로 이미지 변환 후 OCR)
  python tools/extract_with_easyocr.py scanned.pdf

  # 결과 파일로 저장
  python tools/extract_with_easyocr.py scanned.pdf --output result.txt
"""
import sys
import pathlib
import io
import argparse
import os

# Windows 콘솔 인코딩 문제 해결
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = pathlib.Path(__file__).resolve().parents[1]

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("[ERROR] EasyOCR이 설치되지 않았습니다.")
    print("설치: pip install easyocr")
    sys.exit(1)

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

from PIL import Image

# 전역 reader (재사용)
_reader = None

def get_reader(lang=['ko', 'en'], gpu=False):
    """EasyOCR reader 초기화 (싱글톤)"""
    global _reader
    if _reader is None:
        print(f"[INFO] EasyOCR 모델 로딩 중... (언어: {', '.join(lang)})")
        if gpu:
            print("[INFO] GPU 사용")
        else:
            print("[INFO] CPU 사용 (GPU가 있으면 더 빠릅니다)")
        _reader = easyocr.Reader(lang, gpu=gpu)
        print("[INFO] 모델 로딩 완료")
    return _reader


def extract_from_image(image_path, reader):
    """이미지 파일에서 텍스트 추출"""
    result = reader.readtext(str(image_path), detail=0)
    return '\n'.join(result)


def extract_from_pdf(pdf_path, reader):
    """PDF 파일을 이미지로 변환 후 텍스트 추출"""
    if not PDF2IMAGE_AVAILABLE:
        print("[ERROR] pdf2image가 설치되지 않았습니다.")
        print("설치: pip install pdf2image")
        print("\nWindows의 경우 Poppler도 필요합니다:")
        print("  다운로드: https://github.com/oschwartz10612/poppler-windows/releases")
        return None
    
    # 환경 변수에서 Poppler 경로 가져오기
    poppler_path = os.getenv('POPPLER_PATH')
    
    print(f"[INFO] PDF를 이미지로 변환 중...")
    try:
        # PDF를 이미지로 변환
        kwargs = {'dpi': 300}
        if poppler_path:
            kwargs['poppler_path'] = poppler_path
        
        images = convert_from_path(pdf_path, **kwargs)
        print(f"[INFO] {len(images)}개 페이지 변환 완료")
    except Exception as e:
        print(f"[ERROR] PDF 변환 실패: {e}")
        return None
    
    # 각 페이지에서 텍스트 추출
    all_text = []
    for i, image in enumerate(images, 1):
        print(f"[INFO] 페이지 {i}/{len(images)} OCR 수행 중...")
        
        # PIL Image를 numpy array로 변환하여 EasyOCR에 전달
        import numpy as np
        image_array = np.array(image)
        
        result = reader.readtext(image_array, detail=0)
        page_text = '\n'.join(result)
        
        all_text.append(f"=== 페이지 {i} ===\n{page_text}")
        print(f"[INFO] 페이지 {i} 완료 ({len(page_text)}자)")
    
    return '\n\n'.join(all_text)


def main():
    parser = argparse.ArgumentParser(
        description="EasyOCR을 사용한 텍스트 추출",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 이미지 파일
  python tools/extract_with_easyocr.py image.jpg

  # PDF 파일
  python tools/extract_with_easyocr.py scanned.pdf

  # 결과 저장
  python tools/extract_with_easyocr.py scanned.pdf --output result.txt

  # GPU 사용
  python tools/extract_with_easyocr.py image.jpg --gpu
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
        "--gpu",
        action="store_true",
        help="GPU 사용 (CUDA 필요)"
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="ko,en",
        help="인식 언어 (쉼표로 구분, 기본: ko,en)"
    )
    
    args = parser.parse_args()
    
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
    
    # Reader 초기화
    languages = args.lang.split(',')
    reader = get_reader(lang=languages, gpu=args.gpu)
    
    # 파일 타입에 따라 처리
    ext = file_path.suffix.lower()
    
    try:
        if ext == '.pdf':
            print("[INFO] PDF 파일 감지 → 이미지 변환 후 OCR")
            text = extract_from_pdf(file_path, reader)
        elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
            print("[INFO] 이미지 파일 감지 → 직접 OCR")
            text = extract_from_image(file_path, reader)
        else:
            print(f"[ERROR] 지원하지 않는 파일 형식: {ext}")
            return 1
        
        if text is None:
            return 1
        
    except Exception as e:
        print(f"[ERROR] 텍스트 추출 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 결과 출력/저장
    print("=" * 60)
    print(f"[결과] 전체 텍스트 길이: {len(text)}자")
    print("=" * 60)
    
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
        # 처음 2000자만 미리보기
        preview = text[:2000]
        print(preview)
        if len(text) > 2000:
            print(f"\n... (총 {len(text)}자 중 2000자만 표시)")
            print(f"\n전체 텍스트를 보려면 --output 옵션으로 파일로 저장하세요")
        print("-" * 60)
    
    print("\n[성공] 텍스트 추출 완료!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

