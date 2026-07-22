# MoviePilot Lite

> **非官方、社区维护的 MoviePilot v2 网盘精简构建。**
>
> **当前状态：`v2.14.5-lite.1-rc.8` 已完成核心工作流验收；Docker Hub `latest` 指向此版本。**

MoviePilot Lite 不是 MoviePilot 官方版本，不由 MoviePilot 官方团队维护或提供支持。请勿将 Lite 特有问题提交到官方项目。

本项目面向个人和家庭自托管的网盘媒体管理场景，重点保留网盘、元数据识别、文件整理、插件、消息通知和媒体服务器能力，同时移除 PT、下载器、影视订阅及其他非目标运行链路。

精简目标不是隐藏菜单，而是在构建和运行时真正做到：不安装非目标依赖、不导入和注册非目标模块、不启动相关服务和后台任务，并尽量维持官方源码结构以持续跟踪上游更新。

## 核心流程

```text
网盘文件或目录
  → 元数据识别与人工纠正
  → 重命名、刮削和文件整理
  → STRM 或媒体库内容更新
  → 消息通知
  → Emby / Jellyfin / Plex 刷新
```

消息渠道中的115分享链接处理流程：

```text
官方消息渠道接收115分享链接
  → 使用官方身份和权限逻辑校验
  → MoviePilot Lite 识别分享链接
  → 调用用户手动安装的 P115StrmHelper
  → 完成转存、整理及 STRM 处理
  → 通过原消息渠道返回结果
```

## 保留能力

- 官方网盘及存储适配器的源码兼容，按实际配置延迟加载。
- 115网盘授权、文件访问和分享链接转存，作为首个真实验收对象。
- TMDB、豆瓣、Bangumi、TheTVDB、Fanart 等元数据底层能力。
- 元数据识别、识别预览、人工纠正、重命名和刮削。
- 文件浏览、文件管理、目录监控、手动整理、整理历史和失败重试。
- 插件市场、手动安装、升级、插件页面、事件、定时任务和插件 API。
- 官方消息渠道、通知发送、必要回调和115分享链接入站处理。
- Emby、Jellyfin 和 Plex 的媒体库刷新、同步及查询。
- 单管理员密码登录、登录会话、Token 和 `API_TOKEN`。
- SQLite、进程内缓存和 `ffprobe`。
- Docker `linux/amd64` 和 `linux/arm64`。

## 移除能力

- PT站点、索引器、站点资源包、`AUTH_SITE` 及其在线校验链路。
- qBittorrent、Transmission、rTorrent 等下载器及下载任务。
- 影视订阅、资源搜索、推荐、探索、榜单和人物发现。
- Agent、LLM、MCP、Skills、语音和相关模型依赖。
- 工作流编辑器、执行引擎和后台任务。
- CookieCloud、浏览器内核、Playwright、OCR 和 FlareSolverr。
- PostgreSQL、Redis、多用户、注册、角色系统、SSO 和辅助认证。
- Radarr、Sonarr 和 CookieCloud 兼容接口。
- `ffmpeg` 及依赖它的插件功能。
- 非必要的统计和数据上报。

## 115网盘STRM助手

[P115StrmHelper（115网盘STRM助手）](https://github.com/DDSRem-Dev/MoviePilot-Plugins/tree/main/docs/p115strmhelper)是目标115工作流的必装插件，但不包含在 MoviePilot Lite 核心中。

- 必须由用户手动安装和配置。
- Lite 不预装、不自动安装、不在后台自动下载或静默升级。
- 每个 Lite 版本只支持经过明确测试的插件版本或版本范围。
- 插件缺失、未启用或不兼容时，MoviePilot Lite 仍可启动，但115分享转存和相关 STRM 功能不可用，并应显示明确提示。
- 插件内部的 PT、搜索、下载、Agent、MCP、浏览器或其他已移除能力不属于 Lite 支持范围。
- 第三方插件可能有独立的隐私、遥测和外部服务设置，安装前必须检查。

## 安装

默认安装镜像：

```text
docker.io/zfl0087/moviepilot-lite:latest
```

当前固定版本为 `v2.14.5-lite.1-rc.8@sha256:f7acb73bd2abf510bac42a09838d3f91b558e4d11ab8dab4d438610b24b88d34`。安装前必须备份 `/config`；回退或复现问题时请使用固定版本，而不要依赖 `latest`。不得把管理端口直接暴露到公网。P115StrmHelper `2.8.62` 需要通过插件市场手动安装。

新手可直接查看 [Docker 安装教程](docs/DOCKER_INSTALL.md)；完整的镜像校验、升级、回退步骤及未验证项目见 [公开发布与安装说明](docs/PUBLIC_RELEASE.md)。

## 兼容范围

- 正式数据库只支持 SQLite。
- 保留官方 `/config` 目录迁移和回退目标，首次使用官方数据启动 Lite 前必须备份。
- 115是首个真实账号验收的网盘；其他官方存储适配器保留源码兼容，但首版不承诺全部真实验收。
- Emby、Jellyfin 和 Plex 保持相同官方版本的接口语义。
- 只正式支持明确配对的 Lite 后端和 Lite 前端。
- 插件兼容性按插件及版本分别记录，不承诺兼容所有官方或第三方插件。

完整兼容合同见 [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md)。

## 项目文档

- [PROJECT_BRIEF.md](PROJECT_BRIEF.md)：产品目标、保留范围、移除范围和验收指标。
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)：能力配置、导入门控、前后端边界和构建裁剪。
- [docs/UPSTREAM_SYNC.md](docs/UPSTREAM_SYNC.md)：上游同步、分支、测试、候选发布和回退流程。
- [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md)：配置、数据库、API、插件和部署兼容矩阵。
- [docs/DOCKER_INSTALL.md](docs/DOCKER_INSTALL.md)：NAS 图形界面与 Docker Compose 快速安装教程。
- [docs/PUBLIC_RELEASE.md](docs/PUBLIC_RELEASE.md)：公开镜像的固定版本、安装、升级和回退说明。
- [SECURITY.md](SECURITY.md)：安全问题报告范围和敏感信息处理规则。
- [AGENTS.md](AGENTS.md)：AI代理和项目实施规则。

## 上游与版本

MoviePilot Lite 基于以下官方项目：

- 后端：[jxxghp/MoviePilot](https://github.com/jxxghp/MoviePilot)，跟踪 `v2`。
- 前端：[jxxghp/MoviePilot-Frontend](https://github.com/jxxghp/MoviePilot-Frontend)，跟踪 `v2`。
- 官方插件市场：[jxxghp/MoviePilot-Plugins](https://github.com/jxxghp/MoviePilot-Plugins)。

首个实现基线：

| 组件 | 版本 | 官方提交 |
|---|---|---|
| 后端 | `v2.14.5` | `8b5524a321c940f337873cefa54ba6a58462f9a4` |
| 前端 | `v2.14.5` | `435e9ecfdd4febf791fd581b3be9233816cebf7f` |

对应基线的[官方后端 README](https://github.com/jxxghp/MoviePilot/blob/8b5524a321c940f337873cefa54ba6a58462f9a4/README.md)可用于查看未经 Lite 改写的官方说明。

Lite 版本格式为 `v<官方版本>-lite.<修订号>`，例如 `v2.14.5-lite.1`。每个版本必须记录官方后端提交、官方前端提交、Lite 后端提交、Lite 前端提交和 Docker 镜像摘要。

## 分发与许可证

MoviePilot Lite 是非官方社区构建，不代表 MoviePilot 官方，也不由官方团队提供支持。维护者目前不销售支持、不运营 SaaS，也不公开托管用户实例。

- 本项目继承并保留上游的 GNU General Public License v3.0、版权声明和修改记录。
- 向他人分发镜像或二进制时，必须同时提供与该版本对应的完整源码和版本追溯信息。
- 维护者的运营选择不限制接收者依据 GPLv3 使用、修改、再分发或收费分发的权利。
- MoviePilot Lite 移除了 PT 站点用户认证；修改、分发和使用产生的责任由相应修改者、分发者和使用者承担。
- 本项目不对第三方插件、外部 API、网盘服务或用户数据损失承担保证责任，部署前必须备份重要数据。

完整许可证见 [LICENSE](LICENSE)。

## 安全提示

- 不得提交115 Token、Cookie、消息渠道 Token、管理员密码、`API_TOKEN`、数据库文件或真实 `/config`。
- 真实网盘凭据只保存在部署实例的安全配置中，不进入普通 CI、构建日志或测试产物。
- 第三方插件安装前必须核对来源、许可证、依赖、隐私政策和遥测设置。
- 升级前固定当前镜像版本并备份 `/config`，不得依赖 `latest` 回退。
