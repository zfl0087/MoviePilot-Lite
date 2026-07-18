## Context

`ModuleManager.load_modules()` 当前调用 `ModuleHelper.load("app.modules")`。后者先导入、重载每个顶层包，再根据类方法过滤对象，因此过滤器不能阻止 qBittorrent、Transmission、Redis、PostgreSQL、PT Indexer 或未配置消息渠道的依赖进入解释器。`ModuleHelper.load_with_pre_filter()` 同样在检查候选类前完成了顶层导入，不是真正的包级预过滤。

第二层问题位于 `FileManagerModule.init_module()`：它扫描 `app.modules.filemanager.storages` 并导入 Local、U115、Alipan、Alist、Rclone、SMB 全部实现。仅配置 115 的实例仍会加载 `oss2`、`smbclient` 等无关依赖。现有 `Storages` 没有 `enabled` 字段，是否出现在配置列表就是远端存储的启用边界；Local 同时承担基础本地文件访问，是必要的轻量兜底。

消息和媒体服务器模块自身通过 `ConfigReloadMixin` 监听配置。若 ModuleManager 再做整表重载，管理器与模块实例会并发响应同一事件，可能重复停止和初始化。首次配置方面，配对前端会先提交 `Storages`、`Notifications` 或 `MediaServers`，再发起授权或测试；REST 调用仍需要能够按明确的官方存储类型完成首次授权，不能依赖启动时扫描全部适配器。

本变更只建立模块发现和适配器加载边界。`modules_initializer.py` 仍有 Redis Helper、Agent 等后续待裁剪启动所有者，Scheduler 和消息动作也仍有独立工作，因此不能把本变更宣传为整个应用已经完成运行链路或依赖裁剪。

## Goals / Non-Goals

**Goals:**

- 在任何候选顶层模块或存储适配器被导入前完成固定、可测试的 Lite 分类。
- 冷启动只导入无条件保留模块、已启用的消息/媒体服务器模块、Local 及已配置远端存储。
- 允许首次配置和 115 OAuth/API 只加载被明确请求的适配器。
- 让 Notifications、MediaServers、Storages 配置变化由单一生命周期所有者串行重建，停止旧活动资源且不重复初始化。
- 未知上游模块、未知配置类型和历史禁用配置默认不能扩大 Lite 能力。
- 保留模块源码、配置数据和官方回退能力，并提供后续依赖删除所需的导入证据。

**Non-Goals:**

- 不删除 `app.modules` 或存储适配器源码，不修改 Python 依赖锁文件或 Docker 构建。
- 不裁剪消息命令、Scheduler 剩余任务、Redis Helper、Agent initializer、插件能力检查或前端菜单。
- 不改变消息身份/白名单、媒体服务器操作、元数据识别、文件整理或存储 API 的业务语义。
- 不保证运行中已经导入的 Python 模块能够从 `sys.modules` 或解释器内存安全卸载；停用保证针对活动实例和资源。
- 不连接真实 115、消息渠道、媒体服务器或元数据服务；真实验证仍属于候选 Canary。

## Decisions

### 1. 通用加载器增加纯包名预过滤

`ModuleHelper.load()` 增加可选 `package_filter`，在拼接并调用 `importlib.import_module(full_package_name)` 之前接收枚举得到的子包名并作出决定。默认值保持“允许”，避免改变其他上游调用者；现有 `filter_func` 继续只负责导入后的类筛选。公开方法和类型别名使用上游命名风格，并补充中文 docstring 明确两个过滤阶段。

选择扩展现有 Helper，而不是在 ModuleManager 复制 `pkgutil` 扫描，是为了让文件整理的第二层适配器扫描复用同一安全原语。产品能力映射不放入 Helper，避免底层工具依赖 Lite taxonomy。

`package_filter` 抛错时对该候选采用 fail-closed 并记录不含配置秘密的日志。允许包自身导入失败仍沿用逐包隔离：记录明确失败，该包不进入模块集合，也不能触发扫描其他包作为回退。

### 2. 顶层模块使用固定白名单矩阵

ModuleManager 持有可审计的包策略，不从目录、环境变量或用户输入动态生成 Python 路径：

- 无条件保留：`bangumi`、`douban`、`fanart`、`filemanager`、`themoviedb`、`thetvdb`。
- 按启用通知配置保留：`discord`、`feishu`、`qqbot`、`slack`、`synologychat`、`telegram`、`vocechat`、`webpush`、`wechat`、`wechatclawbot`。
- 按启用媒体服务器配置保留：`emby`、`jellyfin`、`plex`。
- 固定拒绝：`filter`、`indexer`、`postgresql`、`qbittorrent`、`redis`、`rtorrent`、`subtitle`、`transmission`、`trimemedia`、`ugreen`、`zspace`。
- 任何未分类新包默认拒绝。

配置中的 `type` 只与上述固定表比较，不能作为模块路径。Notifications 和 MediaServers 只有 `enabled=true`、type 在允许表且基本 Schema 可解析时才选择包；同一类型多个实例只导入一次。历史 Downloaders、PT 或 Redis 配置不参与选择。

没有把全部消息和媒体服务器包永久导入，因为这正是冷启动浪费来源；也没有物理删除包，以保留上游同步和官方回退。

### 3. ModuleManager 成为三类配置的唯一集合重载所有者

ModuleManager 监听 `Notifications`、`MediaServers`、`Storages`，使用可重入锁串行执行“停止当前实例 → 重新计算包集合 → 加载并初始化 → 发送既有 ModuleReload 事件”。`_MessageBase` 和 `_MediaServerBase` 不再单独监听这两张配置表，避免同一事件造成两次资源重建。模块自身对环境配置（例如 TMDB 域名、代理）的监听保持不变。

若某个旧实例停止失败，记录错误后继续停止其余实例并重建；失败实例不得继续留在 `_running_modules`。若新配置包导入或初始化失败，只隔离对应包，其他保留模块仍可工作。ModuleManager 初始化期间读取 SQLite 配置，不通过 `ServiceConfigHelper`，以避免 `app.modules → app.helper.service → app.core.module` 的循环依赖；解析使用既有 Schema 和只读 `SystemConfigOper`。

选择统一全量重建而不是事件中增量增删，是因为当前事件分发会通过 ModuleManager 查找模块实例；并发移除集合可能让旧模块的停止处理器失去解析目标。模块数量有限，配置变更远低于业务请求频率，串行重建更容易证明没有双实例和线程泄漏。

### 4. 存储使用固定类型映射和第二层门控

FileManager 的存储映射固定为 `local → local`、`u115 → u115`、`alipan → alipan`、`alist → alist`、`rclone → rclone`、`smb → smb`。冷启动始终加载 Local；其他类型仅在 `Storages` 列表出现时传给 `ModuleHelper.package_filter`。自定义或未知 type 可以保留在历史配置中，但不会转换为导入路径或进入支持集合。

配对前端新增存储时会先提交 `Storages`，该 ConfigChanged 事件使 ModuleManager 重建 FileManager，之后再打开授权或测试。为兼容直接 REST 首次授权，FileManager 的授权、二维码、登录确认和配置保存入口可以对固定映射中的单个目标执行按需导入；该路径必须验证管理员/Token 的既有 Endpoint 依赖，只导入精确目标，不扫描其他存储。普通文件操作不能用任意 `FileItem.storage` 触发未配置适配器导入。

存储专用配置写入和重置必须发布同一个 `Storages` 配置变更信号，使活动集合最终与持久化配置一致。运行中移除某适配器后，ModuleManager 停止并重建 FileManager；其代码可能仍在解释器缓存，但不得继续存在可用操作实例或后台活动。

### 5. 现有模块 API 只展示实际发现结果

`/system/modulelist` 保持路径、认证、响应字段和中文/i18n 名称语义，但只枚举本次发现集合；`/system/moduletest/{moduleid}` 对未加载或禁用模块沿用失败结果，不为兼容返回空壳成功。前端配置表单通过固定选项和系统设置 API 创建配置，不依赖 modulelist 发现尚未启用的消息、媒体服务器或存储类型；审计结果写入兼容文档和 REST 说明。

未采用“导入全部类但只隐藏 modulelist”，因为那不减少资源且违反导入前门控。也不新增第二套公开适配器目录 API，本变更的配对前端不需要它；后续若需要动态目录，必须用静态元数据而非导入实现类。

### 6. 能力清单版本和插件接口保持不变

现有 capability profile 已把 PT、下载器和 Redis 等能力标为禁用，本变更只是让 ModuleManager 消费该固定边界，没有新增或重新分类 `Capability`，因此清单版本保持 2。插件管理器、插件事件和 P115StrmHelper 安装方式不变；模块发现不能根据某个插件的需求恢复禁用核心包。

前端在本变更不提交代码。后续配对前端裁剪必须使用同一产品文档中的固定消息、存储和媒体服务器类型，且不得把后端未分类模块暴露为可启用选项。

### 7. 验证以导入阻断、生命周期计数和离线基线为证据

pytest 使用临时包、导入钩子、模拟 SQLite 配置和假的服务实例验证：被拒绝包一旦导入就抛错时启动仍成功；未知配置不能形成导入；已配置类型只初始化一次；切换配置后旧实例 stop 一次、新实例 init 一次；首次 U115 授权只导入 u115；禁用依赖缺失不影响发现。测试还检查 `sys.modules` 中冷启动没有禁用包，并验证 modulelist 集合。

修改 `app/core/`、共享模块基类和 Helper 后运行定向 pytest、全量 pytest、修改模块 Pylint 及 `pylint app/`，与已知 Windows 基线逐项比较。普通测试阻断真实外联。

资源证据在同一 Python/依赖/配置条件下记录模块发现耗时、进程 RSS、导入包数和活动线程数的前后样本；这些数据用于确认方向，不替代完整 Docker 候选的 -30% RAM、-25% 镜像和 -20% 冷启动最终验收。

## Risks / Trade-offs

- [运行时停用后依赖代码仍在 `sys.modules`] → 明确冷启动导入与活动资源是本变更保证；停止实例并重建集合，完全释放代码内存通过重启实现。
- [统一重载短暂中断消息或媒体服务器请求] → 使用可重入锁串行化，配置变更属于低频管理操作；先停止后重建，避免新旧客户端并存。
- [某模块 stop 不完整导致线程泄漏] → 测试代表性消息/媒体实例的 stop 次数与活动集合，并把具体模块缺陷作为阻断问题修复，不能用移出字典掩盖。
- [配置损坏导致必要适配器未加载] → 对单条配置解析失败做脱敏日志并 fail-closed；其他有效配置继续加载，原始 SQLite 数据不改写。
- [首次授权在配置事件尚未消费时到达] → 授权和配置入口提供固定类型的精确按需加载；不依赖异步事件完成顺序。
- [上游新增消息或存储类型默认不可用] → 这是预期安全边界；同步时先分类、补测试和文档，再加入固定映射。
- [ModuleManager 与 `app.modules` 形成循环导入] → 核心选择只读取 SystemConfigOper 和 Schema，不导入 ServiceConfigHelper；增加冷启动导入测试。
- [modulelist 收窄影响诊断页面] → 诊断页展示实际运行范围符合 Lite 语义；配置页面使用系统设置和固定选项，配对前端回归确认首次新增流程。
- [资源收益不及最终目标] → 本变更只完成发现层；保留测量基线，后续任务、依赖和 Docker 裁剪分别追踪剩余成本。

## Migration Plan

1. 先增加失败测试和导入追踪基线，确认当前实现会导入禁用顶层包及全部存储适配器。
2. 实现通用包级预过滤，再接入顶层固定矩阵；此时保留模块初始化语义不变。
3. 接入存储第二层门控和精确首次授权，验证配对前端“先保存配置、再授权/测试”流程。
4. 把三类集合配置重载收口到 ModuleManager，验证 stop/init 次数、错误恢复和并发锁。
5. 使用官方 `/config` 副本测试历史 Downloaders、Redis、非目标媒体服务器及多个存储配置；不修改原数据库。
6. 部署前备份 `/config` 和 SQLite。回退只需恢复对应源码/镜像并使用原配置启动；历史配置和适配器源码未删除，无数据库迁移需要回滚。
7. 实施、提交、推送和任何 Canary 部署分别遵守既有审批检查点；本变更本身不发布镜像或接触生产实例。

## Open Questions

无。顶层包矩阵、Local 兜底、远端存储配置语义、首次授权路径、统一重载所有者和运行时卸载边界均已明确；全应用启动任务、消息动作、依赖和 Docker 裁剪留给后续独立变更。
