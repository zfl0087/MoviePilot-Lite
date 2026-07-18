## Why

Lite 已在路由、模块发现、应用生命周期、Scheduler 和消息链的导入之前固定禁用 PT、下载器、Agent、Workflow、Redis、PostgreSQL 和浏览器模拟等能力，但正式运行依赖仍与官方完整版本基本一致。结果是已经无法进入的能力仍把 LangChain/模型 SDK、Playwright、下载器客户端、数据库驱动和 Windows 托盘库带入基础镜像，既浪费磁盘和构建时间，也扩大依赖漏洞与上游升级面。

当前审计还发现两个必须在删除依赖前处理的保留链耦合：消息链仍可通过顶层 `TorrentHelper` 导入 `torrentool`；数据库初始化仍会根据历史 `DB_TYPE=postgresql` 选择 PostgreSQL。若只删除清单条目，干净 Lite 环境将出现启动或导入故障。因此本变更必须同时固定正式运行依赖集合、解除残余传递导入并让历史配置安全失败关闭。

## What Changes

- 从 `requirements.in` 固定移除 24 个非目标直接运行依赖：14 个 Agent/LLM 根依赖、4 个 PT/下载器根依赖、2 个浏览器/虚拟显示根依赖、3 个 Redis/PostgreSQL 根依赖和 1 个 Windows 托盘根依赖。
- 将仅供官方禁用源码回归测试使用的上述包放入 `requirements-dev.in` 的独立兼容测试分组；`requirements.txt` 继续只委托正式运行入口，不新增平行的 Lite 运行清单。
- 清除保留启动、消息、整理、插件和 API 链中的残余禁用依赖导入；类型注解使用 `TYPE_CHECKING`、协议或延迟导入，固定禁用路径在解析依赖前拒绝。
- 固定 Lite 使用 SQLite 和进程内缓存。历史 PostgreSQL/Redis 配置只读保留但不再选择驱动、连接后端或触发依赖导入，也不改写 `/config`。
- 保留 U115/其他官方存储适配器源码、元数据识别、文件整理、插件框架、全部官方消息通知渠道、Emby/Jellyfin/Plex、管理员认证和容器重启所需依赖。
- 保持插件依赖由管理员手动安装流程处理。P115StrmHelper 不进入基础依赖、不自动安装；核心在插件及其依赖缺失时仍正常启动。
- 新增固定禁止根依赖契约、干净运行环境导入/启动测试、保留能力回归、依赖安全扫描和同口径资源测量。
- **BREAKING**：Lite 正式运行环境不再提供 Agent/LLM、浏览器模拟、PT/下载器、Redis、PostgreSQL 或 Windows 原生托盘的 Python 包；依赖这些能力的插件必须被兼容检查拒绝或自行声明其纯插件依赖，且不得借此恢复固定禁用的核心能力。
- 本变更不修改 Dockerfile、容器更新器、系统包、FFmpeg/FFprobe、前端仓库、数据库 Schema、消息渠道行为或真实 P115 插件实现。

## Capabilities

### New Capabilities

- `lite-runtime-dependency-profile`: 定义 Lite 基础运行依赖的固定禁止集合、运行/开发分层、缺失依赖行为、插件依赖边界和资源验收口径。

### Modified Capabilities

无。

## Impact

- 依赖文件：预计修改 `requirements.in` 和 `requirements-dev.in`；`requirements.txt` 保持委托结构。
- 运行代码：预计修改数据库选择、保留消息/Chain 的类型导入或延迟导入边界，以及干净环境暴露出的其他少量传递导入；不得删除上游禁用源码目录。
- 正式运行：固定 SQLite、进程内缓存和 Linux Docker 目标；历史 Redis/PostgreSQL/Windows 配置不被执行或改写。
- 保留功能：U115 依赖的 `oss2`、SMB/Rclone、元数据中文处理、通知渠道 SDK、PlexAPI、管理员 MFA/Passkey 和容器重启所需 Docker SDK继续保留。
- 插件：市场查询、手动安装、升级、依赖安装、API、消息事件、命令和定时服务入口保持；P115StrmHelper 及其第三方依赖不预装。
- 测试：开发依赖环境继续覆盖官方完整源码测试；另建只安装 `requirements.in` 的干净环境证明禁用包真实缺失时 Lite 可启动。
- 安全：运行与开发依赖入口都必须通过项目规定的 `safety` 扫描，不提交报告中的环境凭据或真实 Token。
- 资源：以相同 Python、平台和测量脚本比较依赖闭包、安装体积、启动导入、RSS、模块和线程；Docker 镜像指标留给后续独立变更。
- 上游同步：保留官方文件名与源码结构；固定测试在上游重新引入禁止运行依赖时失败关闭，要求先分类再合并。
