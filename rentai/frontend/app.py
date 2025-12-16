# frontend/app.py  (대부분 교체해도 OK)
import io, requests, json
import streamlit as st

API = st.secrets.get("API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="전세계약서 분석", layout="wide")

# ---- 글로벌 스타일 & 헬퍼
st.markdown("""
<style>
.card{border:1px solid #e5e7eb;border-radius:12px;padding:16px;background:#fff;box-shadow:0 2px 6px rgba(15,23,42,.05);}
.small-muted{color:#6b7280;font-size:12px;}
.kv-val{font-size:17px;font-weight:600;color:#111827;}
.badge{display:inline-flex;align-items:center;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600;color:#fff;}
.badge.high{background:#dc2626;}
.badge.med{background:#f97316;}
.badge.low{background:#059669;}
.risk-card{padding:18px;border-left:6px solid var(--risk-color);background:var(--risk-bg);border-radius:12px;margin-bottom:18px;}
.risk-title{font-size:20px;font-weight:700;margin-bottom:6px;display:flex;align-items:center;gap:8px;}
.risk-desc{color:#374151;font-size:14px;margin-bottom:6px;}
.risk-meta{color:#6b7280;font-size:13px;}
.summary-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:18px;}
.summary-item{background:#f9fafb;border-radius:10px;padding:12px;}
.summary-item h4{margin:0;font-size:13px;color:#6b7280;}
.summary-item p{margin:4px 0 0;font-weight:600;color:#111827;font-size:18px;}
.issue-highlight{border-left:4px solid #e5e7eb;padding-left:12px;margin-bottom:16px;}
.issue-meta{font-size:12px;color:#6b7280;margin-top:4px;}
.issue-chip{display:inline-flex;align-items:center;padding:2px 8px;border-radius:8px;font-size:11px;font-weight:600;}
.chip-critical{background:#fee2e2;color:#b91c1c;}
.chip-warning{background:#fef3c7;color:#b45309;}
.chip-safe{background:#d1fae5;color:#065f46;}
.detail-issue-card{border:1px solid #e5e7eb;border-radius:14px;padding:18px;margin-bottom:12px;background:#fff;box-shadow:0 2px 6px rgba(15,23,42,.04);}
.detail-issue-title{font-size:17px;font-weight:600;color:#0f172a;display:flex;align-items:center;justify-content:space-between;gap:10px;}
.detail-issue-meta{font-size:12px;color:#6b7280;margin-top:4px;display:flex;gap:12px;flex-wrap:wrap;}
.detail-issue-body{font-size:12px;color:#475467;line-height:1.5;margin-top:10px;}
.issue-list{margin:6px 0 0 0;padding-left:18px;}
.issue-list li{font-size:12px;margin-bottom:4px;color:#111827;}
</style>
""", unsafe_allow_html=True)

RISK_UI = {
    "critical": {"label": "위험", "icon": "🚨", "color": "#dc2626", "bg": "#fef2f2",
                 "desc": "즉시 조치가 필요한 항목이 있습니다."},
    "warning": {"label": "주의", "icon": "⚠️", "color": "#f97316", "bg": "#fff7ed",
                "desc": "주의가 필요한 항목이 있습니다."},
    "safe": {"label": "양호", "icon": "✅", "color": "#16a34a", "bg": "#ecfccb",
             "desc": "특별한 위험이 발견되지 않았습니다."}
}

CONTRACT_LABEL = {"jeonse": "전세", "wolse": "월세"}
SEVERITY_LABEL = {"HIGH": "높음", "MED": "보통", "LOW": "낮음"}

def get_risk_ui(level: str):
    return RISK_UI.get(level or "safe", RISK_UI["safe"])

def format_contract_type(value):
    if not value:
        return "미기재"
    return CONTRACT_LABEL.get(str(value).lower(), str(value))

st.title("임대차 계약서 분석")

col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("1) 파일 업로드")
    file = st.file_uploader("PDF/이미지 업로드", type=["pdf", "jpg", "jpeg", "png", "bmp", "tiff", "tif"])
    k = st.slider("근거 검색 k", 1, 8, 3)
    run = st.button("분석 실행", type="primary", use_container_width=True)

    result_json = None
    if run and file:
        with st.spinner("분석중..."):
            files = {"file": (file.name, file.getvalue(), "application/pdf")}
            r = requests.post(f"{API}/analyze/pdf", files=files, params={"k": k}, timeout=120)
            r.raise_for_status()
            result_json = r.json()
            st.session_state["result"] = result_json
            st.session_state["uploaded_file"] = file  # PDF 리포트 생성을 위해 파일 저장
            st.success("분석 완료")

with col_right:
    st.subheader("2) 결과")
    data = st.session_state.get("result")
    if not data:
        st.info("분석을 실행하면 결과가 여기에 표시됩니다.")
    else:
        risk_info = data.get("risk", {})
        risk_meta = get_risk_ui(risk_info.get("level", "safe"))
        risk_issues = risk_info.get("issues") or data.get("issues", [])
        issue_count = len(risk_issues)
        extracted = data.get("extracted_fields", {})
        contract_value = extracted.get("contract_type", {}).get("value")
        contract_label = format_contract_type(contract_value)

        st.markdown(f"""
            <div class="risk-card" style="--risk-color:{risk_meta['color']};--risk-bg:{risk_meta['bg']}">
            <div class="risk-title">{risk_meta['icon']} {risk_meta['label']}</div>
            <div class="risk-desc">{risk_meta['desc']}</div>
            <div class="risk-meta">감지된 이슈 {issue_count}건 · 총 점수 {risk_info.get("total_score", 0)}</div>
            </div>
            """, unsafe_allow_html=True)

        s = data.get("summary", {})
        summary_items = [
            ("파일명", s.get("filename", "-")),
            ("계약 유형", contract_label),
            ("페이지 수", s.get("pages", "-")),
            ("표 검출", s.get("tables", "-")),
            ("서명/날인", "있음" if s.get("signatures") else "없음"),
        ]
        grid_html = "<div class='summary-grid'>"
        for label, value in summary_items:
            grid_html += f"<div class='summary-item'><h4>{label}</h4><p>{value}</p></div>"
        grid_html += "</div>"
        st.markdown(grid_html, unsafe_allow_html=True)

        st.markdown("### 핵심 필드")
        cols = st.columns(2)
        for i, f in enumerate(data["fields"]):
            with cols[i % 2]:
                st.markdown(f"""
<div class="card">
  <div class="small-muted">{f['label']}</div>
  <div class="kv-val">{f.get('value') or '—'}</div>
</div>
""", unsafe_allow_html=True)

        st.divider()

        st.markdown("### 📌 주요 이슈 (TOP 3)")
        if not risk_issues:
            st.success("발견된 이슈가 없습니다.")
        else:
            top_issues = risk_issues[:3]
            for idx, issue in enumerate(top_issues, 1):
                level = (issue.get("level") or "warning").lower()
                level_label = get_risk_ui(level)["label"]
                chip_class = {"critical": "chip-critical", "warning": "chip-warning", "safe": "chip-safe"}.get(level, "chip-warning")
                severity = SEVERITY_LABEL.get((issue.get("severity") or "MED").upper(), "보통")
                title = issue.get("title") or issue.get("message") or issue.get("code") or "이슈"
                reasons = issue.get("reasons", [])
                st.markdown(f"""
<div class="card issue-highlight">
  <div class="issue-title">{idx}. {title}</div>
  <div class="issue-meta">
    <span class="issue-chip {chip_class}">{level_label}</span>
    <span class="small-muted">중요도 {severity}</span>
  </div>
  {"".join([f"<div>- {r}</div>" for r in reasons[:3]]) or "<div class='small-muted'>상세 내용은 아래 전체 이슈에서 확인하세요.</div>"}
</div>
""", unsafe_allow_html=True)

        st.markdown("### 📄 상세 이슈 (전체)")
        if not risk_issues:
            st.info("등록된 이슈가 없습니다.")
        else:
            for idx, issue in enumerate(risk_issues, 1):
                title = issue.get("title") or issue.get("message") or issue.get("code") or "이슈"
                level = (issue.get("level") or "warning").lower()
                level_meta = get_risk_ui(level)
                severity = SEVERITY_LABEL.get((issue.get("severity") or "MED").upper(), "보통")
                reasons = issue.get("reasons") or []
                refs = issue.get("references") or []
                chip_class = {"critical": "chip-critical", "warning": "chip-warning", "safe": "chip-safe"}.get(level, "chip-warning")
                
                # 가이드 검색 (LLM이 생성한 가이드 우선 사용)
                guide = issue.get("guide")

                reason_html = ""
                if reasons:
                    reason_items = "".join(f"<li>{r}</li>" for r in reasons)
                    reason_html = f"""
<div class="detail-issue-body">
  <div class="small-muted">감지된 문제</div>
  <ul class="issue-list">{reason_items}</ul>
</div>
"""
                
                # 가이드가 있으면 가이드 HTML 생성
                guide_html = ""
                if guide:
                    action_items = "".join(f"<li>{a}</li>" for a in guide.get('action', []))
                    guide_html = f"""
<div style="margin-top:12px; padding-top:12px; border-top:1px dashed #e5e7eb;">
    <div style="margin-bottom:10px;">
        <strong style="color:#b45309; font-size:13px;">⚠️ 주의사항</strong>
        <div style="font-size:13px; color:#374151; margin-top:4px; line-height:1.5;">{guide.get('caution', '')}</div>
    </div>
    <div style="margin-bottom:8px;">
        <strong style="color:#047857; font-size:13px;">💡 대처 방법</strong>
        <ul class="issue-list" style="margin-top:4px;">{action_items}</ul>
    </div>
</div>
"""

                # 법적 근거 처리 (가이드에 법적 근거가 있으면 그것을 우선 사용)
                ref_html = ""
                if guide and guide.get("law"):
                    # 가이드의 법적근거는 간단하게 표시
                    ref_html = f"""
<div class="detail-issue-body" style="margin-top:12px; background:#f9fafb; padding:10px; border-radius:8px;">
  <div class="small-muted" style="margin-bottom:4px;">관련 법적 근거</div>
  <div style="font-size:12px; color:#4b5563; line-height:1.5;">{guide['law']}</div>
</div>
"""
                elif refs:
                    # RAG 결과를 깔끔하게 포맷팅 (전체 내용 표시, 생략 없음)
                    import re
                    def format_rag_reference(ref):
                        source = ref.get('source', '')
                        text = ref.get('text', '')
                        
                        # 파일 경로 제거 (data\embeddings\... 형식)
                        if '\\' in source or '/' in source:
                            source = ''
                        
                        # 텍스트에서 마크다운 제거 및 정리
                        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
                        text = re.sub(r'^\*\s*', '', text, flags=re.MULTILINE)
                        text = text.strip()
                        
                        # 법 조항명 추출
                        law_match = re.search(r'(주택임대차보호법\s*)?제?\d+조(의\d+)?', text)
                        if law_match:
                            law_name = law_match.group(0)
                            explanation = text[law_match.end():].strip()
                            explanation = re.sub(r'^[:\-\(\)\s]+', '', explanation)
                            
                            # 전체 내용 표시 (생략 없음)
                            if explanation:
                                return f'<div style="margin-bottom:12px;"><strong style="color:#2563eb; font-size:13px;">{law_name}</strong><div style="color:#6b7280; font-size:12px; margin-top:4px; line-height:1.6;">{explanation}</div></div>'
                            else:
                                return f'<div style="margin-bottom:12px;"><strong style="color:#2563eb; font-size:13px;">{law_name}</strong></div>'
                        
                        # 법 조항명이 없으면 텍스트 전체 표시
                        if text and not source:
                            return f'<div style="color:#6b7280; font-size:12px; line-height:1.6; margin-bottom:12px;">{text}</div>'
                        return None
                    
                    formatted_refs = [format_rag_reference(ref) for ref in refs if format_rag_reference(ref)]
                    if formatted_refs:
                        # 첫 번째는 전체 표시, 나머지는 토글로
                        first_html = formatted_refs[0]
                        
                        # 나머지가 있으면 토글로 표시
                        if len(formatted_refs) > 1:
                            other_refs_html = "".join(formatted_refs[1:])
                            
                            ref_html = f"""
<div class="detail-issue-body" style="margin-top:12px; background:#f9fafb; padding:10px; border-radius:8px;">
  <div class="small-muted" style="margin-bottom:6px;">관련 법적 근거</div>
  <div style="font-size:12px; color:#4b5563; line-height:1.5;">
    {first_html}
    <details style="margin-top:8px;">
      <summary style="cursor:pointer; color:#2563eb; font-size:12px; font-weight:500; user-select:none; padding:4px 0;">더보기 ({len(formatted_refs)-1}개)</summary>
      <div style="margin-top:8px; padding-top:8px; border-top:1px solid #e5e7eb;">
        {other_refs_html}
      </div>
    </details>
  </div>
</div>
"""
                        else:
                            ref_html = f"""
<div class="detail-issue-body" style="margin-top:12px; background:#f9fafb; padding:10px; border-radius:8px;">
  <div class="small-muted" style="margin-bottom:6px;">관련 법적 근거</div>
  <div style="font-size:12px; color:#4b5563; line-height:1.5;">{first_html}</div>
</div>
"""

                st.markdown(
                    f"""
<div class="detail-issue-card">
  <div class="detail-issue-title">
    <span>{idx}. {title}</span>
    <span class="issue-chip {chip_class}">{level_meta['label']}</span>
  </div>
  <div class="detail-issue-meta">
    <span>중요도 {severity}</span>
    <span>룰 코드 {issue.get('code','-')}</span>
  </div>
  {reason_html or "<div class='detail-issue-body small-muted'>추가 설명이 없습니다.</div>"}
  {guide_html}
  {ref_html}
</div>
""",
                    unsafe_allow_html=True,
                )

        st.divider()

        # --- RAG 근거(아코디언)
        st.markdown("### 법적 근거 (RAG)")
        for i, ref in enumerate(data["rag"], 1):
            with st.expander(f"근거 {i} | {ref.get('source','unknown')} (score={ref.get('score'):0.3f})"):
                st.write(ref.get("text", ""))

        # --- PDF/JSON 다운로드
        c1, c2 = st.columns(2)
        with c1:
            if st.button("보고서(PDF) 다운로드", use_container_width=True):
                # 원본 파일을 다시 업로드하여 리포트 생성
                uploaded_file = st.session_state.get("uploaded_file") or file
                if uploaded_file is not None:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    pdf = requests.post(f"{API}/report/pdf", files=files, timeout=120)
                    pdf.raise_for_status()
                    st.download_button("다운로드", data=pdf.content, file_name="분석_리포트.pdf",
                                       mime="application/pdf", use_container_width=True)
                else:
                    st.warning("원본 파일이 없어 리포트를 생성할 수 없습니다.")
        with c2:
            st.download_button("원본 JSON 다운로드", data=json.dumps(data, ensure_ascii=False, indent=2),
                               file_name="analysis.json", mime="application/json", use_container_width=True)
