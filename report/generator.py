# -*- coding: utf-8 -*-
"""
PDF 리포트 생성기 (ReportLab) - 사용자 친화 버전
- 깔끔하고 직관적인 레이아웃
- 색상 코딩으로 위험도 시각화
- 핵심 정보 우선 배치
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
from reportlab.lib.enums import TA_LEFT, TA_CENTER
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
    KeepTogether,
)

# --------------------------------------------------------------------------------------
# 폰트 / 스타일
# --------------------------------------------------------------------------------------

def _register_korean_font_if_available() -> str:
    """한글 폰트 등록"""
    here = pathlib.Path(__file__).resolve()
    fonts_dir = here.parent / "fonts"

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

    try:
        pdfmetrics.registerFont(TTFont("MalgunGothic", "malgun.ttf"))
        return "MalgunGothic"
    except Exception:
        pass

    return "Helvetica"


def _build_styles() -> dict:
    base = getSampleStyleSheet()
    font_name = _register_korean_font_if_available()

    styles = {
        "Title": ParagraphStyle(
            name="Title",
            fontName=font_name,
            fontSize=20,
            leading=26,
            textColor=colors.HexColor("#1a1a1a"),
            spaceAfter=4,
        ),
        "Subtitle": ParagraphStyle(
            name="Subtitle",
            fontName=font_name,
            fontSize=11,
            textColor=colors.HexColor("#666666"),
            spaceAfter=16,
        ),
        "SectionTitle": ParagraphStyle(
            name="SectionTitle",
            fontName=font_name,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#2c3e50"),
            spaceBefore=10,
            spaceAfter=8,
            leftIndent=0,
        ),
        "Body": ParagraphStyle(
            name="Body",
            fontName=font_name,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#333333"),
            spaceAfter=4,
        ),
        "BodyBold": ParagraphStyle(
            name="BodyBold",
            fontName=font_name,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1a1a1a"),
            spaceAfter=4,
        ),
        "Small": ParagraphStyle(
            name="Small",
            fontName=font_name,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#666666"),
            spaceAfter=2,
        ),
        "BigNumber": ParagraphStyle(
            name="BigNumber",
            fontName=font_name,
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#2c3e50"),
            alignment=TA_CENTER,
        ),
    }
    return styles


# --------------------------------------------------------------------------------------
# 유틸리티
# --------------------------------------------------------------------------------------

def _get_risk_color(severity: str) -> colors.Color:
    """위험도별 색상"""
    severity = (severity or "MED").upper()
    if severity in ["HIGH", "CRITICAL"]:
        return colors.HexColor("#e74c3c")  # 빨강
    elif severity == "MED":
        return colors.HexColor("#f39c12")  # 주황
    else:  # LOW
        return colors.HexColor("#27ae60")  # 초록


def _format_number(num: Any) -> str:
    """숫자 포맷팅"""
    if num is None or num == "":
        return "미기재"
    
    # dict인 경우 value 가져오기
    if isinstance(num, dict):
        num = num.get("value") or num.get("deposit") or num.get("monthly_rent")
    
    if num is None or num == "":
        return "미기재"
    
    try:
        if isinstance(num, str):
            num = int(num.replace(",", ""))
        return f"{int(num):,}원"
    except:
        return str(num)


def _format_date(date_str: Any) -> str:
    """날짜 포맷팅"""
    if date_str is None or date_str == "":
        return "미기재"
    
    # dict인 경우 value 가져오기
    if isinstance(date_str, dict):
        date_str = date_str.get("value") or date_str.get("start") or date_str.get("end")
    
    if date_str is None or date_str == "":
        return "미기재"
    
    return str(date_str)


def _format_contract_type(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("value")
    if not value:
        return "미기재"
    mapping = {
        "jeonse": "전세",
        "wolse": "월세(차임)",
    }
    return mapping.get(str(value).lower(), str(value))


def _create_summary_box(title: str, value: str, color: colors.Color, font_name: str) -> Table:
    """요약 박스 생성"""
    data = [
        [Paragraph(title, ParagraphStyle(
            name="BoxTitle",
            fontName=font_name,
            fontSize=9,
            textColor=colors.HexColor("#666666"),
            alignment=TA_CENTER,
        ))],
        [Paragraph(value, ParagraphStyle(
            name="BoxValue",
            fontName=font_name,
            fontSize=14,
            leading=18,
            textColor=color,
            alignment=TA_CENTER,
        ))],
    ]
    
    table = Table(data, colWidths=[45*mm])
    table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 1, color),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _create_info_table(data: List[List[str]], font_name: str) -> Table:
    """정보 테이블 생성"""
    table = Table(data, colWidths=[50*mm, 110*mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#666666")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1a1a1a")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


# --------------------------------------------------------------------------------------
# 메인 생성 함수
# --------------------------------------------------------------------------------------

def generate_pdf_bytes(context: Dict[str, Any]) -> bytes:
    """
    깔끔하고 사용자 친화적인 리포트 생성
    """
    styles = _build_styles()
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
        title="임대차 계약서 분석 리포트",
        author="RentAI",
    )

    story: List[Any] = []
    font_name = styles["Body"].fontName

    # ==================================================================================
    # 헤더
    # ==================================================================================
    story.append(Paragraph("🏠 임대차 계약서 분석 리포트", styles["Title"]))
    story.append(Paragraph(
        f"생성일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}",
        styles["Subtitle"]
    ))
    story.append(Spacer(1, 5*mm))

    # ==================================================================================
    # 위험도 요약 (큰 박스로 강조)
    # ==================================================================================
    risk = context.get("risk") or {}
    issues = risk.get("issues") or []
    risk_level_key = str(risk.get("level") or "safe").lower()
    level_styles = {
        "critical": ("위험", "🚨", colors.HexColor("#e74c3c")),
        "warning": ("주의", "⚠️", colors.HexColor("#f39c12")),
        "safe": ("양호", "✅", colors.HexColor("#27ae60")),
    }
    risk_label, risk_emoji, risk_color = level_styles.get(
        risk_level_key, level_styles["safe"]
    )

    risk_box_data = [
        [Paragraph(f"{risk_emoji} 종합 위험도", ParagraphStyle(
            name="RiskTitle",
            fontName=font_name,
            fontSize=14,
            textColor=colors.white,
            alignment=TA_CENTER,
        ))],
        [Paragraph(risk_label, ParagraphStyle(
            name="RiskValue",
            fontName=font_name,
            fontSize=20,
            leading=26,
            textColor=colors.white,
            alignment=TA_CENTER,
        ))],
        [Paragraph(f"감지된 이슈: {len(issues)}건", ParagraphStyle(
            name="RiskSub",
            fontName=font_name,
            fontSize=11,
            textColor=colors.white,
            alignment=TA_CENTER,
        ))],
    ]
    
    risk_table = Table(risk_box_data, colWidths=[170*mm])
    risk_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), risk_color),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 5*mm))

    # ==================================================================================
    # 주요 이슈 (TOP 3) + 상세 분석
    # ==================================================================================
    if issues:
        story.append(Paragraph("📌 주요 발견사항 (TOP 3)", styles["SectionTitle"]))
        
        top_issues = sorted(issues, key=lambda x: x.get("score", 0), reverse=True)[:3]
        for idx, issue in enumerate(top_issues, 1):
            severity = (issue.get("severity") or "MED").upper()
            message = issue.get("title") or issue.get("message") or "이슈"
            issue_color = _get_risk_color(severity)
            issue_data = [
                [Paragraph(f"{idx}. {message}", ParagraphStyle(
                    name="IssueText",
                    fontName=font_name,
                    fontSize=11,
                    textColor=colors.HexColor("#1a1a1a"),
                ))],
            ]
            issue_table = Table(issue_data, colWidths=[170*mm])
            issue_table.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 1.5, issue_color),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
            ]))
            story.append(issue_table)
            story.append(Spacer(1, 3*mm))
    else:
        story.append(Paragraph("📌 주요 발견사항 (TOP 3)", styles["SectionTitle"]))
        story.append(Paragraph("✅ 특별한 위험 요소가 발견되지 않았습니다.", styles["Body"]))
        story.append(Spacer(1, 3*mm))

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("📄 상세 분석 (전체 이슈)", styles["SectionTitle"]))
    if issues:
        for idx, issue in enumerate(issues, 1):
            severity = (issue.get("severity") or "MED").upper()
            message = issue.get("title") or issue.get("message") or "이슈"
            reasons = issue.get("reasons") or []
            story.append(Paragraph(f"{idx}. {message}", styles["BodyBold"]))
            info_line = f"중요도: {severity}"
            if issue.get("level"):
                level_map = {"critical": "위험", "warning": "주의", "safe": "양호"}
                info_line += f" | 등급: {level_map.get(issue.get('level'), issue.get('level'))}"
            story.append(Paragraph(info_line, styles["Small"]))
            if reasons:
                for reason in reasons:
                    story.append(Paragraph(f"  • {reason}", styles["Body"]))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("✅ 상세 분석에서도 이슈가 발견되지 않았습니다.", styles["Body"]))
    story.append(Spacer(1, 5*mm))

    # ==================================================================================
    # 계약 정보 요약
    # ==================================================================================
    extracted = context.get("extracted_fields") or {}
    
    def safe_get_value(field_data, *keys):
        """필드에서 안전하게 값 추출"""
        if not field_data:
            return None
        
        # dict인 경우 value 키로 접근
        if isinstance(field_data, dict):
            # "value" 키가 있으면 먼저 시도
            if "value" in field_data:
                val = field_data["value"]
                # value도 dict이고 keys가 제공되면 해당 키로 접근
                if isinstance(val, dict) and keys:
                    # keys를 순차적으로 탐색
                    for key in keys:
                        if isinstance(val, dict):
                            val = val.get(key)
                        else:
                            return None
                    return val
                return val
            # "value" 키가 없으면 keys로 직접 접근
            elif keys:
                val = field_data
                for key in keys:
                    if isinstance(val, dict):
                        val = val.get(key)
                    else:
                        return None
                return val
            # keys도 없고 value도 없으면 필드 데이터 자체 반환
            return field_data
        
        return field_data
    
    # 보증금/월세
    rent = extracted.get("rent", {})
    deposit = safe_get_value(rent, "deposit")
    monthly_rent = safe_get_value(rent, "monthly_rent")

    # 계약기간
    period = extracted.get("period", {})
    start_date = safe_get_value(period, "start")
    end_date = safe_get_value(period, "end")

    # 주소
    address = extracted.get("address", {})
    address_value = safe_get_value(address)
    if address_value and not isinstance(address_value, str):
        address_value = str(address_value)
    address_value = address_value or ""

    # 확정일자
    conf_date = extracted.get("confirmation_date", {})
    # 계약 유형
    contract_type_val = safe_get_value(extracted.get("contract_type"))
    conf_value = safe_get_value(conf_date)
    if conf_value and not isinstance(conf_value, str):
        conf_value = str(conf_value)
    conf_value = conf_value or ""

    story.append(Paragraph("💰 금액 정보", styles["SectionTitle"]))
    money_data = [
        ["보증금", _format_number(deposit)],
        ["월세", _format_number(monthly_rent)],
    ]
    story.append(_create_info_table(money_data, font_name))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("📅 계약 기간", styles["SectionTitle"]))
    period_data = [
        ["시작일", _format_date(start_date)],
        ["종료일", _format_date(end_date)],
    ]
    story.append(_create_info_table(period_data, font_name))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("📍 기타 정보", styles["SectionTitle"]))
    other_data = [
        ["계약 유형", _format_contract_type(contract_type_val)],
        ["소재지", address_value if address_value else "미기재"],
        ["확정일자", conf_value if conf_value else "미기재"],
    ]
    story.append(_create_info_table(other_data, font_name))
    story.append(Spacer(1, 8*mm))

    # ==================================================================================
    # 상세 분석 (필요시)
    # ==================================================================================
    if len(issues) > 3:
        story.append(PageBreak())
        story.append(Paragraph("📄 상세 분석", styles["SectionTitle"]))
        story.append(Spacer(1, 3*mm))
        
        for idx, issue in enumerate(issues[3:], 4):
            severity = (issue.get("severity") or "MED").upper()
            message = issue.get("title") or issue.get("message") or "이슈"
            reasons = issue.get("reasons") or []
            
            story.append(Paragraph(f"{idx}. {message}", styles["BodyBold"]))
            story.append(Paragraph(f"중요도: {severity}", styles["Small"]))
            
            if reasons:
                for reason in reasons[:2]:  # 최대 2개만
                    story.append(Paragraph(f"  • {reason}", styles["Body"]))
            
            story.append(Spacer(1, 4*mm))

    # ==================================================================================
    # 푸터
    # ==================================================================================
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph(
        "이 리포트는 AI 기반으로 자동 생성되었으며, 참고용으로만 사용하시기 바랍니다.",
        styles["Small"]
    ))

    # 빌드
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
