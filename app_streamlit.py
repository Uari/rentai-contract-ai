# app_streamlit.py
import io
import json
import requests
import streamlit as st

st.set_page_config(page_title="임대차 계약서 분석 데모", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────────────────────────────────────
API_BASE_DEFAULT = "http://127.0.0.1:8000"
st.title("임대차 계약서 분석 (FastAPI + Streamlit)")

with st.sidebar:
    st.header("연결 설정")
    api_base = st.text_input("API Base URL", API_BASE_DEFAULT)
    st.caption("※ FastAPI 서버는 /health 로 응답해야 합니다.")

    if st.button("헬스 체크"):
        try:
            r = requests.get(f"{api_base}/health", timeout=5)
            if r.ok and r.json().get("status") == "ok":
                st.success("FastAPI 연결 OK")
            else:
                st.warning(f"상태 비정상: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"연결 실패: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 업로드
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("PDF 업로드")
uploaded = st.file_uploader("임대차 계약서 PDF", type=["pdf"])

col1, col2 = st.columns([1, 1])

with col1:
    if st.button("분석 실행", disabled=(uploaded is None)):
        if not uploaded:
            st.warning("PDF 파일을 업로드하세요.")
        else:
            files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
            with st.spinner("분석 중..."):
                try:
                    r = requests.post(f"{api_base}/analyze/pdf", files=files, timeout=120)
                except Exception as e:
                    st.error(f"요청 실패: {e}")
                    st.stop()

            if not r.ok:
                st.error(f"분석 실패: {r.status_code}\n{r.text}")
                st.stop()

            data = r.json()
            st.session_state["result"] = data
            st.success("분석 완료")

with col2:
    # 결과 JSON 다운로드
    if "result" in st.session_state:
        buf = io.BytesIO(json.dumps(st.session_state["result"], ensure_ascii=False, indent=2).encode("utf-8"))
        st.download_button("결과 JSON 다운로드", data=buf, file_name="analysis_result.json", mime="application/json")

# ─────────────────────────────────────────────────────────────────────────────
# 결과 표시
# ─────────────────────────────────────────────────────────────────────────────
if "result" in st.session_state:
    data = st.session_state["result"]

    st.markdown("### 개요")
    meta_cols = st.columns(6)
    meta_cols[0].metric("파일명", data.get("file"))
    meta_cols[1].metric("페이지수", data.get("page_count"))
    meta_cols[2].metric("문장수", data.get("sentence_count"))
    meta_cols[3].metric("표 검출", data.get("tables_found"))
    meta_cols[4].metric("서명 키워드", "Yes" if data.get("signature_detected") else "No")
    meta_cols[5].metric("크기(MB)", data.get("size_mb"))

    st.divider()

    # 추출 필드
    st.markdown("### 추출 필드 (스키마_v2)")
    extracted = data.get("extracted_fields", {})

    def show_field(title, node):
        val = None
        evid = []
        if isinstance(node, dict):
            # {"value": x, "evidence": [...]}
            val = node.get("value", node)
            evid = node.get("evidence", [])
        else:
            val = node

        st.markdown(f"**{title}**: `{val}`")
        if evid:
            with st.expander(f"{title} 근거 (상위 {len(evid)}개)"):
                for ev in evid:
                    st.write(f"- [{ev.get('id')}] (p{ev.get('page')}): {ev.get('text')}")

    show_field("확정일자", extracted.get("confirmation_date"))
    show_field("전입신고 여부", extracted.get("resident_reported"))
    show_field("관리비", extracted.get("maintenance_fee"))
    show_field("원상복구", extracted.get("restoration_clause"))
    show_field("위약 조항", extracted.get("termination_penalty"))

    st.divider()

    # 위험 이슈
    st.markdown("### 위험 이슈 (룰셋_v2)")
    risk = data.get("risk", {}) or {}
    issues = risk.get("issues", [])
    total_score = risk.get("total_score", 0)

    # 총점 뱃지
    def severity_color(sev: str):
        sev = (sev or "").upper()
        return {"HIGH": "🔴", "MED": "🟠", "LOW": "🟡"}.get(sev, "⚪")

    st.markdown(f"**총점:** `{total_score}`")
    if not issues:
        st.success("이상 탐지 없음")
    else:
        for it in issues:
            sev = it.get("severity", "LOW")
            icon = severity_color(sev)
            st.markdown(f"{icon} **[{it.get('code')}] {it.get('message')}**  *(severity: {sev})*")

    st.divider()

    # 미리보기 문장
    st.markdown("### 미리보기 문장 (상위 5개)")
    for s in (data.get("preview_sentences") or []):
        st.write(f"- [{s.get('id')}] (p{s.get('page')}): {s.get('text')}")
