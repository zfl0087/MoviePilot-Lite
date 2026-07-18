## Context

当前 `docker/Dockerfile` 与 `docker/entrypoint.sh` 仍与官方 `upstream/v2` 保持一致，而正式 Python 运行依赖已经完成 Lite 裁剪。由此形成三组冲突：

1. Dockerfile 在最终阶段执行 `playwright install-deps chromium`，但正式 venv 已不包含 Playwright。
2. entrypoint 的核心探针和浏览器安装仍要求 `cloakbrowser`，而该发行包已经从运行入口移除；依赖自愈也无法把它恢复。
3. `MOVIEPILOT_AUTO_UPDATE=release` 默认启用，`docker/update.sh`、升级 API 和 `app.cli` 会从官方仓库替换运行代码，绕过 Lite 的 capability、测试和候选流程。

镜像同时包含两套静态媒体工具、全部官方插件、PT 站点资源和大量面向更新、调试、浏览器或已禁用能力的系统包。源代码本身只占较小部分，盲目删除零散 Python 文件会增加上游同步冲突，却不会带来同等资源收益。

## Goals / Non-Goals

**Goals:**

- 让 Docker 构建、启动探针和正式 Python 依赖使用同一 Lite 能力边界。
- 形成固定提交、不可原地更新的 Lite 容器，只通过替换受控候选镜像升级。
- 移除浏览器、`ffmpeg`、PT 资源、预装插件和非必要系统工具，保留网盘与整理链所需运行工具。
- 保持 `/config`、普通重启、Nginx/SSL、插件手动安装、通知、媒体服务器和诊断能力。
- 用合同测试、物理缺失测试、双架构构建和同口径资源数据证明产物边界。
- 集中维护少量显式裁剪矩阵，让上游新增资源或更新入口时失败关闭。

**Non-Goals:**

- 不修改 Lite 前端路由、菜单或前端构建产物；只继续下载固定 `FRONTEND_VERSION`。
- 不构建、推送、发布或部署镜像，不触发 GitHub Actions、DockerHub 或 GHCR。
- 不安装、分叉或真实验证 P115StrmHelper，不使用真实 115/消息/媒体服务器凭据。
- 不删除 Git 仓库中的官方禁用源码，不修改数据库 Schema，不清理历史配置。
- 不承诺当前 Windows 主机能够提供 Linux 镜像体积、amd64/arm64 或容器 RSS 的最终证据。

## Decisions

### 1. Lite 容器采用不可原地更新模型

最终镜像不得包含或调用 `/usr/local/bin/mp_update.sh`，entrypoint 不再设置或执行 `MOVIEPILOT_AUTO_UPDATE`，也不消费 `${CONFIG_DIR}/temp/moviepilot.pending_update`。历史环境变量和文件不作为功能开关，不主动改写普通配置数据。

`POST /api/v1/system/upgrade` 保留管理员认证，但在 Lite 中返回 `success=false` 和稳定、可操作的消息，说明需要部署经审核的固定 Lite 镜像。它不得调用 `SystemHelper.restart()`、不得写一次性升级标记、不得发布停止请求。普通 `/restart` 和消息 `/restart` 继续使用原有重启链。

`app.cli start/restart` 不调用 `_best_effort_auto_update()`，不查询官方 Release API，不执行 `scripts/local_setup.py update`。镜像还要排除可直接执行官方原地更新的辅助入口。显式更新源码仓库属于维护者的上游同步流程，不属于运行容器能力。

拒绝仅把默认值从 `release` 改成 `false`：用户历史配置、一次性标记或升级 API 仍可重新开启官方覆盖，不能形成安全边界。

### 2. 系统包使用正向允许集合

最终运行阶段保留下列工具及其必要传递依赖：

| 组件 | 保留原因 |
|---|---|
| `nginx`、`gettext-base` | 前端静态服务、反向代理和模板渲染 |
| `procps` | entrypoint 使用 `ps`，证书/进程流程使用 `pgrep` |
| `gosu`、`bash`、`tini` | UID/GID 降权、入口脚本和 PID 1 信号处理 |
| `ca-certificates`、`curl` | 健康检查、保留 API/插件安装和受控构建下载 |
| `cron`、`tzdata` | 保留 SSL 证书续期和 `Asia/Shanghai` 时区行为 |
| `unar` | 保留 RAR/字幕解压能力 |
| `libjemalloc2` | 保持现有内存分配器运行配置 |
| `rclone` | 保留 Rclone 存储适配器 |
| `uv` 及 pip 兼容包装 | 主运行依赖诊断修复和管理员手动插件依赖安装 |

从最终阶段移除当前没有保留运行调用方的直接包：`locales`、`wget`、`git`、`gh`、`busybox`、`jq`、`ripgrep`、`less`、`unzip`、`fuse3`、`rsync`、`openssh-client`、`iproute2`、`netcat-openbsd`、`lsof` 和 `nano`。构建阶段可以使用临时工具，但不得把它们带入最终镜像。

`LANG=C.UTF-8` 保持不变，删除 `zh_CN.UTF-8` 生成。必须用中文、空格和常见标点文件名完成创建、枚举、整理和 `ffprobe` 路径往返测试；若证据显示保留链确实依赖完整 locale 数据，再以最小依赖恢复，而不是凭推测预装。

### 3. 浏览器和媒体二进制按 capability 裁剪

删除 `playwright install-deps chromium`，entrypoint 不再下载 CloakBrowser 内核、读取 `BROWSER_EMULATION` 或特殊处理 `${HOME}/.cloakbrowser`。Doctor 的 `CORE_DEPENDENCIES` 和启动探针只检查正式运行入口中的真实核心包。

从 `mwader/static-ffmpeg` 只复制 `/ffprobe`。镜像内容测试必须证明 `ffprobe` 可执行且 `ffmpeg` 不存在。依赖转码的插件继续由兼容检查拒绝，不能通过插件安装把 `ffmpeg` 重新定义为 Lite 核心二进制。

### 4. 插件和 PT 资源不进入基础镜像

`prepare_code` 只下载固定版本前端，不克隆或解压 `MoviePilot-Plugins`，不下载 `user.sites.v2.bin` 或平台 `sites.*`。`/app/app/plugins` 保持可写的空目录结构，管理员仍可通过保留的插件 API 和市场手动安装兼容插件。

启动不得因 P115StrmHelper 缺失而失败，也不得访问插件市场自动补装。普通 115 分享链接继续通过既有 `UserMessage`/`MessageAction` 事件交给已经手动安装且启用的插件。

### 5. 只从最终产物排除经过证明的源码整块

Git 仓库继续保留完整上游源码，裁剪只发生在 Docker 构建上下文或最终镜像层。首批候选排除范围限于已经存在导入前门控、且可用物理缺失测试证明启动不依赖的整块：

- `app/agent/`、`app/workflow/`、`skills/`；
- 已禁用 API endpoint 模块、`app/api/servarr.py`、`app/api/servcookie.py` 和只服务于这些端点的 OpenAI 适配文件；
- `app/modules/indexer/`、`app/modules/postgresql/`、`app/modules/qbittorrent/`、`app/modules/redis/`、`app/modules/rtorrent/`、`app/modules/transmission/`；
- 仅供测试或本地更新/安装使用、且 Docker 运行不引用的辅助文件。

精确清单必须集中在 Docker 构建合同中并由测试枚举。`app/chain/search.py`、其他禁用 Chain/Helper 和共享 Schema 仍存在保留端点或延迟引用时，本变更不直接删除；先让调用点在 import 前依据 capability 返回明确不支持，才能进入后续清单。

拒绝在 Git 中物理删除整个功能树，也拒绝为了几 MB 源码收益维护大规模逐文件黑名单。

### 6. `/config` 和重启行为保持兼容

镜像不迁移、不删除或重写 SQLite、插件数据、历史 PT/下载器配置和未知字段。`MOVIEPILOT_AUTO_UPDATE` 即使仍存在于 `app.env`，也不能扩大 Lite 能力。旧的一次性升级标记不得被 Lite 执行为官方更新；迁移/回退文档必须提示用户在切回官方镜像前检查该临时状态。

普通重启继续支持 Docker restart policy 和 Docker socket proxy 两条官方路径。SSL、ACME/cron、健康检查、日志、Doctor、diagnostic keepalive、PUID/PGID/UMASK 和插件目录权限语义不得因裁剪退化。

### 7. 运行依赖修复只恢复 Lite 主程序

entrypoint 的 `ensure_backend_runtime_dependencies` 可以继续从 `/app/requirements.txt` 修复正式 Lite 核心依赖，但探针必须与 `requirements.in` 契约一致。修复不读取 `requirements-dev.in`，不恢复 CloakBrowser/Playwright，也不替未安装插件补依赖。

手动插件安装仍通过既有管理员认证流程调用 `uv`/pip 兼容入口。插件依赖失败只影响该插件，不使核心进入错误 keepalive。

### 8. 构建和资源验证分层进行

本地无 Docker 主机可完成静态合同、Python 测试和不依赖 Bash 的测试。候选构建环境必须补齐：

1. `linux/amd64` 和 `linux/arm64` 构建；
2. 对最终镜像运行文件、二进制、包管理器和 Python 模块清单检查；
3. 使用临时 `/config` 连续启动/停止两次，验证登录、U115 mock、整理、通知、媒体服务器、插件手动安装和普通重启；
4. 在相同硬件、相同官方版本、相同前端和等价配置下比较压缩/解压镜像体积、冷启动到健康检查时间、稳定空闲 RSS/CPU；
5. 安装 P115StrmHelper 前后分别记录占用，不把插件后依赖算入基础镜像收益。

镜像体积至少降低 25%、冷启动至少缩短 20%、空闲 RSS 至少降低 30%，空闲 CPU 长期接近 0。任何平台构建或功能门禁失败均停止候选，不降低标准或发布单架构镜像冒充完成。

### 9. 上游同步与镜像发布继续分离

Docker 构建固定 Lite 后端提交和 `FRONTEND_VERSION` 对应前端产物，不使用浮动 `latest`。官方 `.github/workflows/build.yml`/`beta.yml` 会发布 DockerHub、维护 `latest` 并改写 Release，不能复用。

本变更只建立镜像合同。私有 GHCR 候选工作流、构建凭据、标签、发布和 Canary 部署必须分别讨论并获得批准。

## Risks / Trade-offs

- **遗漏隐式系统命令**：APT 删除可能直到某条保留流程运行才暴露。通过静态命令扫描、容器行为测试和逐包正向证明缓解，不一次删除无法验证的传递库。
- **C.UTF-8 与中文路径差异**：基础镜像声明支持 UTF-8，但实际文件/整理/探针流程仍需双架构测试。失败时根据调用方恢复最小 locale 组件。
- **升级入口仍可被旁路调用**：只改 entrypoint 默认值不够。API、CLI 调用点、更新器复制和最终镜像文件清单必须同时失败关闭。
- **源码裁剪破坏延迟路径**：保留端点中仍有历史禁用方法。物理缺失测试覆盖主入口和保留 API；未完成 import 前门控的文件暂不裁剪。
- **插件安装需要构建工具**：基础镜像不保留 `build-essential`。兼容插件应使用 wheel；需要现场编译或禁用系统能力的插件标记不兼容，不为单个插件扩大基础镜像。
- **证书流程依赖 cron/时区**：保留 `cron` 和显式 `tzdata`，用启动与续期模拟验证，不能因体积优化删除。
- **资源指标受平台缓存影响**：固定设备、镜像、配置、测量窗口和重复次数，报告原始值与方法，不把 Windows 静态估算当 Docker 结果。

## Migration Plan

1. 在任何实现前备份 `/config` 副本并记录当前镜像、Lite/官方提交、`MOVIEPILOT_AUTO_UPDATE` 状态和插件清单，不记录秘密值。
2. 先写 Docker/entrypoint/Doctor/升级失败关闭合同测试并确认在当前官方镜像定义上失败。
3. 调整 Dockerfile 与 entrypoint，移除浏览器、`ffmpeg`、预装插件、PT 资源、更新器和非必要包。
4. 调整 Doctor、API、SystemHelper 和 CLI 更新行为，保持普通重启测试通过。
5. 增加物理缺失、中文路径、插件手动安装和干净启动测试；运行相关及全量 Python 测试、ShellCheck/Pylint 和 OpenSpec 校验。
6. 经单独批准后在私有受控环境构建 amd64/arm64 候选并生成资源报告；不得发布或部署。
7. 再经批准使用 `/config` 副本和真实 P115StrmHelper 完成隔离 Canary；生产升级仍需另行批准。

## Rollback

回退本变更实现提交并重新构建上一固定镜像即可恢复原 Docker 产物。由于本变更不迁移数据库、不删除 `/config` 数据且不消费历史升级标记，上一 Lite 或对应官方镜像仍可读取原配置。回退前必须检查一次性升级标记和自动更新配置，避免官方镜像启动后执行意外原地更新。
