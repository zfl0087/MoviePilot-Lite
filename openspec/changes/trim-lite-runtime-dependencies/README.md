# trim-lite-runtime-dependencies

从 MoviePilot Lite 正式运行时移除 PT/下载器、Agent/LLM、浏览器模拟、Redis/PostgreSQL 和 Windows 托盘专属 Python 依赖，同时保留网盘、元数据、文件整理、插件、消息通知和媒体服务器能力。

## 审计基线

在当前 Windows 开发环境中，变更前 `requirements.in` 的运行依赖闭包包含 168 个已安装发行包，磁盘占用约 594.06 MiB。移除本变更定义的 24 个直接运行依赖后，闭包估算为 114 个发行包、约 313.79 MiB，预计基础 Python 环境减少 280.28 MiB（47.2%）。实际创建的全新 Windows 运行虚拟环境包含 120 个发行包（含 pip 等虚拟环境引导工具）、占用 326.31 MiB，24 个禁止发行包均不存在。

干净环境已成功导入主 API、Scheduler、Command、MessageChain、TransferChain、Monitor、生命周期和主程序入口；U115/Local/SMB/Rclone、Telegram/Slack/Discord/飞书/WebPush、Emby/Jellyfin/Plex、元数据、整理和插件核心模块也全部可导入。正常模式连续两次启动和停止均无禁止模块加载或残留线程。以上是 Windows Python 环境证据，不是最终 Linux Docker 镜像结果。

手动安装 P115StrmHelper 后，插件会按自身声明安装 `numpy` 等依赖，因此基础镜像和安装必装插件后的部署占用必须分别记录。本变更不预装插件，也不实施 Docker 系统包、浏览器内核、FFmpeg 或前端产物裁剪。
