"""app_streamlit.py
⚠️ 이 화면은 로컬 점검용 서브 UI 입니다. (메인: frontend/app.py)
"""
import json
import requests
import streamlit as st

st.set_page_config(page_title="임대차 계약서 분석 데모", layout="wide")

API_BASE_DEFAULT = "http://127.0.0.1:8000"

# ─────────────────────────────────────────────────────────────────────────────
# 글로벌 스타일 & 헬퍼
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
body {background:#f4f6fb;}
.card{border:1px solid #e5e7eb;border-radius:12px;padding:16px;background:#fff;box-shadow:0 2px 6px rgba(15,23,42,.05);}
.small-muted{color:#6b7280;font-size:12px;}
.kv-val{font-size:17px;font-weight:600;color:#111827;}
.risk-card{padding:18px;border-left:6px solid var(--risk-color);background:var(--risk-bg);border-radius:12px;margin-bottom:18px;}
.risk-title{font-size:20px;font-weight:700;margin-bottom:6px;display:flex;align-items:center;gap:8px;}
.risk-desc{color:#374151;font-size:14px;margin-bottom:6px;}
.risk-meta{color:#6b7280;font-size:13px;}
.summary-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:18px;}
.summary-item{background:#f9fafb;border-radius:10px;padding:12px;}
.summary-item h4{margin:0;font-size:13px;color:#6b7280;}
.summary-item p{margin:4px 0 0;font-weight:600;color:#111827;font-size:18px;}
.issue-highlight{border-left:4px solid #e5e7eb;padding-left:12px;margin-bottom:16px;}
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
""",
    unsafe_allow_html=True,
)

RISK_UI = {
    "critical": {"label": "위험", "icon": "🚨", "color": "#dc2626", "bg": "#fef2f2", "desc": "즉시 조치가 필요합니다."},
    "warning": {"label": "주의", "icon": "⚠️", "color": "#f97316", "bg": "#fff7ed", "desc": "주의가 필요한 항목이 있습니다."},
    "safe": {"label": "양호", "icon": "✅", "color": "#16a34a", "bg": "#ecfccb", "desc": "특별한 위험이 발견되지 않았습니다."},
}

CONTRACT_LABEL = {"jeonse": "전세", "wolse": "월세"}
SEVERITY_LABEL = {"HIGH": "높음", "MED": "보통", "LOW": "낮음"}


def get_risk_ui(level: str):
    return RISK_UI.get((level or "safe").lower(), RISK_UI["safe"])


def format_contract_type(value):
    if not value:
        return "미기재"
    return CONTRACT_LABEL.get(str(value).lower(), str(value))


# ─────────────────────────────────────────────────────────────────────────────
# 사이드바: 연결 설정
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("연결 설정")
    api_base = st.text_input("API Base URL", API_BASE_DEFAULT)
    st.caption("FastAPI 서버 주소 (예: http://127.0.0.1:8000)")
    if st.button("헬스 체크"):
        try:
            r = requests.get(f"{api_base}/health", timeout=5)
            if r.ok and r.json().get("status") == "ok":
                st.success("FastAPI 연결 OK")
            else:
                st.warning(f"상태 비정상: {r.status_code} / {r.text}")
        except Exception as e:
            st.error(f"연결 실패: {e}")

st.title("임대차 계약서 분석 (데모 UI)")

col_left, col_right = st.columns([1, 2])

# ─────────────────────────────────────────────────────────────────────────────
# 좌측: 업로드 & 실행
# ─────────────────────────────────────────────────────────────────────────────
with col_left:
    st.subheader("1) 파일 업로드")
    uploaded_file = st.file_uploader(
        "PDF / 이미지 업로드",
        type=["pdf", "jpg", "jpeg", "png", "bmp", "tif", "tiff"],
    )
    k = st.slider("법적 근거 검색 개수 (k)", 1, 8, 3)
    run = st.button("분석 실행", type="primary", use_container_width=True)

    if run:
        if not uploaded_file:
            st.warning("먼저 파일을 업로드하세요.")
        else:
            file_bytes = uploaded_file.getvalue()
            mime = uploaded_file.type or "application/octet-stream"
            files = {"file": (uploaded_file.name, file_bytes, mime)}
            with st.spinner("분석 중..."):
                try:
                    resp = requests.post(
                        f"{api_base}/analyze/pdf", files=files, params={"k": k}, timeout=180
                    )
                    resp.raise_for_status()
                except Exception as exc:
                    st.error(f"분석 실패: {exc}")
                    st.stop()

            st.session_state["result"] = resp.json()
            st.session_state["uploaded_file"] = uploaded_file
            st.success("분석 완료")

    if "result" in st.session_state:
        st.download_button(
            "결과 JSON 다운로드",
            data=json.dumps(st.session_state["result"], ensure_ascii=False, indent=2),
            file_name="analysis_result.json",
            mime="application/json",
            use_container_width=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# 우측: 결과 요약 UI
# ─────────────────────────────────────────────────────────────────────────────
with col_right:
    st.subheader("2) 결과")
    data = st.session_state.get("result")
    if not data:
        st.info("분석을 실행하면 결과가 여기에 표시됩니다.")
    else:
        risk_info = data.get("risk", {}) or {}
        risk_meta = get_risk_ui(risk_info.get("level", "safe"))
        risk_issues = risk_info.get("issues") or data.get("issues", [])
        issue_count = len(risk_issues)
        extracted = data.get("extracted_fields", {})
        contract_value = extracted.get("contract_type", {}).get("value")
        contract_label = format_contract_type(contract_value)

        st.markdown(
            f"""
<div class="risk-card" style="--risk-color:{risk_meta['color']};--risk-bg:{risk_meta['bg']}">
  <div class="risk-title">{risk_meta['icon']} {risk_meta['label']}</div>
  <div class="risk-desc">{risk_meta['desc']}</div>
  <div class="risk-meta">감지된 이슈 {issue_count}건</div>
</div>
""",
            unsafe_allow_html=True,
        )

        summary = data.get("summary", {})
        summary_items = [
            ("파일명", summary.get("filename", "-")),
            ("계약 유형", contract_label),
            ("페이지 수", summary.get("pages", "-")),
            ("표 검출", summary.get("tables", "-")),
            ("서명/날인", "있음" if summary.get("signatures") else "없음"),
        ]
        grid_html = "<div class='summary-grid'>"
        for label, value in summary_items:
            grid_html += f"<div class='summary-item'><h4>{label}</h4><p>{value}</p></div>"
        grid_html += "</div>"
        st.markdown(grid_html, unsafe_allow_html=True)

        st.markdown("### 핵심 필드")
        fields = data.get("fields", [])
        cols = st.columns(2)
        for idx, field in enumerate(fields):
            value = field.get("value")
            display_value = "—" if value in (None, "", "None") else value
            with cols[idx % 2]:
                st.markdown(
                    f"""
<div class="card">
  <div class="small-muted">{field.get('label')}</div>
  <div class="kv-val">{display_value}</div>
</div>
""",
                    unsafe_allow_html=True,
                )

        st.divider()

        st.markdown("### 📌 주요 이슈 (TOP 3)")
        if not risk_issues:
            st.success("발견된 이슈가 없습니다.")
        else:
            top_issues = risk_issues[:3]
            for idx, issue in enumerate(top_issues, 1):
                level = (issue.get("level") or "warning").lower()
                severity = SEVERITY_LABEL.get((issue.get("severity") or "MED").upper(), "보통")
                title = issue.get("title") or issue.get("message") or issue.get("code") or "이슈"
                reasons = issue.get("reasons") or []
                chip_class = {
                    "critical": "chip-critical",
                    "warning": "chip-warning",
                    "safe": "chip-safe",
                }.get(level, "chip-warning")
                st.markdown(
                    f"""
<div class="card issue-highlight">
  <div class="issue-title">{idx}. {title}</div>
  <div class="issue-meta">
    <span class="issue-chip {chip_class}">{get_risk_ui(level)['label']}</span>
    <span class="small-muted">중요도 {severity}</span>
  </div>
  {"".join([f"<div>- {r}</div>" for r in reasons[:3]]) or "<div class='small-muted'>상세 내용은 아래 전체 이슈에서 확인하세요.</div>"}
</div>
""",
                    unsafe_allow_html=True,
                )

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
                chip_class = {
                    "critical": "chip-critical",
                    "warning": "chip-warning",
                    "safe": "chip-safe",
                }.get(level, "chip-warning")

                reason_html = ""
                if reasons:
                    reason_items = "".join(f"<li>{r}</li>" for r in reasons)
                    reason_html = f"""
<div class="detail-issue-body">
  <div class="small-muted">주요 근거</div>
  <ul class="issue-list">{reason_items}</ul>
</div>
"""

                ref_html = ""
                if refs:
                    ref_items = "".join(
                        f"<li><strong>{ref.get('source','근거')}</strong> - {ref.get('text','')}</li>"
                        for ref in refs
                    )
                    ref_html = f"""
<div class="detail-issue-body">
  <div class="small-muted">법적 근거</div>
  <ul class="issue-list">{ref_items}</ul>
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
  {ref_html}
</div>
""",
                    unsafe_allow_html=True,
                )

        st.divider()

        st.markdown("### 법적 근거 (RAG)")
        rag_refs = data.get("rag") or []
        if not rag_refs:
            st.info("연결된 법적 근거가 없습니다.")
        else:
            for idx, ref in enumerate(rag_refs, 1):
                with st.expander(f"근거 {idx} | {ref.get('source', 'unknown')} (score={ref.get('score', 0):0.3f})"):
                    st.write(ref.get("text", ""))

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            uploaded_obj = st.session_state.get("uploaded_file")
            if st.button("보고서(PDF) 다운로드", use_container_width=True, disabled=(uploaded_obj is None)):
                if not uploaded_obj:
                    st.warning("원본 파일이 없습니다.")
                else:
                    files = {
                        "file": (
                            uploaded_obj.name,
                            uploaded_obj.getvalue(),
                            uploaded_obj.type or "application/pdf",
                        )
                    }
                    with st.spinner("리포트 생성 중..."):
                        r = requests.post(f"{api_base}/report/pdf", files=files, timeout=180)
                        if r.ok:
                            st.download_button(
                                "다운로드",
                                data=r.content,
                                file_name="analysis_report.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                            )
                        else:
                            st.error(f"리포트 생성 실패: {r.status_code} / {r.text}")
        with c2:
            st.download_button(
                "원본 JSON 다운로드",
                data=json.dumps(data, ensure_ascii=False, indent=2),
                file_name="analysis.json",
                mime="application/json",
                use_container_width=True,
            )

