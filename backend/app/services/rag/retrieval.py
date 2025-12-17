# -*- coding: utf-8 -*-
"""
RAG 검색 유틸
- Chroma(VectorStore) + HuggingFaceEmbeddings
- search_law(query, k): [{text, source, score}] 반환
- kb_status(): {"name", "count", "persist_directory"}
- 하위호환 alias: search, stats, RULE_HINTS
"""

from __future__ import annotations
import pathlib
from typing import List, Dict, Any, Tuple

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# ─────────────────────────────────────────────────────────────
# 경로: .../rentai/backend/app/services/rag/retrieval.py
# parents[4] == .../rentai  (rag→services→app→backend→rentai)
# tools/ingest.py가 쓰는 경로와 맞춤: rentai/vectorstore/chroma
# ─────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parents[4]   # .../rentai
STORE_DIR = ROOT / "vectorstore" / "chroma"
COLLECTION = "lease-law"

# 모델 파라미터
_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Lazy 싱글톤
_EMB: HuggingFaceEmbeddings | None = None
_VS: Chroma | None = None


def _ensure_ready() -> None:
    """임베딩/벡터스토어 lazy 로딩."""
    global _EMB, _VS
    if _EMB is None:
        _EMB = HuggingFaceEmbeddings(
            model_name=_EMBED_MODEL,
            encode_kwargs={"normalize_embeddings": True},
        )
    if _VS is None:
        STORE_DIR.mkdir(parents=True, exist_ok=True)
        _VS = Chroma(
            persist_directory=str(STORE_DIR),
            collection_name=COLLECTION,
            embedding_function=_EMB,
        )


def _sim_search(vs: Chroma, query: str, k: int) -> List[Tuple[Any, float]]:
    """
    Chroma 점수 API가 버전에 따라 다름:
      - similarity_search_with_relevance_scores: score 높을수록 유사(보통 0~1)
      - similarity_search_with_score           : 보통 distance(작을수록 유사)
    둘 다 대응.
    """
    # 우선 relevance_scores 시도
    try:
        pairs = vs.similarity_search_with_relevance_scores(query, k=k)
        # 형식: [(Document, relevance_score), ...]
        # relevance_score는 높을수록 유사. 그대로 반환.
        return [(doc, float(score)) for doc, score in pairs]
    except Exception:
        pass

    # 구버전 fallback
    pairs = vs.similarity_search_with_score(query, k=k)
    # 형식: [(Document, distance), ...]  distance는 작을수록 유사.
    # 비교/정렬은 호출부에서 동일하게 사용하고, 표시만 위해 score를 그대로 둔다.
    return [(doc, float(score)) for doc, score in pairs]


def search_law(query: str, k: int = 3, score_threshold: float | None = None) -> List[Dict[str, Any]]:
    """
    질의문으로 유사 문서 상위 k개 반환
    반환: [{text, source, score}]
    - score_threshold: None이면 필터링 안함.
      (주의: relevance/ distance 혼재 가능 → 임계값은 운영 중 로그 보며 조정 권장)
    """
    _ensure_ready()
    assert _VS is not None

    pairs = _sim_search(_VS, query, k)
    items: List[Dict[str, Any]] = []

    for doc, score in pairs:
        # 메타에서 source 추출
        meta = getattr(doc, "metadata", {}) or {}
        source = meta.get("source") or meta.get("path") or "unknown"

        # 임계값 필터 (점수 정의 혼재 가능하므로 기본 비활성)
        if score_threshold is not None:
            # 경험적으로 relevance(0~1)는 threshold를 '이상' 기준,
            # distance는 threshold를 '이하' 기준으로 쓰는게 일반적이지만
            # 혼재 환경에선 혼동 가능 → 기본은 비활성 권장.
            pass

        items.append({"text": doc.page_content, "source": source, "score": score})

    return items


def kb_status() -> Dict[str, Any]:
    """KB 상태 확인 (count, 경로 등)"""
    _ensure_ready()
    assert _VS is not None
    count = 0
    # Chroma 버전에 따라 내부 API 다름 → 방어적 접근
    try:
        count = _VS._collection.count()  # type: ignore[attr-defined]
    except Exception:
        try:
            ids = _VS._collection.get(include=[])  # type: ignore[attr-defined]
            # chromadb>=0.5는 dict 반환 가능 → 안전 처리
            if isinstance(ids, dict) and "ids" in ids:
                count = len(ids["ids"])
            elif isinstance(ids, (list, tuple)) and len(ids) > 0:
                count = len(ids[0])
        except Exception:
            count = 0
    return {"name": COLLECTION, "count": int(count), "persist_directory": str(STORE_DIR)}


# ── 하위호환 alias (fastapi_app의 기존 임포트와 호환) ──
def search(query: str, k: int = 3) -> List[Dict[str, Any]]:
    return search_law(query, k=k)

def stats() -> Dict[str, Any]:
    return kb_status()


# ── 규칙별 검색어 힌트(선택적으로 확장) ──
RULE_HINTS: Dict[str, list[str]] = {
    "확정일자": ["확정일자", "주택임대차보호법", "우선변제", "대항력", "임차권"],
    "대항력": ["대항력", "주민등록 전입신고", "점유", "확정일자", "우선변제권"],
    "우선변제": ["우선변제", "보증금", "확정일자", "배당요구", "경매"],
    "전입신고": ["전입신고", "주민등록", "대항력", "점유", "열람"],
    "보증금 반환": ["보증금", "반환기한", "지연이자", "계약종료", "원상복구"],
    "지연이자": ["지연이자", "지체상금", "지연손해금", "연체이자", "이율"],
    "특약": ["특약", "표준계약서 위반", "불공정", "무효", "과도한 면책"],
    "원상복구": ["원상복구", "수선의무", "보수", "훼손", "반환시 상태"],
    "관리비": ["관리비", "항목", "부과기준", "체납", "정산"],
}

__all__ = ["search_law", "kb_status", "search", "stats", "RULE_HINTS"]
