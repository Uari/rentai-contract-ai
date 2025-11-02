
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.pipelines.analyze_pipeline import analyze_pdf_bytes

router = APIRouter(tags=["analyze"])

@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF만 업로드 해주세요.")
    content = await file.read()
    result = await analyze_pdf_bytes(content, filename=file.filename)
    return result
