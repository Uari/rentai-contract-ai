
import streamlit as st
import requests, os

st.set_page_config(page_title="임대차 계약서 이상탐지", layout="wide")
st.title("임대차 계약서 이상탐지 (Prototype)")

backend_url = os.getenv("BACKEND_URL", "http://localhost:8000/api")

uploaded = st.file_uploader("PDF 업로드", type=["pdf"])
if st.button("분석 시작") and uploaded:
    files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
    with st.spinner("분석중..."):
        res = requests.post(f"{backend_url}/analyze", files=files, timeout=300)
    if res.ok:
        data = res.json()
        st.success("분석 완료")
        with st.expander("추출된 문서 스키마 보기"):
            st.json(data.get("doc", {}))
        st.subheader("요약 결과")
        st.write(data.get("summary", ""))
        st.subheader("이슈 목록")
        st.json(data.get("issues", []))
    else:
        st.error(res.text)
