# frontend/app.py  (대부분 교체해도 OK)
import io, requests, json
import streamlit as st

API = st.secrets.get("API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="전세계약서 분석", layout="wide")

# ---- 작은 CSS로 배지/표 단정히
st.markdown("""
<style>
.badge {display:inline-block;padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600;color:white;}
.badge.high {background:#d92d20;}
.badge.med  {background:#f59e0b;}
.badge.low  {background:#16a34a;}
.small-muted{color:#6b7280;font-size:12px}
.kv-key {width:180px;color:#374151;font-weight:600}
.kv-val {color:#111827}
.card {border:1px solid #e5e7eb;padding:14px;border-radius:10px;background:#fff}
h3 {margin-top:0.6rem}
</style>
""", unsafe_allow_html=True)

st.title("임대차 계약서 분석")

col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("1) 파일 업로드")
    file = st.file_uploader("PDF 업로드", type=["pdf"])
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
        # --- 상단 요약 카드
        s = data["summary"]
        st.markdown(f"""
<div class="card">
  <div style="display:flex;gap:32px;flex-wrap:wrap">
    <div><div class="small-muted">파일명</div><div class="kv-val">{s['filename']}</div></div>
    <div><div class="small-muted">페이지</div><div class="kv-val">{s['pages']}</div></div>
    <div><div class="small-muted">표 검출</div><div class="kv-val">{s['tables']}</div></div>
    <div><div class="small-muted">서명 검출</div><div class="kv-val">{s['signatures']}</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

        st.divider()

        # --- 필드 요약(2열)
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

        # --- 이슈(배지 + 테이블)
        st.markdown("### 위험/주의 이슈")
        if not data["issues"]:
            st.success("발견된 이슈가 없습니다.")
        else:
            def badge(sev):
                s = sev.lower()
                return f'<span class="badge {{"high":"high","med":"med"}.get(s,"low")}">{sev}</span>'
            rows = []
            for it in data["issues"]:
                rows.append([
                    it["code"],
                    badge(it["severity"]),
                    it["message"],
                    len(it.get("evidence", [])),
                ])
            st.markdown("""<div class="card">""", unsafe_allow_html=True)
            st.markdown("| 코드 | 심각도 | 메시지 | 근거수 |\n|---|---|---|---|", unsafe_allow_html=True)
            for r in rows:
                st.markdown(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

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
