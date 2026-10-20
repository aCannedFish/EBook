"""核对实际模型生成的两轮规范及其与原书城的分页、类型、鉴权约束。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python-assistant"))
from backend.api_design import validate_contract


def main() -> None:
    for number in [1, 2]:
        path = ROOT / f"docs/assignments/hw1/openapi-round-{number}.json"
        result = validate_contract(json.loads(path.read_text(encoding="utf-8")))
        print(f"第{number}轮通过 OpenAPI 3.0.3 及书城契约约束校验：{result}")


if __name__ == "__main__":
    main()
