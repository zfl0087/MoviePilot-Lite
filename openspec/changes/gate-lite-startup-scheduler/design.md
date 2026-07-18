## Context

当前生命周期在模块顶层导入全部 initializer。`scheduler_initializer.py` 顶层导入 `app.scheduler`，后者再顶层导入 MediaServer、Recommend、Subscribe、Transfer、Workflow 等 Chain；Subscribe 继续导入 Search 和动态 `app.helper.sites`。`command_initializer.py` 顶层导入 `app.command`，Command 又导入 Download、Site、Skills、Subscribe、Transfer、Message 和 Scheduler。`modules_initializer.py` 顶层导入 Redis、Display、Agent initializer，并在正常启动时实例化虚拟显示、DoH、Agent 和多项服务端统计状态。即使 capability profile 已固定禁用这些能力，门控发生得太晚或根本没有发生。

两个保留入口存在必要耦合。目录监控调用 TransferChain 完成自动整理，而 TransferChain 顶层导入 Agent 和 Subscribe；消息渠道调用 MessageChain，后者顶层导入 Agent/LLM、Download、Search、Site、Skills、Subscribe 和 Transfer。简单地在 lifecycle 中不调用 Workflow 或 Agent 不能阻止这些传递导入；简单地关闭 Monitor 或 Command 又会破坏网盘整理和 115 分享链接插件事件。

插件当前在启动后执行 `sync_plugins()` 和 `install_plugin_missing_dependencies()`，会依据历史安装列表访问插件市场并自动下载插件代码或依赖。Lite 的插件策略是管理员手动安装，P115StrmHelper 必装但不得预装、自动安装或后台下载，因此启动只能加载本地已存在插件。

## Goals / Non-Goals

**Goals:**

- 在导入禁用 initializer、Chain、动态资源或第三方依赖之前应用固定 capability 门控。
- 正常启动保留模块、事件、插件、目录监控、消息命令、媒体服务器和必要 Scheduler，同时不加载 Agent、Workflow、PT/站点、订阅、下载器、推荐、Redis 或虚拟显示链路。
- 固定系统定时任务和内建命令集合，未知或历史配置不能扩大范围。
- 保留普通消息到 `UserMessage`、插件输入到 `MessageAction`、插件命令注册和插件定时任务，使手动安装的 P115StrmHelper 可以继续接收 115 分享链接。
- 保留 Local/网盘目录监控和实际文件整理，并把 TransferChain 的非目标依赖移出导入期。
- 启动时不自动下载插件、升级插件或安装插件依赖；显式管理员安装/升级流程保持。
- 关闭流程与实际启动集合对称，单个停止错误不阻断其余资源释放。
- 用干净独立进程证明禁用链路缺失时生命周期仍可导入、启动和停止，并记录资源前后基线。

**Non-Goals:**

- 不物理删除 Agent、Workflow、Subscribe、Download、Site、Redis 或其他上游源码。
- 不修改 Python/Node 依赖清单、Dockerfile、前端仓库或数据库 Schema。
- 不重写消息渠道身份、白名单、管理员权限、通知格式或第三方 SDK。
- 不实现 P115StrmHelper 内部转存/STRM 逻辑；只保证核心事件、插件命令和定时服务通路不被裁剪。
- 不恢复基于消息的媒体搜索、站点管理、订阅、下载、AI 对话、语音或 Skills 交互。
- 不运行真实插件市场、115、元数据、媒体服务器或消息渠道 Canary；真实验证属于后续候选镜像阶段。

## Decisions

### 1. 生命周期按固定所有者矩阵延迟导入

`app.startup.lifecycle` 只在模块顶层导入标准库、FastAPI、核心配置/日志和轻量 capability 查询。其他 initializer 在对应保留分支内延迟导入，避免“先导入、后判断”。固定矩阵如下：

| 所有者 | Lite 决定 | 条件 |
|---|---|---|
| Router / ModuleManager / EventManager | 保留 | 始终 |
| PluginManager、插件 API、插件事件 | 保留 | 非安全模式 |
| Lite Scheduler | 保留 | 非安全模式 |
| 目录 Monitor | 保留 | 非安全模式；无目录配置时不得创建 watcher |
| Lite Command | 保留 | 非安全模式且 Messaging 能力固定启用 |
| DoH | 保留 | 仅 `DOH_ENABLE=true` 时延迟导入和初始化 |
| Workflow initializer | 禁用 | 固定不导入、不初始化、不停止 |
| Agent initializer | 禁用 | 固定不导入、不创建线程、不停止 |
| DisplayHelper / 浏览器显示 | 禁用 | 固定不导入、不初始化、不停止 |
| Redis / AsyncRedis | 禁用 | 固定不导入、不连接、不为关闭而导入 |
| 订阅/插件/使用统计预上报 | 禁用 | 固定不在启动或周期任务执行 |

安全模式继续跳过插件、Scheduler、Monitor 和 Command；关闭阶段使用已启动所有者记录或同一固定矩阵，只停止可能已启动的对象。没有为禁用 owner 创建空壳实例，因为空壳仍会让调用方误以为能力存在。

DoH 服务可能被元数据和网盘 API 的用户配置使用，不等同于浏览器自动化，因此保留为显式环境配置的条件 owner。Windows frozen 前端辅助不在本变更扩大支持范围，保持现有平台 no-op 语义并留给前端/Docker 阶段处理。

### 2. 启动完成任务不得执行自动插件下载或统计外联

保留 `PluginManager().start()`、本地插件 API 注册、插件事件、命令和服务注册。`init_extra()` 不再调用 `sync_plugins()`、`install_plugin_missing_dependencies()`、插件安装统计、订阅统计、GitHub 用户预取或使用统计上报；它只完成本地系统修改标记与重启完成通知等无外联收尾。

插件市场列表在管理员打开市场或显式刷新时按既有 API 获取；安装、升级和依赖安装只由经过既有管理员认证的显式操作触发。历史 `UserInstalledPlugins` 记录保留，但本地代码不存在时启动不据此下载。P115StrmHelper 缺失时启动成功，消息事件没有对应插件消费者；本变更不伪造插件成功结果。

### 3. Scheduler 使用固定任务描述和延迟工厂

`app.scheduler` 顶层不得导入禁用 Chain。Scheduler 以固定任务描述表计算系统任务，并在创建保留任务 callable 时才导入最小目标所有者。配置值只能改变规定任务的时间或启停条件，不能提供导入路径、函数名或新增任务 ID。

保留系统任务：

- `mediaserver_sync`：仅配置有效正整数间隔且存在启用媒体服务器时注册。
- `scheduler_job`：保留模块公共定时钩子，供实际运行模块实现轻量维护任务。
- `clear_cache`：保留模块缓存清理。
- `data_cleanup`：仅 `DATA_CLEANUP_ENABLE=true` 时注册；历史表按既有保留期处理，不删除配置。
- `full_gc`：仅 `MEMORY_GC_INTERVAL` 为有效正数时注册。
- 运行中兼容插件声明的任务：保留插件 ID、触发器、错误隔离和重载语义。

固定移除系统任务：`subscribe_tmdb`、`subscribe_search`、`new_subscribe_search`、`subscribe_refresh`、`subscribe_follow`、`transfer`、`random_wallpager`、`recommend_refresh`、`plugin_market_refresh`、`subscribe_calendar_cache`、`agent_heartbeat`、`usage_report`，以及全部 `workflow-*` 任务。插件市场改为显式按需获取，下载文件转移任务不能与网盘/目录监控整理混为一谈。

Scheduler 的 `CONFIG_WATCH` 只保留实际影响上述任务的配置。旧 SUBSCRIBE、AI_AGENT、USAGE 或其他禁用设置变化不能重建或恢复任务。手动 `start(job_id)` 对不存在或禁用 ID 返回明确失败，不导入对应 owner；列表只展示实际系统和兼容插件任务。

### 4. Command 使用固定内建命令矩阵并延迟解析 callable

Lite 内建命令固定为：

- `/mediaserver_sync`
- `/clear_cache`
- `/restart`
- `/version`

运行中兼容插件通过既有 `CommandRegister` 事件声明的命令继续合并，P115StrmHelper 可以保留自身命令。固定移除 `/cookiecloud`、`/sites`、`/subscribes`、`/downloading`、`/transfer`、`/redo`、`/clear_session`、`/stop_agent`、`/session_status`、`/skills` 及任何禁用能力命令。

Command 构造不得实例化 Scheduler 或禁用 Chain。Scheduler 类命令在实际执行时按固定 ID获取 Scheduler；函数命令使用小型固定 resolver 延迟获取 SystemChain。未知或禁用命令不通过历史注册缓存恢复。消息渠道的命令广播、用户/管理员检查和插件命令事件保持官方逻辑。

### 5. MessageChain 收敛为通知、固定命令和插件事件路由

MessageChain 顶层只保留消息解析、通知发送、渠道能力、插件交互和事件所需依赖。Agent/LLM、语音、Download、Search、Site、Skills、Subscribe、Workflow 以及传统媒体搜索交互不在 Lite 路由，不能在模块导入时出现。

消息处理顺序保持安全边界：渠道模块完成官方身份/白名单判断 → MessageChain 解析消息 → 插件输入/回调优先 → 固定斜杠命令发送 `CommandExcute` → 普通文本发送 `UserMessage`。`UserMessage` 必须保留 `text`、`userid`、`channel`、`source`、`chat_id` 和 `reply_to_message_id`，使 P115StrmHelper 能按官方事件契约识别分享链接。没有兼容插件消费普通文本时核心不启动搜索、下载或 AI 回退。

移除能力的历史交互会话不能恢复对应 Chain。图片/文件仍可按插件输入的既有结构传递；Voice Processing 固定禁用，音频输入不得触发 Agent 或语音模型导入。

### 6. TransferChain 必须成为可由 Monitor 安全导入的保留整理链

TransferChain 是现有文件整理领域所有者，Monitor 继续通过它调用 `do_transfer()`；不新增第二套 Lite 整理 Chain。TransferChain 顶层保留 Media、Storage、TMDB、元数据、目录、历史和文件 Schema，移除 Agent 与 Subscribe 的顶层依赖。仅服务于订阅、下载或 Agent 提示的历史方法必须在固定能力判断后延迟导入，Lite 下直接返回明确不支持或走不依赖禁用能力的整理分支。

实施以独立进程 `sys.modules` 断言为门禁：导入 Monitor、TransferChain、MessageChain、Command、Scheduler 和完整 lifecycle 后，不得出现 `app.agent`、`app.workflow`、`app.chain.subscribe`、`app.chain.search`、`app.chain.download`、`app.chain.site`、`app.chain.skills`、`app.chain.recommend`、`app.helper.sites`、`app.helper.redis`、`app.helper.display` 及其子模块。若保留整理方法仍真实需要某依赖，必须先重新分类产品能力并取得批准，不能用测试垫片掩盖。

### 7. Monitor 保留配置语义并避免空配置资源

Monitor 继续读取 `Directories`、创建 Local watcher 或远端存储快照任务，并将文件事件交给 TransferChain。无有效目录配置时不得创建 BackgroundScheduler、watcher 线程或快照文件；配置移除后必须停止并 join watcher、关闭 Scheduler。远端存储只使用 ModuleManager 已允许的存储适配器，未知历史 storage 不能触发导入。

本变更不改变目录 Schema、整理模式、文件过滤、历史记录或元数据识别语义。下载器完成目录的周期 `transfer` 任务已经固定移除，不影响目录监控检测到的本地/网盘文件整理。

### 8. 生命周期关闭和配置重载保持对称

启动所有者按实际成功状态记录；初始化失败的 owner 不进入已启动集合。关闭按逆向业务依赖顺序执行并隔离异常：Command/Monitor/Scheduler/Plugins → Modules/Event/DoH/Thread/Message/Database/HTTP。禁用 Agent、Workflow、Display、Redis 不在关闭路径导入。

Scheduler 重载使用既有锁先停止旧 scheduler，再按固定矩阵重建；插件重载只更新该插件的任务和命令，不恢复周期插件市场刷新。全局停止信号、安全模式和 Logger 最后关闭的现有保证保持。

### 9. API 与诊断只反映实际 Lite 运行集合

现有 Scheduler 列表、进度和手动运行端点保持路径、认证依赖和响应模型，但只返回实际系统/插件任务。禁用 ID 返回既有失败响应或明确“不支持”，不能临时构造任务。插件安装/升级端点保持管理员认证；启动策略变化不新增匿名安装入口。

`docs/mcp-api.md`、`docs/ARCHITECTURE.md`、`docs/COMPATIBILITY.md` 和 `PROJECT_BRIEF.md` 同步记录固定任务/命令矩阵、插件手动安装、消息事件和启动完成状态。前端本阶段不改，但后续 Scheduler/命令页面必须消费实际返回集合。

实现审计发现，保留 Router 并不等同于只导入 API 汇总模块：`app.api.apiv1` 还会递归导入 history、system、mediaserver 等保留端点。因而这些端点中仅服务于 Agent、站点、搜索和下载器的对象也必须在 capability 判断后延迟导入。独立进程测试直接导入完整 `app.api.apiv1`，以实际路由树而不是单个端点垫片作为门禁。

历史配置可能仍把 `CACHE_BACKEND_TYPE` 设为 Redis。Lite 的缓存工厂必须先检查固定 REDIS capability，再决定是否导入或连接 Redis；能力关闭时忽略该历史值并回退文件/内存缓存，不改写用户配置。这样启动、API 和关闭阶段都不会因旧配置恢复 Redis 链路。

### 10. 验证使用导入失败、精确集合和资源基线

先写 pytest-native 失败测试：缺少 `app.helper.sites`、Agent、Workflow、Redis、Display 及下载器依赖时仍可导入/启动/停止；Scheduler 和 Command 集合精确；普通 115 链接产生插件事件；P115StrmHelper 缺失不下载；Monitor 保留整理。测试用假 BackgroundScheduler、假插件和临时配置，禁止真实网络。

修改启动、Scheduler、Command、MessageChain、TransferChain 和 Monitor 后运行定向 pytest、全量 pytest、修改文件 Pylint 及 `pylint app/`，逐项比较现有 Windows 基线。相同解释器和空配置下重复记录 lifecycle 导入耗时、RSS、新模块数和线程；还要启动/停止一次实际 Lite owner 集合，确认没有后台任务泄漏。资源结果只证明本层收益，不替代 Docker 最终指标。

## Risks / Trade-offs

- [范围比单一 Scheduler 更大] → Command、MessageChain、Monitor 和 TransferChain 会传递导入同一批禁用能力；不处理会使门控失真。通过分组测试和小步骤提交控制风险，不缩小真实边界。
- [TransferChain 历史方法高度耦合 Agent/Subscribe] → 保留文件整理主路径，禁用路径改为能力判断后的延迟导入或明确失败；不复制整理实现。
- [插件启动不再自动恢复缺失代码] → 符合手动安装策略；UI/API 必须清楚显示本地缺失，管理员显式安装后正常加载。部署文档后续说明持久化插件目录。
- [移除周期插件市场刷新导致列表非实时] → 打开市场或显式刷新时获取，避免空闲实例每 30 分钟外联。
- [公共 `scheduler_job` 可能调用插件外模块] → ModuleManager 已只包含 Lite 模块；调用范围受实际运行集合约束，并测试无禁用模块。
- [普通消息不再回退媒体搜索或 AI] → 这是产品范围内的预期 BREAKING 行为；插件事件和固定管理命令保留。
- [未知上游任务默认消失] → 这是 fail-closed 设计；同步上游时必须先分类、补测试和文档。
- [关闭时未导入禁用 owner 可能与旧测试假设冲突] → 测试改为断言实际 owner 对称性，不能为了调用 stop 而导入禁用代码。
- [资源收益仍低于最终指标] → 本阶段消除运行链路和传递导入，依赖/镜像物理裁剪在下一阶段完成。

## Migration Plan

1. 记录干净导入失败和带最小测试垫片的时间/RSS/模块/线程基线，建立禁止导入前缀清单。
2. 先为 lifecycle owner、Scheduler 任务、Command 集合、Message 插件事件、Monitor/Transfer 导入和插件手动安装编写失败测试。
3. 将 lifecycle 与 initializer 改为固定 owner 延迟导入，移除 Agent/Workflow/Display/Redis/统计启动副作用，并保持安全模式与关闭隔离。
4. 重构 Scheduler 为固定任务矩阵和延迟工厂，保留系统/插件任务，移除禁用任务和配置监听。
5. 收敛 Command/MessageChain，验证 P115StrmHelper 插件事件和命令通路；再隔离 TransferChain/Monitor 的禁用依赖并验证真实整理调用。
6. 停止启动插件自动下载和依赖安装，验证显式管理员安装/升级仍可用且插件缺失不影响核心。
7. 更新文档，运行定向、全量、Pylint、OpenSpec、差异/秘密检查和离线启动两轮资源验证。
8. 实施提交、推送、OpenSpec 归档及后续 Canary/发布分别遵守用户批准检查点；本变更不构建或部署镜像。

## Open Questions

无。启动 owner、系统任务、内建命令、插件手动安装、普通消息事件、Monitor/Transfer 保留边界和禁止导入前缀均依据现有产品决策固定；真实 P115StrmHelper Canary、依赖/Docker 和前端裁剪继续后续独立实施。
