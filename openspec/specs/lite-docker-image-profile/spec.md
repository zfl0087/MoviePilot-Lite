# lite-docker-image-profile Specification

## Purpose
TBD - created by archiving change trim-lite-docker-image. Update Purpose after archive.
## Requirements
### Requirement: Lite 最终镜像必须使用固定系统工具允许集合
Lite Docker 最终阶段 MUST 只安装保留运行链能够正向证明需要的系统工具，并 MUST 将构建工具限制在临时阶段。最终镜像 MUST 保留 Nginx/模板渲染、进程检查、UID/GID 降权、信号处理、TLS/健康检查、证书续期、时区、RAR/字幕解压、jemalloc 和 Rclone 所需工具；MUST NOT 直接安装只服务于官方更新、浏览器、交互调试、网络诊断或已禁用能力的系统包。

#### Scenario: 最终 APT 直接包符合允许集合
- **WHEN** 测试解析 Dockerfile 最终运行阶段的直接 APT 安装项
- **THEN** 所有保留包均有明确运行所有者，`locales`、`wget`、`git`、`gh`、`busybox`、`jq`、`ripgrep`、`less`、`unzip`、`fuse3`、`rsync`、`openssh-client`、`iproute2`、`netcat-openbsd`、`lsof` 和 `nano` 均不作为最终直接包出现

#### Scenario: 构建工具不泄漏到最终镜像
- **GIVEN** venv 或前端准备阶段需要编译器、下载器或解压工具
- **WHEN** 检查最终镜像的软件包和文件清单
- **THEN** 临时构建工具未被复制到最终阶段，且保留运行工具仍可执行

#### Scenario: 上游新增系统包失败关闭
- **GIVEN** 上游 Dockerfile 新增一个不在 Lite 允许集合的最终系统包
- **WHEN** 候选运行 Docker 产物合同测试
- **THEN** 测试失败并要求人工能力分类，不能自动接受或仅按包大小决定

### Requirement: Lite 镜像必须移除浏览器并只保留 ffprobe
Lite 镜像 MUST NOT 安装 Chromium/Playwright 系统依赖、CloakBrowser 内核、虚拟显示或浏览器专属运行文件；entrypoint 和 Doctor MUST NOT 把这些组件认定为核心依赖。镜像 MUST 提供可执行的 `ffprobe`，MUST NOT 提供 `ffmpeg`。

#### Scenario: 浏览器组件不进入构建和启动
- **WHEN** 检查 Dockerfile、entrypoint、Doctor 和最终镜像
- **THEN** 不存在 Playwright/Chromium 安装、CloakBrowser 探针或下载、`BROWSER_EMULATION` 启动行为和 `.cloakbrowser` 专属权限处理

#### Scenario: 媒体探针保留而转码器缺失
- **WHEN** 容器执行二进制存在性和版本检查
- **THEN** `ffprobe` 成功运行，`ffmpeg` 不存在，元数据识别和文件整理仍可读取 mock 媒体信息

#### Scenario: 浏览器依赖插件被拒绝
- **GIVEN** 管理员手动安装一个要求 Playwright、CloakBrowser 或 FFmpeg 转码的插件
- **WHEN** Lite 进行兼容检查和启用
- **THEN** 插件得到具体缺失能力说明且不运行，核心镜像不为该插件恢复浏览器或 `ffmpeg`

### Requirement: 基础镜像不得预装插件或 PT 资源
Lite MUST NOT 在构建或启动阶段下载、复制或自动安装官方插件、P115StrmHelper、PT 站点索引/认证资源或平台 `sites.*` 二进制。插件框架、市场查询和经管理员认证的手动安装/升级 MUST 保持可用，空插件状态 MUST NOT 阻止核心启动。

#### Scenario: 干净镜像没有预装插件和 PT 资源
- **WHEN** 检查全新最终镜像的 `/app/app/plugins` 和 PT 资源路径
- **THEN** 没有从 `MoviePilot-Plugins` 预置的插件、P115StrmHelper、`user.sites.v2.bin` 或 `sites.*`，且构建日志不访问这些下载源

#### Scenario: 管理员手动安装兼容插件
- **GIVEN** 核心已经正常启动且管理员通过既有认证显式安装兼容插件
- **WHEN** 插件安装器使用保留的 `uv`/pip 入口安装插件及其声明依赖
- **THEN** 安装结果按官方语义返回，依赖不写回主程序清单，失败也不使核心退出

#### Scenario: 115 分享链接继续交给手动插件
- **GIVEN** 用户已经手动安装并启用兼容 P115StrmHelper
- **WHEN** 官方消息渠道接收普通 115 分享链接并通过既有权限判断
- **THEN** `UserMessage`/`MessageAction` 字段原样交给插件并回传结果，不触发 PT、下载器、浏览器或自动插件安装

### Requirement: Lite 容器必须禁止官方原地自更新
Lite 运行镜像 MUST 固定到已经构建和审核的 Lite 提交，MUST NOT 包含或执行能够从官方仓库覆盖 `/app` 的内建更新器。`MOVIEPILOT_AUTO_UPDATE`、历史一次性升级标记、升级 API 和 CLI `start/restart` MUST NOT 恢复官方原地更新；持续更新 MUST 通过 `docs/UPSTREAM_SYNC.md` 定义的上游同步、测试、固定候选镜像和人工推进流程完成。

#### Scenario: 容器启动不访问官方更新源
- **GIVEN** `app.env` 保存 `MOVIEPILOT_AUTO_UPDATE=release` 或 `dev`
- **WHEN** Lite 容器启动或普通重启
- **THEN** 不查询官方 Release、不下载官方后端、不执行更新脚本、不覆盖 `/app`，并继续启动当前固定镜像

#### Scenario: 一次性升级标记不能扩大能力
- **GIVEN** `/config/temp/moviepilot.pending_update` 来自历史官方实例
- **WHEN** Lite 容器启动
- **THEN** 标记不被执行为官方更新，Lite 不以其恢复已移除能力，也不把成功升级写入状态

#### Scenario: 管理员调用升级 API
- **GIVEN** 已认证管理员调用系统升级接口
- **WHEN** Lite 处理请求
- **THEN** 返回 `success=false` 和部署固定 Lite 候选镜像的明确说明，不写升级标记、不调用重启、不发布停止请求

#### Scenario: 普通重启保持可用
- **GIVEN** 容器配置有效 restart policy 或 Docker proxy
- **WHEN** 管理员调用普通重启 API 或保留消息命令
- **THEN** 继续使用官方优雅退出/代理重启语义，且重启前后都不执行更新

### Requirement: 禁用源码只能在最终镜像按证据排除
Lite MUST 保留 Git 仓库中的上游源码结构，但最终镜像 MUST 排除明确属于禁用能力、已有导入前门控且通过物理缺失测试的源码整块和本地更新/测试辅助文件。仍被保留 API、Chain、Schema、插件框架或延迟路径引用的文件 MUST NOT 仅按目录名称删除；任何新增排除路径 MUST 先有明确失败关闭行为和物理缺失证据。

#### Scenario: 首批禁用源码不进入镜像
- **WHEN** 检查最终镜像和集中排除清单
- **THEN** Agent、Workflow、Skills、PT 索引器、下载器、外部数据库和禁用 API 的已批准整块不存在，同时 Git 工作树仍保留对应上游文件

#### Scenario: 保留入口在物理缺失下可启动
- **GIVEN** 所有批准排除路径均无法导入或访问
- **WHEN** 独立进程导入并启动主 API、Scheduler、MessageChain、TransferChain、PluginManager、存储、通知和媒体服务器入口
- **THEN** 保留链成功运行，不以 `ModuleNotFoundError` 作为正常控制流，也不动态恢复被排除文件

#### Scenario: 仍有延迟引用的文件暂不排除
- **GIVEN** 一个禁用 Chain 仍可能被保留端点在 capability 判断前延迟导入
- **WHEN** 生成最终镜像排除清单
- **THEN** 该文件保持在镜像，直到调用点先失败关闭并新增物理缺失测试

### Requirement: C.UTF-8 必须支持保留的中文文件流程
Lite MAY 移除完整 `locales` 包和 `zh_CN.UTF-8` 生成，但 MUST 保持 `LANG=C.UTF-8`，并 MUST 证明中文、空格和常见标点路径能够在 Python、文件管理、整理和 `ffprobe` 调用边界无损往返。区域设置精简 MUST NOT 改变消息文本、元数据或文件名语义。

#### Scenario: 中文文件名无损往返
- **GIVEN** 临时目录包含中文、空格和常见标点的媒体文件与目录
- **WHEN** Lite 创建、枚举、序列化 FileItem、生成整理目标并调用 mock `ffprobe`
- **THEN** 每个路径按原字符返回，无乱码、编码异常或错误重命名

#### Scenario: 双架构使用相同 UTF-8 合同
- **WHEN** amd64 和 arm64 干净候选分别运行中文路径测试
- **THEN** 两个平台都通过，且最终镜像不依赖运行时生成 `zh_CN.UTF-8`

### Requirement: Docker 启动必须保留网盘产品运行基础
Docker 裁剪 MUST 保留 `/config`、SQLite、Nginx 前端、SSL/证书续期、健康检查、诊断 keepalive、PUID/PGID/UMASK、插件目录权限、Rclone/Unar、`ffprobe`、管理员认证、消息通知和 Emby/Jellyfin/Plex 所需行为。历史禁用配置和未知数据 MUST NOT 被自动删除或改写。

#### Scenario: 空插件干净容器连续启动
- **GIVEN** 临时 `/config`、SQLite、进程内缓存、空插件目录和全部外部服务 mock
- **WHEN** 候选容器连续启动、健康、停止两次
- **THEN** 核心两次均就绪，无浏览器/PT/下载器/Agent/Workflow 进程或周期任务，且没有残留后台线程

#### Scenario: 保留工具和服务可用
- **WHEN** 测试 Nginx/健康检查、SSL/cron、Doctor、Rclone、Unar、`ffprobe`、通知和媒体服务器 mock 流程
- **THEN** 每项保留能力按既有响应和权限语义工作，未因删除调试或更新工具失败

#### Scenario: 历史配置保持可回退
- **GIVEN** `/config` 中包含官方或旧 Lite 的插件、PT、下载器、更新和未知配置
- **WHEN** Lite 完成启动、普通重启和停止
- **THEN** 原始数据库与配置保持可由对应官方版本读取，禁用值不恢复运行能力且日志不泄露秘密

### Requirement: Lite Docker 候选必须通过双架构和资源门禁
每个可发布 Lite Docker 候选 MUST 使用固定后端/前端提交构建 `linux/amd64` 和 `linux/arm64`，MUST 在最终镜像检查和干净容器功能测试通过后，按相同设备、相同官方版本和等价配置测量资源。任一平台构建失败、内容合同失败、保留流程失败或指标不达标 MUST 停止候选发布。

#### Scenario: 双架构内容合同一致
- **WHEN** 分别构建并检查 amd64 和 arm64 最终镜像
- **THEN** 两个平台拥有相同允许/禁止能力、固定版本追溯信息和保留工具，不发布只有单平台通过的正式候选

#### Scenario: 资源目标按相同口径达成
- **WHEN** 将 Lite 候选与相同官方版本在固定硬件和等价配置下重复比较
- **THEN** 镜像体积至少降低 25%、冷启动至少缩短 20%、空闲 RSS 至少降低 30%、空闲 CPU 长期接近 0，并记录原始值、方法和波动

#### Scenario: 插件前后资源分别记录
- **GIVEN** P115StrmHelper 由用户手动安装并可能引入额外依赖
- **WHEN** 生成候选资源报告
- **THEN** 空插件基础镜像与安装目标插件后的状态分别测量，不把插件后依赖归为基础镜像永久节省

#### Scenario: 官方发布工作流不被复用
- **WHEN** 准备 Lite 候选构建
- **THEN** 不触发官方 DockerHub、`latest`、Release 删除/重建流程；任何私有 GHCR 工作流都需另行审查批准
