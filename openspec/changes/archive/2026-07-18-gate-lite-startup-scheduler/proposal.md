## Why

模块发现已经在导入前拒绝 PT、下载器、Redis、PostgreSQL 和未配置服务包，但正常应用生命周期仍会顶层导入完整 Scheduler、Command、Workflow、Agent、Monitor 及其传递依赖。当前 `app.scheduler` 直接导入 Subscribe、Recommend、Transfer 和 Workflow 链，`app.command` 又直接导入站点、下载、订阅、Skills 和完整消息链；Monitor 所需的 TransferChain 也在导入期加载 Agent 与 Subscribe。结果是禁用能力仍可通过保留入口重新进入解释器，甚至在干净 Lite 环境缺少动态站点资源时仅导入 Scheduler 就失败。

这一层必须先于 Python 依赖和 Docker 裁剪完成，否则删除任何非目标依赖都会把潜在浪费变成启动故障。与此同时，消息渠道接收 115 分享链接、插件命令、网盘/本地目录监控、媒体服务器同步和插件定时任务都属于保留能力，不能通过整体关闭 Scheduler、Command 或 Monitor 来伪造精简。

## What Changes

- 将应用启动所有者改为固定 Lite 矩阵：保留路由、模块、事件、插件、Lite Scheduler、目录监控和 Lite 消息命令；Agent、Workflow、虚拟显示、Redis 连接和非目标服务端统计在导入前拒绝。
- 让 Scheduler 使用固定系统任务矩阵和延迟任务工厂，只保留媒体服务器同步、模块公共定时钩子、缓存/数据清理、可选内存回收及兼容插件注册的定时任务；移除订阅、下载转移、推荐、壁纸、Agent、Workflow、使用统计和周期插件市场刷新。
- 使 Command 和 MessageChain 在模块顶层不导入站点、搜索、下载、订阅、Agent、LLM、MCP、Skills 或 Workflow；只注册固定 Lite 管理命令和运行中兼容插件提供的命令，普通文本、回调和插件输入继续通过既有事件交给插件，以保留 P115StrmHelper 分享链接链路。
- 使 Monitor 依赖的 TransferChain 在导入期只加载网盘整理、元数据和文件操作所需对象；Agent、Subscribe 和下载器相关路径必须固定禁用或仅在对应能力允许时延迟加载，不能因目录监控恢复禁用能力。
- 停止启动时自动下载/更新插件或安装缺失依赖，插件市场查询、安装和升级只由显式管理员操作触发；已存在且已启用的本地插件、插件 API、事件、命令和定时任务继续初始化，P115StrmHelper 缺失时核心正常启动。
- 让关闭流程只停止实际启动的所有者并继续隔离单个停止错误；安全模式语义保持，未启动禁用所有者不得为关闭而导入。
- 收窄 Scheduler 和命令诊断结果到实际 Lite 集合；历史环境变量、SQLite 配置或未知任务 ID 不能恢复禁用任务或命令。
- 新增完全离线的 pytest 契约和独立进程导入基线，证明正常生命周期不再导入禁用链路，保留的网盘整理、插件消息、通知、媒体服务器与目录监控仍可工作。
- **BREAKING**：系统定时任务列表和内建消息命令不再包含订阅、下载、站点、推荐、Agent、Skills、Workflow、使用统计或自动插件市场刷新相关项目；启动时不再自动下载插件代码和依赖。
- 本变更不删除源码或依赖清单，不修改数据库 Schema、前端仓库或 Docker 构建，也不执行真实 115、插件市场、元数据、消息渠道或媒体服务器请求。

## Capabilities

### New Capabilities

- `lite-startup-scheduler-gating`: 定义 Lite 启动所有者、定时任务、消息命令和保留链路在导入前门控，以及插件手动安装和关闭对称性的契约。

### Modified Capabilities

无。

## Impact

- 启动编排：预计修改 `app/startup/lifecycle.py`、`app/startup/modules_initializer.py`、`app/startup/scheduler_initializer.py`、`app/startup/command_initializer.py` 和插件启动辅助逻辑；固定产品策略继续读取 `app/core/capability.py`，不由环境变量重写。
- Scheduler：预计重构 `app/scheduler.py` 的顶层导入、系统任务注册、配置监听、Workflow/Agent 事件入口和手动任务启动失败语义；插件任务仍由运行中兼容插件声明。
- 消息：预计修改 `app/command.py` 与 `app/chain/message.py` 的固定命令和延迟导入边界；官方消息渠道身份、白名单、管理员判断、通知发送及 `UserMessage`/`MessageAction` 插件事件保持。
- 整理与监控：预计修改 `app/chain/transfer.py` 和 `app/monitor.py` 的导入边界，不改变 Local/U115 文件整理、元数据识别、目录配置或整理历史数据结构。
- 插件：运行中本地插件、插件 API、插件命令和插件定时服务保留；启动后台不得自动下载缺失插件或安装依赖，手动安装/升级 API 保持既有认证。
- API：不新增路由；Scheduler 列表、手动运行和命令注册只反映实际 Lite 集合，需同步 REST/MCP 说明及兼容文档。
- 配置与数据库：不新增迁移，不删除 Workflow、Subscribe、Download 或 Agent 历史记录和配置；固定禁用配置只不再被消费，便于回退官方版本。
- 依赖与 Docker：不修改依赖文件或镜像。本变更输出可安全删除的传递导入证据，实际依赖裁剪继续单独实施。
- 资源：目标是消除当前约 143–146 MiB 的启动导入增量中的非目标部分并阻止无效周期任务；完整产品资源指标仍在后续依赖/Docker 候选中验收。
- 安全：未知任务、命令和历史配置默认拒绝；测试使用临时配置、模拟插件和假 Scheduler，禁止真实出站和真实凭据。
- 上游同步：保留官方文件结构，优先以小型固定矩阵、延迟工厂和方法级门控隔离差异；上游新增启动所有者或系统任务默认不进入 Lite，必须先分类和补测。
