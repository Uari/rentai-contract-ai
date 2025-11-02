
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.settings import settings

def get_gemini():
    if not settings.GEMINI_API_KEY:
        class Dummy:
            def invoke(self, prompt):
                class R:
                    content = "[검증 필요] GEMINI_API_KEY 미설정. 샘플 응답입니다.\n" + str(prompt)
                return R()
        return Dummy()
    return ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL, temperature=0, api_key=settings.GEMINI_API_KEY)
