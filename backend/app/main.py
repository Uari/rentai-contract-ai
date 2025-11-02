
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import analyze, health, rules

app = FastAPI(title="RentAI Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")

@app.get("/")
def root():
    return {"ok": True, "service": "RentAI Backend"}
