## Why

MoviePilot Lite 已经在运行依赖、API、模块发现、生命周期、Scheduler 和消息链中固定移除 PT、下载器、Agent、Workflow、Redis、PostgreSQL 和浏览器模拟能力，但官方 Docker 构建仍按完整版本组装镜像。当前 Dockerfile 仍安装 Chromium/Playwright 系统依赖、复制 `ffmpeg`、预装全部官方插件并下载 PT 站点资源；entrypoint 仍把 CloakBrowser 视为核心依赖并在每次启动下载浏览器内核。

这已经造成明确的不一致：`requirements.in` 不再安装 Playwright/CloakBrowser，而 Dockerfile 和启动探针仍直接调用它们，镜像可能在构建或启动阶段失败。更严重的是，容器默认执行官方原地更新器，升级 API 和本地 CLI 自动更新也会从 `jxxghp/MoviePilot` 覆盖 `/app`，从而绕过 Lite 的能力审查并恢复已移除功能。

因此本变更必须把 Docker 产物收敛为固定提交、不可原地变更的 Lite 镜像：只通过经过测试的候选镜像升级，运行中的容器不得从官方仓库改写自身代码。

## What Changes

- 移除 Docker 构建中的 Playwright/Chromium 系统依赖安装、CloakBrowser 核心探针、浏览器内核下载和专属 HOME 权限处理。
- 仅复制并保留 `ffprobe`；不再把 `ffmpeg` 放入 Lite 镜像。
- 停止下载和预装 `MoviePilot-Plugins`；保留插件市场和经管理员认证的手动安装/升级能力。P115StrmHelper 仍是目标 115 工作流的必装插件，但不进入基础镜像。
- 停止下载 `user.sites.v2.bin`、平台 `sites.*` 二进制和其他 PT 站点资源。
- 将最终镜像系统包收敛为保留运行链的正向允许集合，移除只服务于官方更新器、浏览器、调试工具或已禁用能力的 APT 包；使用 `C.UTF-8` 并移除未被运行配置使用的 `locales`/`locale-gen`。
- 移除镜像内官方更新器和更新辅助入口。Docker 启动不读取、消费或执行 `MOVIEPILOT_AUTO_UPDATE`；升级 API 明确失败关闭且不写一次性标记、不重启；`app.cli` 的 `start/restart` 不访问官方 GitHub 或执行本地更新脚本。
- 普通重启、Docker restart proxy、Nginx、SSL/证书续期、插件手动安装、`uv`、Rclone、RAR/字幕解压、`ffprobe`、健康检查、诊断 keepalive、`gosu`、`tini` 和 jemalloc 保持可用。
- Git 仓库继续保留官方源码结构；只在最终镜像排除已经有导入前门控、且物理缺失测试通过的禁用源码整块和测试/构建辅助文件。仍被保留端点或 Chain 延迟引用的零散源码不在本变更冒险删除。
- 新增 Docker 构建合同、entrypoint/Doctor/升级失败关闭、C.UTF-8 中文文件名、物理缺失导入、插件手动安装和干净容器启动测试。
- 要求 `linux/amd64` 与 `linux/arm64` 构建、镜像内容检查，以及相同官方版本/配置下的体积、冷启动、空闲 RSS/CPU 对比；本机无法完成的构建证据必须在受控候选工作流中补齐后才能发布。
- **BREAKING**：Lite 不再支持运行中原地升级，也不提供浏览器内核、`ffmpeg`、PT 站点资源或预装插件。升级操作改为部署已审核的固定 Lite 候选镜像。

## Capabilities

### New Capabilities

- `lite-docker-image-profile`: 定义 Lite 最终容器的系统包、二进制、资源、源码、插件和不可原地更新合同，以及双架构与资源验收要求。

### Modified Capabilities

- `lite-runtime-dependency-profile`: Doctor 和容器启动探针必须与已经精简的正式 Python 运行依赖一致，不得把 CloakBrowser 等禁止包重新认定为核心依赖或在启动时补装。

## Impact

- Docker：预计修改 `.dockerignore`、`docker/Dockerfile`、`docker/entrypoint.sh`；`docker/update.sh` 保留在 Git 上游结构中，但不复制、不执行、不进入最终镜像。
- 后端：预计修改 `app/doctor/checks.py`、`app/helper/system.py`、`app/api/endpoints/system.py` 和 `app/cli.py`，使升级链路在 Lite 中明确失败关闭而普通重启保持官方行为。
- CLI 文档：若改变可见 CLI 行为，按项目耦合规则同步 `moviepilot` 入口、`docs/cli.md` 和相关测试；Docker 镜像内不提供任何可改写 `/app` 的内建更新入口。
- 插件：基础镜像的内建插件目录保持空白；用户通过既有管理员认证和插件市场手动安装兼容插件。不会自动下载 P115StrmHelper，也不会改变普通 115 分享链接广播合同。
- 配置与数据库：不修改数据库 Schema，不迁移、不删除历史配置；`MOVIEPILOT_AUTO_UPDATE` 和旧的一次性标记在 Lite 中不执行，也不作为恢复官方更新的开关。
- 前端：继续下载后端 `FRONTEND_VERSION` 对应的固定前端产物；本变更不实施 Lite 前端路由/产物裁剪，也不允许使用浮动 `latest`。
- 兼容性：保留 `/config`、SQLite、网盘、元数据、整理、通知、Emby/Jellyfin/Plex、插件 API 和普通重启；依赖浏览器、PT、下载器、Agent、Workflow、Redis/PostgreSQL 或 `ffmpeg` 的插件继续不兼容。
- 安全：消除运行容器从官方仓库覆盖 Lite 代码的路径，减少浏览器和调试工具攻击面；不把真实 115、消息渠道或管理员凭据放入构建和普通 CI。
- 资源：预期主要收益来自移除 Chromium 系统库、CloakBrowser 内核、`ffmpeg`、预置插件、PT 资源和非必要 APT 包；Python 源码排除只作合同强化，不夸大其体积收益。
- 上游同步：继续通过 `docs/UPSTREAM_SYNC.md` 的只读上游合并、测试、候选镜像和 Canary 流程更新；不得复用官方会发布 DockerHub/`latest` 或重建 Release 的工作流。
- 非目标：不构建或发布镜像、不创建外部 CI、不部署 Canary、不修改前端仓库、不安装真实 P115StrmHelper，也不公开发行。
