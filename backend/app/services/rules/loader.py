# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Tuple
import os, yaml

# rentai/<여기에서>/../../../rules/rules_v2.yml 로 기본 경로 계산
DEFAULT_RULES_PATH = os.path.join(
    os.path.dirname(__file__),                           # .../services/rules
    "..",                                                # .../services
    "..",                                                # .../app
    "..",                                                # .../backend
    "..",                                                # .../rentai
    "rules",
    "rules_v2.yml",
)

def load_rules(path: str | None = None) -> Tuple[int, List[Dict[str, Any]]]:
    """
    반환: (version, rules[])
    - YAML 최상단: {version: 2, rules: [...]}
    - 방어적으로 비-딕셔너리/누락 항목 제외
    """
    p = path or DEFAULT_RULES_PATH
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    version = 1
    rules_raw: List[Dict[str, Any]] = []

    if isinstance(data, dict):
        version = int(data.get("version") or 1)
        r = data.get("rules")
        if isinstance(r, list):
            rules_raw = r
    elif isinstance(data, list):
        # 구버전 호환(리스트가 바로 오는 경우)
        rules_raw = data

    cleaned: List[Dict[str, Any]] = []
    for item in rules_raw:
        if not isinstance(item, dict):
            continue
        # 최소 필수키: code, message, when(op 포함)
        w = item.get("when")
        if not (item.get("code") and item.get("message") and isinstance(w, dict) and w.get("op")):
            continue
        cleaned.append(item)

    return version, cleaned
