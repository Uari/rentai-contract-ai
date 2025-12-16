
# from langchain.prompts import PromptTemplate
from langchain_core.prompts import PromptTemplate
from app.services.llm.gemini_wrapper import get_gemini

from app.core.settings import settings
print(f"[Gemini] Using model -> {settings.GEMINI_MODEL}")

tmpl = PromptTemplate.from_template("""
다음의 계약 위험 항목을 한국 임대차 기준으로 요약하세요.
각 항목은 '위험등급/이유/권장대응' 형태로 bullet로 작성.

[이슈 목록]
{issues_text}
""")

def make_summary(issues_text: str) -> str:
    llm = get_gemini()
    prompt = tmpl.format(issues_text=issues_text)
    return llm.invoke(prompt).content
