"""
EasyOCR + 이미지 전처리로 정확도 향상

사용법:
  # 기본 (전처리 자동)
  python tools/extract_with_easyocr_enhanced.py image.jpg --output result.txt

  # 전처리 옵션 조정
  python tools/extract_with_easyocr_enhanced.py image.jpg --preprocess aggressive --output result.txt

전처리 레벨:
  - none: 전처리 없음
  - basic: 기본 전처리 (그레이스케일, 대비 향상)
  - aggressive: 강력한 전처리 (이진화, 노이즈 제거, 해상도 증가)
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

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import numpy as np
import cv2

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
            print("[INFO] CPU 사용")
        _reader = easyocr.Reader(lang, gpu=gpu)
        print("[INFO] 모델 로딩 완료")
    return _reader


def preprocess_image_basic(image):
    """기본 이미지 전처리"""
    print("[PREPROCESS] 기본 전처리 적용...")
    
    # PIL Image로 변환
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    
    # 1. 그레이스케일 변환
    image = image.convert('L')
    
    # 2. 대비 향상
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)
    
    # 3. 샤프닝
    image = image.filter(ImageFilter.SHARPEN)
    
    return image


def preprocess_image_aggressive(image):
    """강력한 이미지 전처리 (정확도 최대화)"""
    print("[PREPROCESS] 강력한 전처리 적용...")
    
    # PIL Image를 numpy array로 변환
    if isinstance(image, Image.Image):
        image = np.array(image)
    
    # 1. 그레이스케일 변환
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image
    
    # 2. 노이즈 제거 (bilateral filter)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 3. 대비 향상 (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # 4. 이진화 (Otsu's method)
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 5. 모폴로지 연산 (작은 노이즈 제거)
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    # 6. 해상도 증가 (2배)
    height, width = cleaned.shape
    upscaled = cv2.resize(cleaned, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
    
    # PIL Image로 변환
    result = Image.fromarray(upscaled)
    
    return result


def extract_from_image(image_path, reader, preprocess='basic'):
    """이미지 파일에서 텍스트 추출"""
    # 이미지 로드
    image = Image.open(str(image_path))
    
    # 전처리 적용
    if preprocess == 'basic':
        image = preprocess_image_basic(image)
    elif preprocess == 'aggressive':
        image = preprocess_image_aggressive(image)
    # 'none'이면 전처리 안 함
    
    # numpy array로 변환
    image_array = np.array(image)
    
    # OCR 수행
    print("[OCR] 텍스트 추출 중...")
    result = reader.readtext(image_array, detail=0, paragraph=True)
    
    return '\n'.join(result)


def extract_from_pdf(pdf_path, reader, preprocess='basic'):
    """PDF 파일을 이미지로 변환 후 텍스트 추출"""
    if not PDF2IMAGE_AVAILABLE:
        print("[ERROR] pdf2image가 설치되지 않았습니다.")
        print("설치: pip install pdf2image")
        return None
    
    # 환경 변수에서 Poppler 경로 가져오기
    poppler_path = os.getenv('POPPLER_PATH')
    
    print(f"[INFO] PDF를 이미지로 변환 중...")
    try:
        # PDF를 이미지로 변환 (DPI 높게)
        kwargs = {'dpi': 400}  # 기본 300 → 400으로 증가
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
        print(f"\n[INFO] === 페이지 {i}/{len(images)} ===")
        
        # 전처리 적용
        if preprocess == 'basic':
            processed_image = preprocess_image_basic(image)
        elif preprocess == 'aggressive':
            processed_image = preprocess_image_aggressive(image)
        else:
            processed_image = image
        
        # numpy array로 변환
        image_array = np.array(processed_image)
        
        # OCR 수행
        print(f"[OCR] 페이지 {i} 텍스트 추출 중...")
        result = reader.readtext(image_array, detail=0, paragraph=True)
        page_text = '\n'.join(result)
        
        all_text.append(f"=== 페이지 {i} ===\n{page_text}")
        print(f"[INFO] 페이지 {i} 완료 ({len(page_text)}자)")
    
    return '\n\n'.join(all_text)


def main():
    parser = argparse.ArgumentParser(
        description="EasyOCR + 이미지 전처리로 정확도 향상",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 전처리
  python tools/extract_with_easyocr_enhanced.py image.jpg

  # 강력한 전처리 (정확도 우선)
  python tools/extract_with_easyocr_enhanced.py image.jpg --preprocess aggressive

  # 전처리 없음
  python tools/extract_with_easyocr_enhanced.py image.jpg --preprocess none
        """
    )
    parser.add_argument(
        "file",
        type=str,
        help="추출할 파일 경로"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="결과를 파일로 저장"
    )
    parser.add_argument(
        "--preprocess",
        type=str,
        choices=['none', 'basic', 'aggressive'],
        default='basic',
        help="전처리 레벨 (기본: basic)"
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="GPU 사용"
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="ko,en",
        help="인식 언어 (기본: ko,en)"
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
    print(f"[INFO] 전처리: {args.preprocess}")
    print("=" * 60)
    
    # Reader 초기화
    languages = args.lang.split(',')
    reader = get_reader(lang=languages, gpu=args.gpu)
    
    # 파일 타입에 따라 처리
    ext = file_path.suffix.lower()
    
    try:
        if ext == '.pdf':
            print("[INFO] PDF 파일 → 이미지 변환 + 전처리 + OCR")
            text = extract_from_pdf(file_path, reader, args.preprocess)
        elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
            print("[INFO] 이미지 파일 → 전처리 + OCR")
            text = extract_from_image(file_path, reader, args.preprocess)
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
    print("\n" + "=" * 60)
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
        preview = text[:2000]
        print(preview)
        if len(text) > 2000:
            print(f"\n... (총 {len(text)}자 중 2000자만 표시)")
            print(f"\n전체 텍스트를 보려면 --output 옵션 사용")
        print("-" * 60)
    
    print("\n[성공] 텍스트 추출 완료!")
    print(f"\n💡 팁: 정확도가 낮다면 --preprocess aggressive 옵션을 사용해보세요")
    return 0


if __name__ == "__main__":
    sys.exit(main())

