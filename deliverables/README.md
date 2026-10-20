# 四次作业

四份按作业命名的压缩包用于对应作业提交，各包含模板报告、对应自编源码、脚本和真实运行证据。作业1另附最终 openapi.json。`524031910113-书城集成源码.zip` 保存四次功能整合后的唯一书城源码，供完整运行。

作业2的库存/比价和作业3的书目/政策功能统一运行在 React 的 /assistant 页面；四个工具使用同一套 Function Calling 与 ReAct 循环，页面保留 Thought、Action 和 Observation。

解压集成源码，进入 bookstore/ 后执行 `./run-all.sh`；停止使用 `./stop-all.sh`，状态使用 `./status-all.sh`。需要单独管理时使用 `--frontend`、`--backend` 或 `--agent`。默认端口 5173、8080、8000；启动前清理选定端口，停止后保留数据库数据。

需要 JDK21、Maven、Node18+、Python3.10+、Docker Desktop 和 lsof。首次使用会下载依赖和本地向量模型。真实模型通过 python-assistant/.env 配置；密钥文件不包含在交付包中。演示管理员 admin/admin123，普通用户 DefaultUser/123456。
