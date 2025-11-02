
from typing import Dict, Any
from app.services.parser_pdf.simple_parser import pdf_bytes_to_pages_text, naive_extract_fields
from app.models.contract_schema import LeaseDoc
from app.services.rule_engine.loader import load_rules
from app.services.rule_engine.checker import run_rules
from app.services.anomaly.simple import anomaly_score
from app.services.report.summary import make_summary

async def analyze_pdf_bytes(pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
    pages = pdf_bytes_to_pages_text(pdf_bytes)
    extracted = naive_extract_fields(pages)
    doc = LeaseDoc(**extracted)

    rules = load_rules()
    issues = run_rules(doc, rules)
    score = anomaly_score(doc)

    issues_lines = [f"- [{i['severity']}] {i['code']}: {i['msg']} / 근거: {i['evidence']}" for i in issues]
    issues_lines.append(f"- [SCORE] anomaly={score:.2f}")
    summary = make_summary("\n".join(issues_lines))

    return {
        "file": filename,
        "status": "ok",
        "risk_score": score,
        "issues": issues,
        "summary": summary,
        "doc": doc.model_dump()
    }
