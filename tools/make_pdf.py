#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
임대차계약서 이상탐지 시스템 발표용 PDF 생성기

사용 예:
  python rentai/tools/make_pdf.py \
    --project "임대차계약서 이상탐지 시스템" \
    --presenter "박병현" \
    --out "docs/임대차계약서_이상탐지_시스템_발표.pdf"
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT


def _register_korean_font() -> str:
    """가급적 한글 폰트를 등록하고, 실패 시 Helvetica로 폴백"""
    # 프로젝트 내 폰트 (rentai/report/fonts)
    here = Path(__file__).resolve()
    fonts_dir = here.parents[2] / "report" / "fonts"
    candidates = [
        (fonts_dir / "NanumGothic.ttf", "NanumGothic"),
        (fonts_dir / "NotoSansKR-Regular.ttf", "NotoSansKR"),
    ]
    for fpath, name in candidates:
        try:
            if fpath.exists():
                pdfmetrics.registerFont(TTFont(name, str(fpath)))
                return name
        except Exception:
            pass
    # Windows 기본 'Malgun Gothic' 시도
    try:
        pdfmetrics.registerFont(TTFont("MalgunGothic", "malgun.ttf"))
        return "MalgunGothic"
    except Exception:
        return "Helvetica"


def _styles() -> dict:
    base = getSampleStyleSheet()
    fname = _register_korean_font()
    return {
        "H1": ParagraphStyle(name="H1", parent=base["Heading1"], fontName=fname, alignment=TA_LEFT, fontSize=18, leading=24, spaceAfter=8),
        "H2": ParagraphStyle(name="H2", parent=base["Heading2"], fontName=fname, alignment=TA_LEFT, fontSize=14, leading=20, spaceAfter=6),
        "Body": ParagraphStyle(name="Body", parent=base["BodyText"], fontName=fname, alignment=TA_LEFT, fontSize=10.5, leading=16, spaceAfter=4),
        "Small": ParagraphStyle(name="Small", parent=base["BodyText"], fontName=fname, alignment=TA_LEFT, fontSize=9, leading=12, textColor=colors.HexColor("#555")),
    }


def _bullets(items: List[str], style: ParagraphStyle) -> ListFlowable:
    return ListFlowable([ListItem(Paragraph(i, style)) for i in items], bulletType='bullet', start='-', leftIndent=12)


def build_pdf(project: str, presenter: str, out_path: Path) -> None:
    st = _styles()
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm,
        title=project, author=presenter,
    )
    story: List = []

    today = datetime.now().strftime("%Y-%m-%d")

    # 1) 타이틀
    story.append(Paragraph(project, st["H1"]))
    story.append(Paragraph(f"발표자: {presenter} | 날짜: {today}", st["Small"]))
    story.append(Spacer(1, 8))

    # 2) 프로젝트 개요
    story.append(Paragraph("프로젝트 개요", st["H2"]))
    story.append(_bullets([
        "목적: 전세계약서 PDF 자동 분석·이상 탐지·보고서 생성",
        "구성: FastAPI 백엔드, Streamlit 프론트, RAG(Chroma), ReportLab",
        "이번 범위: 정리/통합/정합화 및 RAG 인덱스 재구축",
    ], st["Body"]))
    story.append(Spacer(1, 6))

    # 3) 현재 아키텍처
    story.append(Paragraph("현재 아키텍처", st["H2"]))
    story.append(_bullets([
        "백엔드 진입점 단일화: backend/fastapi_app.py",
        "서비스: 파서/필드추출/룰엔진/RAG/리포트",
        "프론트: frontend/app.py (API 연동 및 보고서 다운로드)",
    ], st["Body"]))

    # 4) 정리 작업(클린업)
    story.append(Paragraph("정리 작업(클린업)", st["H2"]))
    story.append(_bullets([
        "__pycache__/ .pyc, 미사용 템플릿 삭제",
        "레거시 파일에 '미사용/레거시' 주석 표시",
        "효과: 혼선 제거, 유지보수성 향상",
    ], st["Body"]))

    # 5) 백엔드 진입점 통일
    story.append(Paragraph("백엔드 진입점 통일", st["H2"]))
    story.append(_bullets([
        "app/main.py ↔ fastapi_app.py 중복 제거",
        "공식 엔드포인트는 fastapi_app.py에 집중",
        "장점: 단일 실행/배포 경로, 디버깅 단순화",
    ], st["Body"]))

    # 6) API 응답 스키마 표준화
    story.append(Paragraph("API 응답 스키마 표준화", st["H2"]))
    story.append(_bullets([
        "프론트 기대 구조: summary / fields / issues / rag",
        "하위 호환: 원본 데이터 동시 제공",
        "프론트 렌더링 로직 간소화",
    ], st["Body"]))

    # 7) 레거시 라우터 정리
    story.append(Paragraph("레거시 라우터 정리", st["H2"]))
    story.append(_bullets([
        "app/api/analyze.py → 410 Gone(안내 전용)",
        "app/main.py에서 레거시 include 제거",
        "공식 엔드포인트 안내 명확화",
    ], st["Body"]))

    # 8) RAG 인덱스 재구축
    story.append(Paragraph("RAG 인덱스 재구축", st["H2"]))
    story.append(_bullets([
        "tools/ingest.py로 임베딩 생성, vectorstore/chroma 저장",
        "/kb/status, /reference/law 점검",
        "말뭉치: lease_law_samples.txt 등",
    ], st["Body"]))

    # 9) 데모 플로우
    story.append(Paragraph("데모 플로우", st["H2"]))
    story.append(_bullets([
        "업로드 → /analyze/pdf → 결과 요약/이슈/RAG 근거",
        "보고서 다운로드: /report/pdf (원본 PDF 첨부)",
        "PDF: 필드/이슈/근거/프리뷰 포함",
    ], st["Body"]))

    # 10) 변경 전/후 요약
    story.append(Paragraph("변경 전/후 요약", st["H2"]))
    story.append(_bullets([
        "전: 진입점 이원화, 응답 스키마 불일치, 레거시 혼재",
        "후: 단일 진입점, 표준 스키마, 레거시 명시/정리",
    ], st["Body"]))

    # 11) 리스크 및 대응
    story.append(Paragraph("리스크 및 대응", st["H2"]))
    story.append(_bullets([
        "RAG 품질: 말뭉치 확대·정제",
        "파서 정밀도: 규칙/정규식 개선",
        "키 관리: .env 및 권한 관리",
    ], st["Body"]))

    # 12) 다음 계획
    story.append(Paragraph("다음 계획(로드맵)", st["H2"]))
    story.append(_bullets([
        "테스트 보강(파서/룰엔진)",
        "예외 처리/로깅 개선",
        "PDF 레이아웃 개선, 도커/CI 도입",
    ], st["Body"]))

    # 13) Q&A
    story.append(Paragraph("Q&A", st["H2"]))
    story.append(_bullets(["질문을 받겠습니다."], st["Body"]))

    doc.build(story)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--presenter", required=True)
    ap.add_argument("--out", default="docs/presentation_rentai.pdf")
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(project=args.project, presenter=args.presenter, out_path=out_path)
    print(f"[PDF OK] saved -> {out_path}")


if __name__ == "__main__":
    main()


