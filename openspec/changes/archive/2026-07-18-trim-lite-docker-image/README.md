# trim-lite-docker-image

将 MoviePilot Lite 正式容器收敛为固定提交、不可原地更新的精简镜像：移除浏览器、`ffmpeg`、PT 资源、预装插件和非必要系统工具，保留 `ffprobe`、网盘、整理、手动插件、通知、媒体服务器、SSL 与普通重启能力。

## 当前状态

Docker 静态产物合同、Python 升级拒绝路径和 CLI 文档已经在提交 `c5d5fa1d` 中实施并推送到私有 `origin/lite`。本次归档只把已批准的规范增量合并到主规范，不代表候选镜像已经通过发布门禁。

当前主机没有 Docker/Bash，因此 Linux entrypoint、Shell 静态分析、`linux/amd64`/`linux/arm64` 候选构建、最终镜像内容与运行检查、资源指标和真实 115 Canary 仍待后续受控环境验证。尚未构建、发布或部署任何 Lite 镜像。

## 实施与验证摘要

- Docker 运行系统包已收敛为允许集合，移除浏览器、`ffmpeg`、PT 资源和预装插件，保留 `ffprobe`、固定 Rclone、Unar、Nginx/SSL/cron 与空插件目录。
- 容器和 CLI 官方原地更新链路已移除；管理员升级 API 固定拒绝原地升级，普通重启行为保持不变。
- Windows 保留流程回归 140 项通过，定向 Pylint 为 `10.00/10`，OpenSpec 严格验证为 7 项通过、0 项失败。
- Windows 全量 pytest 为 1989 项通过、29 项失败、39 项跳过；失败包含 Windows/GBK、Linux 路径、符号链接权限、临时文件锁和已禁用上游能力测试，不能表述为全量绿色。

候选构建、发布和部署仍需按 `tasks.md` 的独立批准检查点推进。
