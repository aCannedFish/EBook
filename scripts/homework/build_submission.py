"""按作业拆分自编文件，并为同一书城保存一份可构建的源码快照。

只遍历明确列出的源码、配置和证据目录；不收集虚拟环境、依赖、编译产物、
本机配置或模型权重。每份压缩包内附逐文件 SHA-256 清单。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "deliverables"
STUDENT = "524031910113"
EXCLUDED = {"__pycache__", ".pytest_cache", ".index", ".DS_Store", "node_modules", "target", ".venv", ".git", ".tools"}
COMMON = ["run-all.sh", "stop-all.sh", "status-all.sh", "scripts/services.py"]
JAVA = ["springboot-ebook/src", "springboot-ebook/pom.xml", "springboot-ebook/run-local.sh", "springboot-ebook/stop-local.sh"]
PYTHON = ["python-assistant/backend", "python-assistant/data/policy.txt", "python-assistant/requirements.txt",
          "python-assistant/pytest.ini", "python-assistant/.env.example", "python-assistant/README.md",
          "python-assistant/run-local.sh", "python-assistant/stop-local.sh"]
FRONTEND = ["react-ebook/src", "react-ebook/public", "react-ebook/index.html", "react-ebook/package.json",
            "react-ebook/package-lock.json", "react-ebook/vite.config.js", "react-ebook/run-local.sh", "react-ebook/stop-local.sh"]


def collect(inputs: list[str]) -> dict[str, Path]:
    """保留原项目相对路径，使对应作业源码可以直接放回原书城。"""
    files = {}
    for name in inputs:
        source = ROOT / name
        if not source.exists():
            raise FileNotFoundError(source)
        for path in sorted(source.rglob("*")) if source.is_dir() else [source]:
            relative = path.relative_to(ROOT)
            if not path.is_file() or EXCLUDED.intersection(relative.parts):
                continue
            if path.name == ".env" or path.suffix in {".pyc", ".jar", ".class", ".war"}:
                continue
            files[str(relative)] = path
    return files


def write_archive(path: Path, files: dict[str, Path], texts: dict[str, str] | None = None) -> None:
    """存原始文件字节和可执行权限，并写入可离线校验的内容清单。"""
    manifest = []
    with ZipFile(path, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for name, source in sorted(files.items()):
            content = source.read_bytes()
            archive.write(source, name)
            manifest.append({"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
        for name, content in (texts or {}).items():
            archive.writestr(name, content.encode("utf-8"))
            manifest.append({"path": name, "bytes": len(content.encode()), "sha256": hashlib.sha256(content.encode()).hexdigest()})
        archive.writestr("MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    with ZipFile(path) as archive:
        assert archive.testzip() is None
        for entry in manifest:
            assert hashlib.sha256(archive.read(entry["path"])).hexdigest() == entry["sha256"]
    print(f"已生成 {path.name}，{len(manifest)} 个文件，{path.stat().st_size / 1024 / 1024:.2f} MiB")


def validate_images() -> None:
    """报告中的每张图必须能与浏览器原图及采集清单对应。"""
    records = json.loads((ROOT / "docs/assignments/browser-captures.json").read_text())["screenshots"]
    hashes = set()
    for record in records:
        digest = hashlib.sha256((ROOT / record["file"]).read_bytes()).hexdigest()
        assert digest == record["sha256"], record["file"]
        hashes.add(digest)
    for number in range(1, 5):
        with ZipFile(OUTPUT / f"{STUDENT}-作业{number}.docx") as report:
            media = [name for name in report.namelist() if name.startswith("word/media/")]
            assert len(media) == {1: 2, 2: 3, 3: 2, 4: 3}[number]
            assert all(hashlib.sha256(report.read(name)).hexdigest() in hashes for name in media)


def main() -> None:
    """四份按作业的提交包，加一份共享的集成源码，避免重新引入独立项目。"""
    OUTPUT.mkdir(exist_ok=True)
    validate_images()
    shared = collect(["README.md", ".gitignore", "requirements-docs.txt", *COMMON, *JAVA, *PYTHON, *FRONTEND,
                      "scripts/homework", "scripts/book_import", "docs/assignments"])
    shared_name = f"{STUDENT}-书城集成源码.zip"
    write_archive(OUTPUT / shared_name, {"bookstore/" + name: source for name, source in shared.items()})
    selected = {
        1: ["python-assistant/backend/api_design.py", "react-ebook/src/pages/ApiDesignPage.jsx",
            "springboot-ebook/src/main/java/com/ebook/backend/controller/BookController.java",
            "scripts/homework/generate_contract.py", "scripts/homework/validate_openapi.py"],
        2: [*PYTHON, "react-ebook/src/pages/AssistantPage.jsx", "react-ebook/src/pages/AssistantPage.css",
            "react-ebook/src/api/assistantApi.js", "scripts/homework/collect_evidence.py"],
        3: [*PYTHON, "react-ebook/src/pages/AssistantPage.jsx", "react-ebook/src/pages/AssistantPage.css",
            "react-ebook/src/api/assistantApi.js", "scripts/homework/collect_evidence.py"],
        4: [*JAVA, "react-ebook/src/api/auth.js", "react-ebook/src/api/backendApi.js",
            "scripts/homework/collect_evidence.py"],
    }
    package_names = []
    for number in range(1, 5):
        name = f"{STUDENT}-作业{number}.zip"
        package_names.append(name)
        sources = collect([*COMMON, *selected[number], "scripts/homework/build_reports.py",
                           "scripts/homework/report_document.py", "scripts/homework/templates/作业模版.docx",
                           "scripts/homework/capture_browser.cjs", "scripts/homework/capture_readonly.cjs",
                           "requirements-docs.txt"])
        files = {"source/" + name: source for name, source in sources.items()}
        files[f"{STUDENT}-作业{number}.docx"] = OUTPUT / f"{STUDENT}-作业{number}.docx"
        evidence = collect([f"docs/assignments/hw{number}", "docs/assignments/browser-captures.json",
                            "docs/assignments/service-lifecycle.json"])
        files.update(evidence)
        if number == 1:
            files["openapi.json"] = ROOT / "docs/assignments/hw1/openapi.json"
        readme = (f"# 作业{number}\n\n"
                  "本包包含模板报告、对应实现的自编源码、运行脚本与真实证据。source/ 下保留原书城的文件路径，"
                  "用于审阅本次作业的实现，所有作业共用同一个书城。\n\n"
                  "客服查询、书目推荐与政策问答现在使用同一个 /assistant 页面和 /api/assistant/chat 接口。"
                  "库存与比价函数、查书与政策 RAG 工具由同一个 Agent 通过 Function Calling + ReAct 循环调用。\n\n"
                  f"完整运行请解压同交付目录中的 `{shared_name}`，进入 bookstore/，执行 `./run-all.sh`。"
                  "该源码包仅包含自编源文件、必要静态资源、脚本和文档；依赖与编译产物由启动脚本安装或构建。"
                  "各次作业包不含第三方 Jar、node_modules、Python 虚拟环境、本机密钥或模型权重。\n\n"
                  "前端 http://127.0.0.1:5173，后端 http://127.0.0.1:8080，统一 Agent http://127.0.0.1:8000。"
                  "`./stop-all.sh` 关闭三个服务及本项目数据库并保留数据。环境和模型配置见集成源码中的 README.md。\n")
        write_archive(OUTPUT / name, files, {"README.md": readme})
    readme = ("# 四次作业\n\n"
              "四份按作业命名的压缩包用于对应作业提交，各包含模板报告、对应自编源码、脚本和真实运行证据。"
              f"作业1另附最终 openapi.json。`{shared_name}` 保存四次功能整合后的唯一书城源码，供完整运行。\n\n"
              "作业2的库存/比价和作业3的书目/政策功能统一运行在 React 的 /assistant 页面；"
              "四个工具使用同一套 Function Calling 与 ReAct 循环，页面保留 Thought、Action 和 Observation。\n\n"
              "解压集成源码，进入 bookstore/ 后执行 `./run-all.sh`；停止使用 `./stop-all.sh`，状态使用 `./status-all.sh`。"
              "需要单独管理时使用 `--frontend`、`--backend` 或 `--agent`。默认端口 5173、8080、8000；启动前清理选定端口，停止后保留数据库数据。\n\n"
              "需要 JDK21、Maven、Node18+、Python3.10+、Docker Desktop 和 lsof。首次使用会下载依赖和本地向量模型。"
              "真实模型通过 python-assistant/.env 配置；密钥文件不包含在交付包中。演示管理员 admin/admin123，普通用户 DefaultUser/123456。\n")
    (OUTPUT / "README.md").write_text(readme)
    bundle = {name: OUTPUT / name for name in [*package_names, shared_name]}
    write_archive(OUTPUT / f"{STUDENT}-四次作业.zip", bundle, {"README.md": readme})


if __name__ == "__main__":
    main()
