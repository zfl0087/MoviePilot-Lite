# trim-lite-docker-image

将 MoviePilot Lite 正式容器收敛为固定提交、不可原地更新的精简镜像：移除浏览器、`ffmpeg`、PT 资源、预装插件和非必要系统工具，保留 `ffprobe`、网盘、整理、手动插件、通知、媒体服务器、SSL 与普通重启能力。

## 当前状态

只读审计和 OpenSpec 已完成，尚未实施 Docker、Python、CLI 或工作流修改，也未构建、发布或部署任何镜像。当前主机没有 Docker/Bash，双架构构建、Shell 行为和最终资源指标必须在后续获批的受控候选环境补齐。

## 审计摘要

- 当前 Dockerfile 仍调用未安装的 Playwright，并在启动时要求/下载 CloakBrowser。
- 当前镜像仍复制 `ffmpeg` 和 `ffprobe`、预装全部官方插件并下载 PT 站点资源。
- 当前容器默认从官方仓库原地更新，可覆盖 Lite 代码并绕过候选审查。
- Lite 核心相关测试在本次审计中为 56 项通过；Docker shell 测试受当前 Windows 缺少 Bash 和符号链接权限限制，不能作为 Linux 镜像证据。

实施、提交、推送、候选构建、发布和部署均需按 `tasks.md` 的独立批准检查点推进。
