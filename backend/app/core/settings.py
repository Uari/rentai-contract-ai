
import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    ENV: str = os.getenv("ENV", "local")
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    VECTOR_DIR: str = os.getenv("VECTOR_DIR", "vectorstore")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite") #gemini-2.5-flash-lite
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

settings = Settings()
