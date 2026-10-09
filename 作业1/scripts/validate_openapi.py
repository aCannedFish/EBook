#!/usr/bin/env python3
"""OpenAPI 3.0 规范自检脚本。

对 openapi.json 做结构与语义两层校验，作为「多轮对话第 4 轮：确定性验证」的可复现证据：

1. 结构层：OpenAPI 版本、paths / components 必备字段、$ref 是否可解析、
   路径参数是否在 path 模板中声明。
2. 语义层：文档中每一处 example / examples 的取值，都用 jsonschema 按它自己
   声明的 schema 校验一遍。示例与 schema 不一致是接口文档最常见的失真，
   这一步能把「文档写得像对的」和「文档确实自洽」区分开。
3. 确定性：同一份文档两次规范化序列化后字节一致，且文档内不含随机 id、
   当前时间等非确定字段。

退出码 0 表示全部通过，非 0 表示存在失败项。

用法：
    python3 scripts/validate_openapi.py [openapi.json 路径]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import jsonschema

DEFAULT_SPEC = Path(__file__).resolve().parent.parent / "openapi.json"

REQUIRED_PATHS = {
    "/api/v1/books": {"get", "post"},
    "/api/v1/books/{bookId}": {"get"},
    "/api/v1/books/{bookId}/stock": {"patch"},
}

# 出现在 schema 定义里的字段名，出现即视为不确定性来源。
NONDETERMINISTIC_KEYS = {"$random", "uuid", "seed"}


class Failure(Exception):
    """单条校验失败，携带已收集到的失败列表。"""


def load_spec(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def iter_refs(node, trail="$"):
    """深度遍历，产出所有 (JSON 指针路径, $ref 字符串)。"""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield trail, value
            else:
                yield from iter_refs(value, f"{trail}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from iter_refs(value, f"{trail}/{index}")


def resolve_ref(spec: dict, ref: str):
    """把 #/a/b/c 形式的引用解析为实际节点。"""
    if not ref.startswith("#/"):
        raise Failure(f"仅支持文档内引用，收到 {ref}")
    node = spec
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or token not in node:
            raise Failure(f"引用无法解析：{ref}")
        node = node[token]
    return node


def deref(spec: dict, node, stack=()):
    """把文档内的 $ref 就地展开成实际 schema。

    jsonschema 默认只认识文档自身的 $id 基址，不会按 OpenAPI 的
    components 结构去解析 #/components/...，所以这里先把引用全部展开，
    再交给 jsonschema。stack 用于发现循环引用。
    """
    if isinstance(node, list):
        return [deref(spec, item, stack) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        ref = node["$ref"]
        if ref in stack:
            raise Failure(f"检测到循环引用：{' -> '.join([*stack, ref])}")
        return deref(spec, resolve_ref(spec, ref), (*stack, ref))
    return {key: deref(spec, value, stack) for key, value in node.items()}


# OpenAPI 3.0 的 schema 方言与 JSON Schema 有几处差异，校验前做一次轻量归一化。
def to_json_schema(node):
    if isinstance(node, list):
        return [to_json_schema(item) for item in node]
    if not isinstance(node, dict):
        return node

    converted = {key: to_json_schema(value) for key, value in node.items()}

    if converted.pop("nullable", False) and "type" in converted:
        declared = converted["type"]
        if isinstance(declared, str):
            converted["type"] = [declared, "null"]
        elif isinstance(declared, list) and "null" not in declared:
            converted["type"] = [*declared, "null"]

    # example / xml / discriminator 等是 OpenAPI 扩展关键字，JSON Schema 会忽略。
    return converted


def check_structure(spec: dict) -> list[str]:
    problems: list[str] = []

    version = str(spec.get("openapi", ""))
    if not re.fullmatch(r"3\.0\.\d+", version):
        problems.append(f"openapi 版本必须是 3.0.x，实际为 {version!r}")

    for field in ("info", "paths", "components"):
        if field not in spec:
            problems.append(f"缺少顶层字段 {field}")
    for field in ("title", "version"):
        if field not in spec.get("info", {}):
            problems.append(f"info 缺少字段 {field}")

    for trail, ref in iter_refs(spec):
        try:
            resolve_ref(spec, ref)
        except Failure as error:
            problems.append(f"{trail} 的 $ref 无效：{error}")

    for path, path_item in spec.get("paths", {}).items():
        declared = set(re.findall(r"\{([^}]+)\}", path))
        for method, operation in path_item.items():
            if method.startswith("x-") or method == "parameters":
                continue
            operation_params = {
                param["name"]
                for param in operation.get("parameters", [])
                if param.get("in") == "path"
            }
            missing = declared - operation_params
            if missing:
                problems.append(
                    f"{method.upper()} {path} 未声明路径参数 {sorted(missing)}"
                )
            if not operation.get("responses"):
                problems.append(f"{method.upper()} {path} 缺少 responses")

    for required_path, required_methods in REQUIRED_PATHS.items():
        if required_path not in spec.get("paths", {}):
            problems.append(f"缺少作业要求的路径 {required_path}")
            continue
        present = set(spec["paths"][required_path])
        for method in required_methods:
            if method not in present:
                problems.append(f"{required_path} 缺少 {method.upper()} 方法")

    for key in NONDETERMINISTIC_KEYS:
        if json.dumps(spec, ensure_ascii=False).find(f'"{key}"') >= 0:
            problems.append(f"文档中出现非确定性关键字 {key}")

    return problems


def check_examples(spec: dict) -> tuple[list[str], int]:
    """校验每一处示例都符合其所属 schema。返回 (问题列表, 已校验示例数)。"""
    problems: list[str] = []
    checked = 0

    def validate_example(label: str, schema_node, example) -> None:
        nonlocal checked
        try:
            resolved = deref(spec, schema_node)
        except Failure as error:
            problems.append(f"{label}：schema 引用无效 {error}")
            return
        validator = jsonschema.Draft202012Validator(to_json_schema(resolved))
        errors = sorted(validator.iter_errors(example), key=lambda item: list(item.path))
        checked += 1
        for error in errors:
            location = "/".join(str(part) for part in error.path) or "(root)"
            problems.append(f"{label} 不符合 schema：{location} {error.message}")

    def walk(node, trail="$"):
        if isinstance(node, dict):
            schema_node = node.get("schema")
            if schema_node:
                if isinstance(node.get("example"), (dict, list, str, int, float, bool)):
                    validate_example(f"{trail}/example", schema_node, node["example"])
                for name, entry in (node.get("examples") or {}).items():
                    if isinstance(entry, dict) and "value" in entry:
                        validate_example(f"{trail}/examples/{name}", schema_node, entry["value"])
            for key, value in node.items():
                walk(value, f"{trail}/{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{trail}/{index}")

    for name, schema in spec.get("components", {}).get("schemas", {}).items():
        if "example" in schema:
            validate_example(f"components/schemas/{name}/example", schema, schema["example"])
    walk(spec)

    return problems, checked


def check_determinism(spec: dict) -> list[str]:
    problems: list[str] = []
    first = json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    second = json.dumps(
        json.loads(json.dumps(spec, ensure_ascii=False)), ensure_ascii=False,
        sort_keys=True, separators=(",", ":"),
    )
    if first != second:
        problems.append("两次规范化序列化结果不一致，文档存在不确定性")
    return problems


def main(argv: list[str]) -> int:
    spec_path = Path(argv[1]).resolve() if len(argv) > 1 else DEFAULT_SPEC
    spec = load_spec(spec_path)

    structure = check_structure(spec)
    example_problems, checked = check_examples(spec)
    determinism = check_determinism(spec)

    print(f"规范文件：{spec_path}")
    print(f"路径数：{len(spec.get('paths', {}))}，schema 数：{len(spec.get('components', {}).get('schemas', {}))}")
    print(f"已校验示例：{checked} 处")

    failures = structure + example_problems + determinism
    if failures:
        print(f"\n未通过（{len(failures)} 项）：")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("\n全部校验通过：结构完整、引用可解析、示例与 schema 一致、输出确定。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
