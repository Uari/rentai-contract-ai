# tools/eval_runner.py
import argparse, json, pathlib, traceback
from typing import Dict, Any
import sys

# 루트/rentai/backend 모듈 경로 추가
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))

from app.services.parser_pdf.enhanced_parser import parse_pdf
from app.services.parser_pdf.table_extractor import extract_tables
from app.services.parser_pdf.sign_detection import detect_signature
from app.services.extractors.lease_fields import extract_all
from app.services.rules.rule_engine import evaluate_rules

def analyze_pdf_path(pdf_path: pathlib.Path) -> Dict[str, Any]:
    pdf_bytes = pdf_path.read_bytes()
    parsed = parse_pdf(pdf_bytes)
    extracted = extract_all(parsed["text_full"], parsed["sentences"])
    try:
        tables = extract_tables(pdf_bytes)
    except Exception:
        tables = []
    try:
        signature = detect_signature(parsed["sentences"])
    except Exception:
        signature = False
    rules_path = str(ROOT / "rules" / "rules_v2.yml")
    extras = {"signature_detected": signature, "tables_found": len(tables)}
    risk = evaluate_rules(extracted, parsed["text_full"], extras, rules_path)
    return {
        "file": pdf_path.name,
        "page_count": parsed["page_count"],
        "sentence_count": parsed["sentence_count"],
        "tables_found": len(tables),
        "signature_detected": signature,
        "extracted_fields": extracted,
        "risk": risk,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf_dir", required=True, help="평가 대상 PDF 폴더 경로")
    ap.add_argument("--out", default=str(ROOT / "eval" / "report.json"))
    args = ap.parse_args()

    pdf_dir = pathlib.Path(args.pdf_dir)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    stats = {"files":0, "issues":0, "score_total":0, "by_severity":{"LOW":0,"MED":0,"HIGH":0}}
    for p in sorted(pdf_dir.glob("*.pdf")):
        try:
            r = analyze_pdf_path(p)
            results.append(r)
            stats["files"] += 1
            stats["score_total"] += r["risk"].get("total_score", 0)
            for it in r["risk"].get("issues", []):
                stats["issues"] += 1
                sev = it.get("severity","LOW").upper()
                stats["by_severity"][sev] = stats["by_severity"].get(sev,0)+1
        except Exception as e:
            results.append({"file": p.name, "error": str(e), "trace": traceback.format_exc()})

    report = {"dir": str(pdf_dir), "summary": stats, "results": results}
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] saved -> {out_path}")

if __name__ == "__main__":
    main()
