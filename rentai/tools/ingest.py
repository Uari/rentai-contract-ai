"""
법령 데이터를 Vector DB(ChromaDB)에 추가하는 스크립트

사용법:
  # 모든 파일 추가
  python tools/ingest.py

  # 특정 파일만 추가
  python tools/ingest.py --file data/embeddings/주택임대차보호법.txt

  # 기존 데이터 삭제 후 재추가
  python tools/ingest.py --clear

  # 청킹 크기 조정
  python tools/ingest.py --chunk-size 1000 --chunk-overlap 200
"""
import argparse
import pathlib
import glob
import shutil
from typing import List, Dict, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

ROOT = pathlib.Path(__file__).resolve().parents[1]   # .../rentai
DATA_DIR = ROOT / "data" / "embeddings"
STORE_DIR = ROOT / "vectorstore" / "chroma"
COLLECTION = "lease-law"

# 임베딩 모델 (retrieval.py와 동일하게 유지)
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def clear_vectorstore():
    """기존 벡터스토어 삭제"""
    if STORE_DIR.exists():
        print(f"[CLEAR] 기존 벡터스토어 삭제: {STORE_DIR}")
        shutil.rmtree(STORE_DIR)
        STORE_DIR.mkdir(parents=True, exist_ok=True)
        print("[CLEAR] 완료")
    else:
        print("[CLEAR] 삭제할 벡터스토어가 없습니다.")


def get_files_to_process(file_path: Optional[str] = None) -> List[pathlib.Path]:
    """처리할 파일 목록 반환"""
    if file_path:
        # 특정 파일만 처리
        target = pathlib.Path(file_path)
        if not target.is_absolute():
            target = ROOT / target
        if not target.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {target}")
        return [target]
    else:
        # data/embeddings 폴더의 모든 .txt, .md 파일
        files = []
        for pattern in ["*.txt", "*.md"]:
            files.extend(glob.glob(str(DATA_DIR / pattern)))
        return [pathlib.Path(f) for f in files]


def load_texts(files: List[pathlib.Path]) -> List[Dict[str, str]]:
    """파일들을 읽어서 텍스트 리스트로 변환"""
    texts = []
    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if not content.strip():
                print(f"[SKIP] 빈 파일: {file_path.name}")
                continue
            
            # 상대 경로를 source로 사용
            source = str(file_path.relative_to(ROOT))
            texts.append({"text": content, "source": source})
            print(f"[LOAD] {file_path.name} ({len(content)} chars)")
        except Exception as e:
            print(f"[ERROR] 파일 읽기 실패 {file_path.name}: {e}")
    
    return texts


def main(args):
    """메인 처리 함수"""
    print("=" * 60)
    print("법령 데이터 Vector DB 추가 스크립트")
    print("=" * 60)
    
    # 1. 기존 데이터 삭제 (옵션)
    if args.clear:
        clear_vectorstore()
    
    # 2. 처리할 파일 목록 가져오기
    try:
        files = get_files_to_process(args.file)
        if not files:
            print(f"[WARN] 처리할 파일이 없습니다. {DATA_DIR} 폴더를 확인하세요.")
            return
        print(f"[INFO] 처리할 파일: {len(files)}개")
    except Exception as e:
        print(f"[ERROR] {e}")
        return
    
    # 3. 파일 읽기
    texts = load_texts(files)
    if not texts:
        print("[ERROR] 읽을 수 있는 파일이 없습니다.")
        return
    
    # 4. 텍스트 청킹
    print(f"\n[CHUNK] 청킹 시작 (chunk_size={args.chunk_size}, overlap={args.chunk_overlap})")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        separators=["\n\n", "\n", "。", ".", " ", ""]  # 한국어/일본어/영어 구분자
    )
    
    chunks, metadatas = [], []
    for t in texts:
        parts = splitter.split_text(t["text"])
        chunks.extend(parts)
        metadatas.extend([{"source": t["source"]}] * len(parts))
        print(f"  - {t['source']}: {len(parts)}개 청크")
    
    print(f"[CHUNK] 총 {len(chunks)}개 청크 생성")
    
    # 5. 임베딩 및 벡터스토어에 추가
    print(f"\n[EMBED] 임베딩 모델 로딩: {EMBED_MODEL}")
    embeds = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        encode_kwargs={"normalize_embeddings": True}
    )
    
    print(f"[VECTOR] ChromaDB 연결: {STORE_DIR}")
    vs = Chroma(
        persist_directory=str(STORE_DIR),
        collection_name=COLLECTION,
        embedding_function=embeds
    )
    
    if chunks:
        print(f"[ADD] {len(chunks)}개 청크를 벡터스토어에 추가 중...")
        vs.add_texts(chunks, metadatas=metadatas)
        vs.persist()
        print(f"[OK] 완료! 저장 위치: {STORE_DIR}")
        
        # 상태 확인
        try:
            count = vs._collection.count()  # type: ignore
            print(f"[STATUS] 현재 벡터스토어 문서 수: {count}개")
        except Exception:
            print("[STATUS] 문서 수 확인 실패 (정상 동작에는 문제 없음)")
    else:
        print("[WARN] 추가할 청크가 없습니다.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="법령 데이터를 Vector DB에 추가",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 모든 파일 추가
  python tools/ingest.py

  # 특정 파일만 추가
  python tools/ingest.py --file data/embeddings/주택임대차보호법.txt

  # 기존 데이터 삭제 후 재추가
  python tools/ingest.py --clear
        """
    )
    ap.add_argument(
        "--chunk-size",
        type=int,
        default=700,
        help="청크 크기 (기본: 700자)"
    )
    ap.add_argument(
        "--chunk-overlap",
        type=int,
        default=120,
        help="청크 간 겹치는 부분 (기본: 120자)"
    )
    ap.add_argument(
        "--file",
        type=str,
        default=None,
        help="특정 파일만 처리 (예: data/embeddings/법령.txt)"
    )
    ap.add_argument(
        "--clear",
        action="store_true",
        help="기존 벡터스토어 삭제 후 재생성"
    )
    args = ap.parse_args()
    main(args)
