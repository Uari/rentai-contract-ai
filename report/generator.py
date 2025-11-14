# -*- coding: utf-8 -*-
"""
PDF 리포트 생성기 (ReportLab)
- 한글 폰트 자동 등록(가능한 경우) + 스타일(KoH1/KoH2/KoBody/KoStrong)
- 룰 이슈 포맷 정규화(_normalize_issue): id/title 또는 code/message 모두 지원
- context(dict) 입력 -> PDF bytes 반환(generate_pdf_bytes)
"""
from __future__ import annotations

import io
import os
import pathlib
from datetime import datetime
from typing import Any, Dict, List

# ReportLab imports
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

# --------------------------------------------------------------------------------------
# 폰트 / 스타일
# --------------------------------------------------------------------------------------


def _register_korean_font_if_available() -> str:
    """
    rentai/report/fonts/ 내 대표 한글 폰트 탐색 후 등록.
    우선순위: NanumGothic -> NotoSansKR -> NotoSansCJKkr -> MalgunGothic (Windows) -> Helvetica(영문)
    반환: 등록된 폰트명(ParagraphStyle에서 fontName으로 사용)
    """
    # 탐색 경로: 현재 파일 기준 ../report/fonts
    here = pathlib.Path(__file__).resolve()
    fonts_dir = here.parent / "fonts"

    # 후보 목록 (파일명, 내부폰트명 동일하게 등록)
    candidates = [
        ("NanumGothic.ttf", "NanumGothic"),
        ("NotoSansKR-Regular.ttf", "NotoSansKR"),
        ("NotoSansCJKkr-Regular.ttf", "NotoSansCJKkr"),
    ]

    for fname, fontname in candidates:
        fpath = fonts_dir / fname
        if fpath.exists():
            try:
                pdfmetrics.registerFont(TTFont(fontname, str(fpath)))
                return fontname
            except Exception:
                pass

    # Windows 기본 'Malgun Gothic' 시도 (미설치 환경에서는 실패 가능)
    try:
        pdfmetrics.registerFont(TTFont("MalgunGothic", "malgun.ttf"))
        return "MalgunGothic"
    except Exception:
        pass

    # 최종 fallback: Helvetica (한글 완전 호환 X, 그래도 에러 없이 동작)
    return "Helvetica"


def _build_styles() -> dict:
    base = getSampleStyleSheet()
    font_name = _register_korean_font_if_available()

    styles = {
        "KoH1": ParagraphStyle(
            name="KoH1",
            parent=base["Heading1"],
            alignment=TA_LEFT,
            fontName=font_name,
            fontSize=16,
            leading=22,
            spaceAfter=8,
        ),
        "KoH2": ParagraphStyle(
            name="KoH2",
            parent=base["Heading2"],
            alignment=TA_LEFT,
            fontName=font_name,
            fontSize=13,
            leading=18,
            spaceAfter=6,
        ),
        "KoBody": ParagraphStyle(
            name="KoBody",
            parent=base["BodyText"],
            alignment=TA_LEFT,
            fontName=font_name,
            fontSize=10.5,
            leading=15,
            spaceAfter=4,
        ),
        "KoStrong": ParagraphStyle(
            name="KoStrong",
            parent=base["BodyText"],
            alignment=TA_LEFT,
            fontName=font_name,
            fontSize=10.5,
            leading=15,
            spaceAfter=4,
            textColor=colors.HexColor("#222222"),
        ),
        "KoSmall": ParagraphStyle(
            name="KoSmall",
            parent=base["BodyText"],
            alignment=TA_LEFT,
            fontName=font_name,
            fontSize=9,
            leading=12,
            spaceAfter=2,
            textColor=colors.HexColor("#555555"),
        ),
        "KoMonoSmall": ParagraphStyle(
            name="KoMonoSmall",
            parent=base["Code"],
            alignment=TA_LEFT,
            fontName=font_name,   # 모노 폰트가 없을 수 있으므로 동일 폰트 지정
            fontSize=8.5,
            leading=12,
            spaceAfter=2,
            textColor=colors.HexColor("#333333"),
        ),
    }
    return styles

# --------------------------------------------------------------------------------------
# 데이터 정규화 / 유틸
# --------------------------------------------------------------------------------------

def _normalize_issue(raw: dict) -> dict:
    """
    룰엔진/버전에 따라 다른 키 이름을 단일 포맷으로 정규화.
    반환 키: code, message, severity, weight, score, reasons, references
    """
    code = raw.get("id") or raw.get("code") or ""
    message = raw.get("title") or raw.get("message") or code or "이슈"
    severity = (raw.get("severity") or "MED").upper()
    # score/weight: 일부 버전은 weight만 제공하거나 score를 제공
    weight = int(raw.get("weight") or 0)
    score = int(raw.get("score") or weight or 0)

    # 사유/레퍼런스는 배열 기대
    reasons = raw.get("reasons") or []
    references = raw.get("references") or []

    # 안전장치: 타입 보정
    if not isinstance(reasons, list):
        reasons = [str(reasons)]
    if not isinstance(references, list):
        references = []

    # 각 reference 항목 정규화
    norm_refs = []
    for ref in references:
        if isinstance(ref, dict):
            txt = ref.get("text") or ref.get("chunk") or ""
            src = ref.get("source") or ref.get("path") or ""
            sc = ref.get("score")
            norm_refs.append({"text": txt, "source": src, "score": sc})
        else:
            norm_refs.append({"text": str(ref), "source": "", "score": None})

    return {
        "code": code,
        "message": message,
        "severity": severity,
        "weight": weight,
        "score": score,
        "reasons": reasons,
        "references": norm_refs,
    }


def _kv_table(data, KO_FONT_NAME: str) -> Table:
    table = Table(data, colWidths=[35*mm, 130*mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), KO_FONT_NAME),   # ← 한글폰트 적용
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
        ("BOX", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _format_bool(b: Any) -> str:
    if isinstance(b, bool):
        return "예" if b else "아니오"
    return str(b)

# --------------------------------------------------------------------------------------
# 메인 엔트리
# --------------------------------------------------------------------------------------

def generate_pdf_bytes(context: Dict[str, Any]) -> bytes:
    """
    context 예시:
    {
        "file": "sample.pdf",
        "page_count": 3,
        "sentence_count": 120,
        "tables_found": 1,
        "signature_detected": true,
        "extracted_fields": {...},
        "preview_sentences": [...],
        "risk": {
            "total_score": 7,
            "issues": [
                {
                    "id": "RULE-001", "title": "보증금 반환 기한 없음",
                    "severity": "HIGH", "score": 5,
                    "reasons": ["확정일자 필드 누락"],
                    "references": [{"text":"...","source":"임대차보호법 §3-2","score":0.23}]
                }
            ]
        }
    }
    """
    styles = _build_styles()
    buffer = io.BytesIO()

    # 문서 설정
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18*mm,
        rightMargin=18*mm,
        topMargin=14*mm,
        bottomMargin=14*mm,
        title="임대차 계약서 분석 리포트",
        author="RentAI",
    )

    story: List[Any] = []

    # ----------------------------------------------------------------------------------
    # 타이틀 & 메타
    # ----------------------------------------------------------------------------------
    story.append(Paragraph("임대차 계약서 분석 리포트", styles["KoH1"]))
    meta_line = f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    story.append(Paragraph(meta_line, styles["KoSmall"]))
    story.append(Spacer(1, 6))

    KO_FONT_NAME = styles["KoBody"].fontName  # 예: "NotoSansKR" 또는 등록한 이름
    # 개요 테이블
    file_name = context.get("file") or "N/A"
    page_count = context.get("page_count", 0)
    sentence_count = context.get("sentence_count", 0)
    tables_found = context.get("tables_found", 0)
    signature_detected = context.get("signature_detected", False)

    overview = [
        ["파일명", file_name],
        ["페이지 수", str(page_count)],
        ["문장 수", str(sentence_count)],
        ["표 검출 수", str(tables_found)],
        ["서명/날인 키워드", _format_bool(signature_detected)],
    ]
    story.append(_kv_table(overview, KO_FONT_NAME))
    story.append(Spacer(1, 10))

    # ----------------------------------------------------------------------------------
    # 추출 필드 요약
    # ----------------------------------------------------------------------------------
    extracted = context.get("extracted_fields") or {}
    story.append(Paragraph("핵심 필드 요약", styles["KoH2"]))
    fields_rows: List[List[str]] = []

    # 필드 예시: 보증금/월세/기간/주소/확정일자/전입신고/관리비 등
    rent = extracted.get("rent") or {}
    period = extracted.get("period") or {}
    maintenance = extracted.get("maintenance_fee") or extracted.get("maintenance") or {}

    fields_rows.extend([
        ["보증금", str(rent.get("deposit") or "")],
        ["월세(차임)", str(rent.get("monthly_rent") or "")],
        ["계약기간(시작)", str(period.get("start") or "")],
        ["계약기간(종료)", str(period.get("end") or "")],
        ["소재지/주소", str(extracted.get("address") or "")],
        ["확정일자", str(extracted.get("confirmation_date") or "")],
        ["전입신고 여부", _format_bool(extracted.get("resident_reported"))],
        ["관리비(포함여부)", _format_bool(maintenance.get("included"))],
        ["관리비(금액)", str(maintenance.get("amount") or "")],
        ["원상복구 조항", str(extracted.get("restoration_clause") or "")],
        ["위약 조항", str(extracted.get("termination_penalty") or "")],
    ])

    story.append(_kv_table(fields_rows, KO_FONT_NAME))
    story.append(Spacer(1, 10))

    # ----------------------------------------------------------------------------------
    # 위험도 요약
    # ----------------------------------------------------------------------------------
    risk = context.get("risk") or {}
    total_score = risk.get("total_score", 0)
    issues_raw = risk.get("issues") or []

    story.append(Paragraph("위험도 요약", styles["KoH2"]))
    story.append(Paragraph(f"총 위험 점수: {total_score}", styles["KoBody"]))
    story.append(Paragraph(f"이슈 개수: {len(issues_raw)}", styles["KoBody"]))
    story.append(Spacer(1, 6))

    # ----------------------------------------------------------------------------------
    # 이슈 상세
    # ----------------------------------------------------------------------------------
    if issues_raw:
        story.append(Paragraph("이슈 상세", styles["KoH2"]))
        for raw in issues_raw:
            issue = _normalize_issue(raw)

            title = f"{issue['code']} — {issue['message']}" if issue["code"] else issue["message"]
            story.append(Paragraph(title, styles["KoH2"]))

            meta = f"중요도: {issue['severity']} | 점수: {issue['score']}"
            story.append(Paragraph(meta, styles["KoSmall"]))

            if issue["reasons"]:
                story.append(Paragraph("사유:", styles["KoStrong"]))
                for r in issue["reasons"]:
                    story.append(Paragraph(f"• {r}", styles["KoBody"]))

            if issue["references"]:
                story.append(Paragraph("법적 근거 (RAG):", styles["KoStrong"]))
                for ref in issue["references"]:
                    txt = ref.get("text") or ""
                    src = ref.get("source") or ""
                    sc = ref.get("score")
                    line = f"• {txt}"
                    if src:
                        line += f" (출처: {src}"
                        if sc is not None:
                            line += f", score={sc}"
                        line += ")"
                    story.append(Paragraph(line, styles["KoBody"]))

            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("검출된 이슈가 없습니다.", styles["KoBody"]))

    story.append(PageBreak())

    # ----------------------------------------------------------------------------------
    # 부록: 본문 일부 프리뷰
    # ----------------------------------------------------------------------------------
    preview = context.get("preview_sentences") or []
    if preview:
        story.append(Paragraph("부록: 본문 미리보기", styles["KoH2"]))
        for i, s in enumerate(preview, 1):
            story.append(Paragraph(f"{i}. {s}", styles["KoBody"]))
    else:
        story.append(Paragraph("본문 미리보기가 없습니다.", styles["KoBody"]))

    # ----------------------------------------------------------------------------------
    # 빌드
    # ----------------------------------------------------------------------------------
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


