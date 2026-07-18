## ADDED Requirements

### Requirement: 生命周期必须在导入启动所有者之前执行固定 Lite 门控
正常 Lite 生命周期 MUST 在导入各启动 initializer 或其业务依赖之前使用固定 capability profile 决定所有者。系统 MUST 保留 Router、ModuleManager、EventManager、PluginManager、Lite Scheduler、Monitor 和 Lite Command，并 MUST 在导入前拒绝 Agent、Workflow、Display/Browser、Redis 及其关闭所有者。环境变量、SQLite 历史配置和未知 initializer MUST NOT 扩大固定集合。

#### Scenario: 干净环境缺少禁用依赖仍可导入生命周期
- **GIVEN** 干净解释器不提供动态站点资源、Agent、Workflow、Redis、虚拟显示和下载器专属依赖
- **WHEN** 系统导入 `app.startup.lifecycle`
- **THEN** 导入成功，禁用包及其子模块未进入 `sys.modules`

#### Scenario: 正常启动只初始化固定所有者
- **GIVEN** Lite 非安全模式且使用空的目录、消息和媒体服务器条件配置
- **WHEN** lifespan 进入启动阶段
- **THEN** Router、Module、Event、Plugin、Lite Scheduler、Monitor 和 Lite Command 按规定初始化，Agent、Workflow、Display 和 Redis 从未导入或初始化

#### Scenario: 历史开关不能恢复禁用所有者
- **GIVEN** 旧配置仍将 AI Agent、Workflow、Redis 或浏览器相关开关设为启用
- **WHEN** Lite 计算启动所有者
- **THEN** 固定 capability profile 优先，禁用所有者不被导入、实例化或创建线程

#### Scenario: DoH 只在显式启用时加载
- **GIVEN** DoH 属于允许的系统网络辅助但 `DOH_ENABLE=false`
- **WHEN** Lite 启动和停止
- **THEN** DohHelper 不被导入或实例化；设置为 true 时才延迟加载并在关闭时释放线程池

### Requirement: 启动完成阶段不得自动下载插件或执行非必要统计外联
Lite MUST 仅初始化本地已存在且已启用的兼容插件、插件 API、事件、命令和定时任务。启动及其后台完成任务 MUST NOT 根据历史安装列表自动下载/升级插件、安装缺失依赖、刷新插件市场、发送插件/订阅/使用统计或预取 GitHub 用户权限。插件市场、安装、升级和依赖操作 MUST 只由经过既有管理员认证的显式请求触发。

#### Scenario: 缺少 P115StrmHelper 时正常启动
- **GIVEN** 历史配置或产品文档将 P115StrmHelper 标为目标插件，但本地没有插件代码
- **WHEN** Lite 启动并完成后台初始化
- **THEN** 核心启动成功，不访问插件市场、不下载插件或依赖，也不伪造插件已运行

#### Scenario: 本地兼容插件保留官方扩展点
- **GIVEN** 一个已手动安装、已启用且兼容的本地插件声明 API、消息命令和定时服务
- **WHEN** PluginManager 和 Lite Scheduler 初始化
- **THEN** 插件实例、API、命令和定时服务按官方扩展点注册且不需要自动市场同步

#### Scenario: 显式管理员安装仍可工作
- **GIVEN** 已认证管理员在插件页面明确请求安装或升级插件
- **WHEN** 调用既有插件安装入口
- **THEN** 系统沿用既有认证、兼容性检查和安装结果，不因关闭启动自动同步而禁用手动操作

#### Scenario: 启动不执行统计与权限预取
- **GIVEN** 旧环境仍开启插件统计、订阅统计或使用统计并保存 GitHub 请求头
- **WHEN** Lite 正常启动及运行周期任务
- **THEN** 不调用对应统计上报或 GitHub 用户预取方法，原始配置不被删除

### Requirement: Scheduler 必须使用固定系统任务矩阵和延迟任务工厂
Lite Scheduler MUST 仅允许 `mediaserver_sync`、`scheduler_job`、`clear_cache`、`data_cleanup`、`full_gc` 及运行中兼容插件声明的任务。`mediaserver_sync`、`data_cleanup` 和 `full_gc` MUST 只在各自有效条件满足时注册。任务 callable MUST 在固定任务被选择后才加载其最小所有者；配置值 MUST NOT 构造导入路径、函数名或未知任务。

#### Scenario: 空条件配置生成精确系统任务集合
- **GIVEN** 没有媒体服务器同步间隔、数据清理或内存回收配置，且没有插件任务
- **WHEN** Lite Scheduler 初始化
- **THEN** 只注册 `scheduler_job` 和 `clear_cache`，不注册任何其他系统任务

#### Scenario: 条件保留任务按配置加入
- **GIVEN** 存在启用媒体服务器并设置有效同步间隔，同时启用数据清理和正数内存回收间隔
- **WHEN** Lite Scheduler 计算任务集合
- **THEN** 精确加入 `mediaserver_sync`、`data_cleanup` 和 `full_gc` 各一次

#### Scenario: 禁用 owner 缺失不影响 Scheduler 导入
- **GIVEN** Subscribe、Recommend、Workflow、Agent、站点资源和下载器依赖一旦导入就抛出错误
- **WHEN** 导入并初始化 Lite Scheduler
- **THEN** Scheduler 成功运行且从未尝试导入这些 owner

#### Scenario: 未知配置不能注入任务
- **GIVEN** 历史配置包含未知任务 ID、函数名或类似 Python 路径的字符串
- **WHEN** Scheduler 重建任务集合
- **THEN** 未知值被忽略或明确拒绝，不触发动态导入且不出现在任务列表

### Requirement: 禁用系统定时任务必须不可注册和不可手动恢复
Lite MUST 固定移除 `subscribe_tmdb`、`subscribe_search`、`new_subscribe_search`、`subscribe_refresh`、`subscribe_follow`、`transfer`、`random_wallpager`、`recommend_refresh`、`plugin_market_refresh`、`subscribe_calendar_cache`、`agent_heartbeat`、`usage_report` 以及全部 `workflow-*` 任务。相关历史环境配置、配置重载、插件重载和手动启动请求 MUST NOT 恢复这些任务。

#### Scenario: 历史开关全部启用仍不注册
- **GIVEN** 旧订阅、推荐、Agent、Workflow、使用统计和插件市场周期刷新设置全部为启用
- **WHEN** Lite Scheduler 初始化或配置重载
- **THEN** 所有固定移除 ID 均不在内部任务表或 BackgroundScheduler 中

#### Scenario: 手动运行禁用任务失败关闭
- **GIVEN** 已认证调用方请求运行 `subscribe_refresh`、`transfer`、`agent_heartbeat` 或一个 `workflow-*` ID
- **WHEN** Scheduler 处理手动启动
- **THEN** 返回不存在或不支持的明确失败，不导入对应 Chain、不创建一次性任务

#### Scenario: 插件重载不能恢复周期市场刷新
- **GIVEN** 本地插件完成重载并重新注册自身服务
- **WHEN** Scheduler 更新该插件任务
- **THEN** 只更新该兼容插件声明的任务，`plugin_market_refresh` 仍不存在

### Requirement: Lite 内建消息命令必须由固定矩阵决定
Lite Command MUST 只注册 `/mediaserver_sync`、`/clear_cache`、`/restart`、`/version` 及运行中兼容插件声明的命令。Command 构造和命令集合生成 MUST NOT 导入或实例化 Scheduler、MessageChain、Site、Download、Subscribe、Skills、Agent 或 Transfer 等禁用命令所有者；保留命令 callable MUST 在实际执行时按固定 resolver 延迟获取。

#### Scenario: 内建命令集合精确
- **GIVEN** Lite 没有运行插件
- **WHEN** Command 初始化菜单命令
- **THEN** 内建集合精确等于四个固定管理命令

#### Scenario: 禁用命令从历史缓存消失
- **GIVEN** 旧进程状态或配置曾包含 `/cookiecloud`、`/sites`、`/subscribes`、`/downloading`、`/transfer`、`/redo`、`/clear_session`、`/stop_agent`、`/session_status` 或 `/skills`
- **WHEN** Lite 重建命令集合
- **THEN** 这些命令均不被广播或执行且不导入对应 owner

#### Scenario: 兼容插件命令继续注册
- **GIVEN** 手动安装并运行的兼容插件通过既有事件声明一个命令
- **WHEN** Command 合并并向消息渠道注册命令
- **THEN** 插件命令保留原插件 ID、描述和执行事件语义，与四个固定命令共同出现

#### Scenario: Command 构造不隐式启动 Scheduler
- **GIVEN** Scheduler 尚未初始化
- **WHEN** 系统仅构造 Command 或重建插件命令
- **THEN** Command 不创建 BackgroundScheduler 或导入禁用 Scheduler owner

### Requirement: 消息路由必须保留插件事件并拒绝非目标交互链
Lite MessageChain MUST 保留官方渠道解析后的身份字段、插件输入、插件回调、固定斜杠命令、通知发送以及普通文本 `UserMessage` 事件。顶层导入和普通文本路由 MUST NOT 加载或调用 Agent/LLM、Voice、Download、Search、Site、Skills、Subscribe、Workflow 或传统媒体搜索交互。没有插件消费普通文本时 MUST NOT 回退到已移除能力。

#### Scenario: 115 分享链接进入插件事件
- **GIVEN** 官方消息渠道已通过既有白名单和权限判断，并收到普通 115 分享链接文本
- **WHEN** Lite MessageChain 处理消息
- **THEN** 发送一次 `UserMessage`，保留 `text`、`userid`、`channel`、`source`、`chat_id` 和 `reply_to_message_id`，不启动搜索、下载或 Agent

#### Scenario: P115 插件输入继续定向派发
- **GIVEN** 运行中的兼容插件建立了一个待输入会话
- **WHEN** 同一用户通过原渠道发送后续文本或取消指令
- **THEN** MessageChain 通过既有 `MessageAction` 结构只派发给目标插件并维持超时/取消语义

#### Scenario: 固定命令只产生命令事件
- **GIVEN** 用户发送 `/version` 或兼容插件命令
- **WHEN** MessageChain 处理斜杠文本
- **THEN** 发送既有 `CommandExcute` 事件，不导入禁用交互 Chain

#### Scenario: 语音和 AI 前缀不能恢复禁用能力
- **GIVEN** 历史配置仍开启全局 AI 或用户发送语音、`/ai`、`/skills` 文本
- **WHEN** Lite 处理消息
- **THEN** 系统返回不支持或普通插件事件语义，不导入语音模型、Agent、LLM 或 Skills

### Requirement: Monitor 与 TransferChain 必须保留整理能力且导入安全
Lite MUST 保留 Monitor 对 Local 和已配置网盘目录的监控，并继续使用现有 TransferChain 执行元数据识别、文件整理和历史记录。导入 Monitor 或 TransferChain MUST NOT 导入 Agent、Subscribe、Search、Site、Download、Skills、Workflow 或动态站点资源。仅服务于禁用能力的 TransferChain 路径 MUST 固定失败关闭或在非 Lite capability 下延迟加载。

#### Scenario: 导入 Monitor 不加载禁用链
- **GIVEN** 禁用 Chain 和动态站点资源均不可用
- **WHEN** 导入 `app.monitor` 和 `app.chain.transfer`
- **THEN** 导入成功，禁止前缀未进入 `sys.modules`

#### Scenario: Local 文件事件继续整理
- **GIVEN** 配置了有效 Local 监控目录并产生符合过滤条件的媒体文件事件
- **WHEN** Monitor 处理稳定文件
- **THEN** 调用 TransferChain 的保留整理路径，完成既有元数据、命名、文件操作和历史记录语义

#### Scenario: 已配置 U115 监控继续工作
- **GIVEN** U115 已配置并存在有效网盘监控目录
- **WHEN** Monitor 执行快照差异并发现新文件
- **THEN** 仅使用已加载 U115/StorageChain 和保留 TransferChain，不导入其他网盘或下载器

#### Scenario: 无目录配置不创建后台资源
- **GIVEN** Directories 为空或全部无效
- **WHEN** Monitor 初始化或重载
- **THEN** 不创建 watcher 线程、快照 BackgroundScheduler 或周期网盘扫描

### Requirement: 插件任务和消息扩展不得恢复固定禁用核心能力
运行中插件的命令、事件和定时任务 MUST 只在插件已通过 Lite 兼容检查且本地存在时注册。插件声明 MUST NOT 使核心重新导入固定禁用的 Agent、PT、站点、下载器、订阅、Redis、Workflow、FFmpeg 或浏览器能力；依赖这些能力的插件 MUST 被阻止运行并提供兼容原因。

#### Scenario: 兼容 P115 插件保留扩展
- **GIVEN** P115StrmHelper 已手动安装、通过兼容检查并声明消息事件和定时服务
- **WHEN** Lite 启动插件扩展
- **THEN** 其插件范围内事件和任务注册成功，核心固定禁用模块仍未导入

#### Scenario: 不兼容插件不能借任务声明恢复能力
- **GIVEN** 一个插件依赖下载器、Redis 或 Workflow 并声明命令和定时任务
- **WHEN** PluginManager 评估并启动插件
- **THEN** 插件被阻止运行，命令和任务均不注册，并返回具体兼容性原因

#### Scenario: 未知插件任务不能成为系统任务
- **GIVEN** 插件提供任意自定义任务 ID
- **WHEN** Scheduler 注册插件服务
- **THEN** 任务带有该运行插件的所有权且只调用插件提供 callable，不被解释为系统导入路径

### Requirement: 启动与关闭必须按实际所有者对称且隔离错误
生命周期 MUST 记录实际成功启动的所有者，并 MUST 在关闭时按依赖逆序停止这些所有者。任一停止异常 MUST 被记录并隔离，后续所有者、数据库、共享 HTTP 和日志关闭仍执行。禁用或未启动所有者 MUST NOT 为执行 stop 而被导入或实例化。

#### Scenario: 正常关闭不导入禁用 owner
- **GIVEN** Agent、Workflow、Display 和 Redis 从未启动
- **WHEN** lifespan 退出
- **THEN** 关闭流程不导入或调用这些 owner，并释放 Command、Monitor、Scheduler、Plugin、Module、Event、DoH、Thread、Message、Database 和 HTTP 中实际存在的资源

#### Scenario: 单个停止失败继续清理
- **GIVEN** Monitor、Scheduler、Plugin、Module 或共享 HTTP 关闭中的任一步抛出异常
- **WHEN** 系统执行关闭编排
- **THEN** 错误被记录一次，其余已启动所有者仍各停止一次，Logger 最后关闭

#### Scenario: 配置重载不遗留 Scheduler 或 watcher
- **GIVEN** Scheduler 或 Directories 配置发生多次并发变化
- **WHEN** 对应所有者串行重建
- **THEN** 旧 BackgroundScheduler 和 watcher 被停止，新集合只创建一次且最终与最新配置一致

#### Scenario: 安全模式保持最小启动
- **GIVEN** `MOVIEPILOT_SAFE_MODE=true`
- **WHEN** Lite 启动并停止
- **THEN** Router、核心 Module 和必要关闭资源工作，Plugin、Scheduler、Monitor 和 Command 均不启动或为关闭而导入

### Requirement: 调度诊断、配置与回退必须保持安全和无破坏性
现有 Scheduler 列表、进度和手动运行 API MUST 保持路径、认证依赖和响应模型，但 MUST 只反映实际 Lite 系统任务及兼容插件任务。门控 MUST 只读取配置，MUST NOT 新增数据库迁移、删除禁用历史任务/命令配置或写入真实凭据；回退同版本官方代码后原数据 MUST 仍可解释。

#### Scenario: Scheduler API 只展示实际任务
- **GIVEN** SQLite 和环境变量包含禁用任务历史配置
- **WHEN** 已认证调用方查询 Scheduler 列表
- **THEN** 响应只包含固定保留系统任务和兼容插件任务，字段和进度语义保持

#### Scenario: 未认证调用不能运行任务
- **GIVEN** 调用方没有有效管理员会话或 API Token
- **WHEN** 请求列出或手动运行任一 Scheduler 任务
- **THEN** 既有认证依赖先拒绝请求，门控不提供绕过路径

#### Scenario: 历史配置原样保留
- **GIVEN** `/config` 副本包含 Subscribe、Download、Workflow、Agent、Redis、使用统计和旧命令相关配置
- **WHEN** Lite 启动、重载、停止并再次启动
- **THEN** 禁用内容不进入运行时，但原始持久化记录和值不被删除或改写

#### Scenario: 普通测试零真实出站
- **GIVEN** CI 覆盖启动、Scheduler、消息、插件、Monitor 和 Transfer 流程
- **WHEN** 运行所有新增和回归测试
- **THEN** 插件市场、115、元数据、媒体服务器、消息渠道和 MoviePilot 服务端全部使用 mock，且日志与差异中没有 Token、Cookie、密码或真实 `/config`
