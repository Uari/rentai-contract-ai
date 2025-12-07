# -*- coding: utf-8 -*-
"""
PDF 리포트 생성기 (ReportLab) - 사용자 친화 버전
- 깔끔하고 직관적인 레이아웃
- 색상 코딩으로 위험도 시각화
- 핵심 정보 우선 배치
- LLM 어드바이저 가이드 상세 포함
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
    ListFlowable,
    ListItem
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
        "GuideTitle": ParagraphStyle(
            name="GuideTitle",
            fontName=font_name,
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#2c3e50"),
            spaceBefore=4,
            spaceAfter=2,
        ),
        "GuideBody": ParagraphStyle(
            name="GuideBody",
            fontName=font_name,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#4b5563"),
            leftIndent=4,
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
    깔끔하고 사용자 친화적인 리포트 생성 (LLM 가이드 반영)
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
    # 주요 발견사항 및 가이드 (TOP 3)
    # ==================================================================================
    if issues:
        story.append(Paragraph("📌 주요 발견사항 및 전문가 가이드 (TOP 3)", styles["SectionTitle"]))
        
        # 중요도 순 정렬
        top_issues = sorted(issues, key=lambda x: x.get("score", 0), reverse=True)[:3]
        
        for idx, issue in enumerate(top_issues, 1):
            # KeepTogether로 이슈 단위가 페이지 넘김으로 잘리지 않게 함
            issue_elements = []
            
            severity = (issue.get("severity") or "MED").upper()
            message = issue.get("title") or issue.get("message") or "이슈"
            issue_color = _get_risk_color(severity)
            
            # --- 이슈 헤더 ---
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
            issue_elements.append(issue_table)
            issue_elements.append(Spacer(1, 2*mm))
            
            # --- LLM 가이드 내용 ---
            guide = issue.get("guide")
            if guide:
                # 1. 주의사항
                if guide.get("caution"):
                    issue_elements.append(Paragraph("⚠️ 주의사항", styles["GuideTitle"]))
                    issue_elements.append(Paragraph(guide["caution"], styles["GuideBody"]))
                
                # 2. 대처 방법
                if guide.get("action"):
                    issue_elements.append(Paragraph("💡 대처 방법", styles["GuideTitle"]))
                    actions = guide["action"]
                    if isinstance(actions, list):
                        for action in actions:
                            issue_elements.append(Paragraph(f"• {action}", styles["GuideBody"]))
                    else:
                        issue_elements.append(Paragraph(f"• {str(actions)}", styles["GuideBody"]))
                
                # 3. 법적 근거
                if guide.get("law"):
                    issue_elements.append(Paragraph("⚖️ 관련 법령", styles["GuideTitle"]))
                    issue_elements.append(Paragraph(guide["law"], styles["GuideBody"]))
            
            # 가이드가 없는 경우 기본 근거 표시
            elif issue.get("reasons"):
                issue_elements.append(Paragraph("🔍 상세 내용", styles["GuideTitle"]))
                for r in issue["reasons"]:
                    issue_elements.append(Paragraph(f"• {r}", styles["GuideBody"]))

            issue_elements.append(Spacer(1, 5*mm))
            story.append(KeepTogether(issue_elements))
            
    else:
        story.append(Paragraph("📌 주요 발견사항", styles["SectionTitle"]))
        story.append(Paragraph("✅ 특별한 위험 요소가 발견되지 않았습니다.", styles["Body"]))
        story.append(Spacer(1, 3*mm))

    story.append(Spacer(1, 5*mm))

    # ==================================================================================
    # 계약 정보 요약
    # ==================================================================================
    story.append(Paragraph("📝 계약 핵심 정보", styles["SectionTitle"]))
    
    extracted = context.get("extracted_fields") or {}
    
    def safe_get_value(field_data, *keys):
        """필드에서 안전하게 값 추출"""
        if not field_data:
            return None
        
        if isinstance(field_data, dict):
            if "value" in field_data:
                val = field_data["value"]
                if isinstance(val, dict) and keys:
                    for key in keys:
                        if isinstance(val, dict):
                            val = val.get(key)
                        else:
                            return None
                    return val
                return val
            elif keys:
                val = field_data
                for key in keys:
                    if isinstance(val, dict):
                        val = val.get(key)
                    else:
                        return None
                return val
            return field_data
        return field_data
    
    rent = extracted.get("rent", {})
    deposit = safe_get_value(rent, "deposit")
    monthly_rent = safe_get_value(rent, "monthly_rent")

    period = extracted.get("period", {})
    start_date = safe_get_value(period, "start")
    end_date = safe_get_value(period, "end")

    address = extracted.get("address", {})
    address_value = safe_get_value(address)
    if address_value and not isinstance(address_value, str):
        address_value = str(address_value)
    
    conf_date = extracted.get("confirmation_date", {})
    contract_type_val = safe_get_value(extracted.get("contract_type"))
    conf_value = safe_get_value(conf_date)
    if conf_value and not isinstance(conf_value, str):
        conf_value = str(conf_value)

    info_data = [
        ["계약 유형", _format_contract_type(contract_type_val)],
        ["보증금", _format_number(deposit)],
        ["월세", _format_number(monthly_rent)],
        ["계약 기간", f"{_format_date(start_date)} ~ {_format_date(end_date)}"],
        ["소재지", address_value if address_value else "미기재"],
        ["확정일자", conf_value if conf_value else "미기재"],
    ]
    
    story.append(_create_info_table(info_data, font_name))
    story.append(Spacer(1, 8*mm))

    # ==================================================================================
    # 나머지 이슈 (상세 분석)
    # ==================================================================================
    if len(issues) > 3:
        story.append(PageBreak())
        story.append(Paragraph("📄 추가 발견사항 (전체)", styles["SectionTitle"]))
        story.append(Spacer(1, 3*mm))
        
        for idx, issue in enumerate(issues[3:], 4):
            severity = (issue.get("severity") or "MED").upper()
            message = issue.get("title") or issue.get("message") or "이슈"
            reasons = issue.get("reasons") or []
            
            story.append(Paragraph(f"{idx}. {message}", styles["BodyBold"]))
            
            # 등급 표시
            level_map = {"critical": "위험", "warning": "주의", "safe": "양호"}
            level_str = level_map.get(issue.get('level'), issue.get('level', ''))
            info_line = f"중요도: {severity}" + (f" | 등급: {level_str}" if level_str else "")
            story.append(Paragraph(info_line, styles["Small"]))
            
            # 상세 내용
            if reasons:
                for reason in reasons:
                    story.append(Paragraph(f"  • {reason}", styles["Body"]))
            
            # 가이드 내용 간략 표시
            guide = issue.get("guide")
            if guide:
                if guide.get("caution"):
                    story.append(Paragraph(f"  ⚠️ {guide['caution']}", styles["Small"]))
                if guide.get("action"):
                    # 첫 번째 대처법만 간략히
                    action1 = guide["action"][0] if isinstance(guide["action"], list) and guide["action"] else str(guide["action"])
                    story.append(Paragraph(f"  💡 {action1}", styles["Small"]))

            story.append(Spacer(1, 4*mm))

    # ==================================================================================
    # 푸터
    # ==================================================================================
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph(
        "본 리포트는 AI 기술을 활용하여 생성된 참고 자료입니다. 법적 효력이 없으며, 정확한 판단을 위해서는 법률 전문가와 상담하시기 바랍니다.",
        styles["Small"]
    ))

    # 빌드
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
