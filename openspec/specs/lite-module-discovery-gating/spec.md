# lite-module-discovery-gating Specification

## Purpose
定义 MoviePilot Lite 在导入前按固定能力矩阵门控顶层模块和存储适配器，并在配置变化时安全重建活动实例的运行契约。
## Requirements
### Requirement: 包过滤必须发生在候选模块导入之前
系统 MUST 为通用模块发现提供包名级过滤，并且 MUST 在调用候选包的导入或重载逻辑之前完成判断。导入后的类过滤 MUST NOT 被当作导入前门控；未提供包过滤器的其他调用方 MUST 保持既有默认加载语义。

#### Scenario: 被拒绝包不会触发导入
- **GIVEN** 一个候选包的导入钩子被设置为一旦调用就抛出错误
- **WHEN** 包过滤器拒绝该候选并执行模块发现
- **THEN** 发现过程成功完成，且该候选的导入钩子从未被调用

#### Scenario: 允许包先通过门控再导入
- **GIVEN** 一个候选包被包过滤器允许
- **WHEN** 模块发现处理该候选
- **THEN** 系统先记录允许决定，再导入该包并执行既有类过滤

#### Scenario: 包过滤异常默认拒绝
- **GIVEN** 包过滤器处理某候选时抛出异常
- **WHEN** 模块发现继续处理目录
- **THEN** 系统不导入该候选，以脱敏日志记录失败，并继续处理其他允许候选

### Requirement: 顶层模块集合必须由固定 Lite 矩阵决定
正常 Lite 模块发现 MUST 无条件允许 `bangumi`、`douban`、`fanart`、`filemanager`、`themoviedb`、`thetvdb`。系统 MUST 仅按启用配置有条件允许规定的消息渠道及 Emby、Jellyfin、Plex，并 MUST 在导入前拒绝 `filter`、`indexer`、`postgresql`、`qbittorrent`、`redis`、`rtorrent`、`subtitle`、`transmission`、`trimemedia`、`ugreen`、`zspace`。任何上游新增且未分类的顶层包 MUST 默认拒绝。

#### Scenario: 无条件保留模块可发现
- **GIVEN** Lite 使用空的消息、媒体服务器和远端存储配置
- **WHEN** ModuleManager 完成首次发现
- **THEN** 六个规定无条件保留包被导入并进入既有类发现流程

#### Scenario: 禁用模块及依赖缺失不影响发现
- **GIVEN** PT、下载器、Redis、PostgreSQL 和非目标媒体服务器包一旦导入就会因依赖缺失而失败
- **WHEN** Lite 执行正常模块发现
- **THEN** 这些包均未被导入、实例化或加入模块集合，其他保留模块仍可初始化

#### Scenario: 历史配置不能恢复禁用包
- **GIVEN** SQLite 中仍有启用的 Downloaders、Redis 或非目标媒体服务器历史配置
- **WHEN** ModuleManager 计算 Lite 包集合
- **THEN** 历史配置被保留但不参与允许决定，禁用包仍未导入

#### Scenario: 未分类上游包默认不加载
- **GIVEN** `app.modules` 目录出现一个固定矩阵没有记录的新包
- **WHEN** Lite 执行模块发现
- **THEN** 新包在导入前被拒绝，直到经过明确分类、文档和测试

### Requirement: 消息与媒体服务器模块必须按启用配置加载
系统 MUST 只在至少存在一条类型匹配且 `enabled=true` 的配置时导入对应消息或媒体服务器包。同一类型存在多条启用配置时 MUST 只导入一个实现包，并由既有 ServiceBase 创建各配置实例。消息允许类型 MUST 固定为 Discord、Feishu、QQBot、Slack、SynologyChat、Telegram、VoceChat、WebPush、WeChat、WeChatClawBot 对应的官方类型；媒体服务器允许类型 MUST 固定为 Emby、Jellyfin、Plex。

#### Scenario: 未配置渠道不导入重依赖
- **GIVEN** Notifications 为空或某消息类型全部禁用
- **WHEN** Lite 冷启动发现消息模块
- **THEN** 对应消息包及其第三方 SDK 不被模块发现路径导入，也不创建客户端或后台线程

#### Scenario: 启用渠道保持官方实例语义
- **GIVEN** 同一允许消息类型有两条名称不同且启用的有效配置
- **WHEN** ModuleManager 加载该类型
- **THEN** 实现包只导入一次，两个服务实例按官方配置、身份和权限逻辑创建

#### Scenario: 只允许三个核心媒体服务器
- **GIVEN** MediaServers 同时包含启用的 Plex 与启用的 ZSpace 历史配置
- **WHEN** ModuleManager 计算条件包
- **THEN** Plex 被允许加载，ZSpace 在导入前被拒绝且历史配置不被删除

#### Scenario: 已配置模块缺少依赖时隔离失败
- **GIVEN** 一个已启用的允许消息渠道缺少其专属第三方依赖
- **WHEN** 系统尝试导入该渠道包
- **THEN** 系统记录该渠道加载失败且不创建其实例，不导入其他未配置渠道，其他保留模块继续工作

### Requirement: 存储适配器必须执行第二层配置门控
FileManager MUST 始终加载 Local 基础适配器，并 MUST 仅为 `Storages` 中已配置的固定官方类型加载远端适配器。固定映射 MUST 只包含 `u115`、`alipan`、`alist`、`rclone`、`smb` 及 Local；配置值 MUST NOT 被拼接为任意 Python 导入路径。未配置远端适配器在冷启动时 MUST NOT 被导入、实例化或创建活动资源。

#### Scenario: 仅配置 115 时不加载其他网盘
- **GIVEN** Storages 只包含 U115 配置
- **WHEN** FileManager 初始化存储实现
- **THEN** 系统加载 Local 和 U115，不导入 Alipan、Alist、Rclone 或 SMB 实现及其专属依赖

#### Scenario: 没有远端配置时只加载 Local
- **GIVEN** Storages 为空或只包含 Local
- **WHEN** FileManager 初始化
- **THEN** Local 文件操作保持可用，所有远端存储实现均未导入

#### Scenario: 未知存储类型不能注入导入路径
- **GIVEN** 历史配置包含不在固定映射中的 type 字符串
- **WHEN** FileManager 计算包过滤结果
- **THEN** 原始配置不被删除，但该值不触发任何动态导入且不进入支持存储集合

#### Scenario: 普通文件请求不能激活未配置适配器
- **GIVEN** U115 未配置且未加载
- **WHEN** 普通文件操作提交一个声称 storage 为 u115 的 FileItem
- **THEN** 系统返回既有的不支持或失败结果，不以该不可信字段触发 U115 导入

### Requirement: 首次存储配置和授权必须支持精确按需加载
经过既有管理员或 Token 认证的存储配置、二维码、OAuth 授权和登录确认入口 MUST 能为固定映射中的单个目标按需加载适配器，以兼容尚无持久配置的首次设置。按需加载 MUST 只处理明确目标，MUST NOT 扫描或导入其他存储，并 MUST NOT 放宽 Endpoint 的既有认证依赖。

#### Scenario: 首次 115 OAuth 只加载 U115
- **GIVEN** U115 尚未出现在持久配置中，调用方具有既有有效凭据
- **WHEN** 调用方请求 `/storage/auth_url/u115`
- **THEN** 系统只延迟加载 U115 实现并沿用官方 OAuth/API 逻辑，其他远端存储仍未导入

#### Scenario: 未授权首次配置被拒绝
- **GIVEN** U115 尚未配置且调用方没有有效管理员会话或 Token
- **WHEN** 调用方请求存储授权或配置入口
- **THEN** 既有认证依赖先拒绝请求，系统不因按需加载机制放宽权限

#### Scenario: 未知类型按需加载失败关闭
- **GIVEN** 调用方请求一个不在固定存储映射中的名称
- **WHEN** 授权或配置入口尝试解析目标
- **THEN** 系统不导入任何候选包，并返回明确失败而非空壳成功

### Requirement: 集合配置变化必须由单一生命周期所有者重载
ModuleManager MUST 作为 Notifications、MediaServers、Storages 集合变化的唯一模块集合重载所有者，MUST 串行停止旧运行实例、重新计算允许包、初始化新集合并发送既有 ModuleReload 事件。消息和媒体服务器基类 MUST NOT 对同一集合配置再执行第二次独立重载。

#### Scenario: 启用新渠道只初始化一次
- **GIVEN** 系统运行时新增一条允许消息类型的启用配置
- **WHEN** ConfigChanged 事件处理完成
- **THEN** ModuleManager 重新发现并初始化该模块一次，不存在管理器与模块基类造成的重复客户端或线程

#### Scenario: 停用渠道释放活动实例
- **GIVEN** 一个消息或媒体服务器模块当前有活动实例
- **WHEN** 对应配置被禁用或删除并完成集合重载
- **THEN** 旧实例的 stop 被调用，实例从运行集合移除且不再处理后续业务事件

#### Scenario: 存储配置变化重建 FileManager
- **GIVEN** 运行中的 Storages 集合新增 U115 或移除另一远端类型
- **WHEN** 持久化写入发布 Storages 配置变更
- **THEN** FileManager 按最新集合重建，新增目标可用且已移除目标不再有活动操作实例

#### Scenario: 停止异常不遗留双实例
- **GIVEN** 一个旧模块 stop 时抛出异常
- **WHEN** ModuleManager 继续执行集合重载
- **THEN** 系统记录错误、继续处理其他模块，旧对象不保留在新的运行集合且不会为同一新配置创建多份实例

### Requirement: 热停用与冷启动导入保证必须明确区分
系统 MUST 保证冷启动未选择包不进入模块发现产生的 `sys.modules`、模块集合或活动资源。对于运行期间已经导入后再停用的包，系统 MUST 停止并移除活动实例，但 MUST NOT 通过不安全删除 `sys.modules` 或强制卸载共享代码来伪造内存释放；完全清除代码缓存允许通过正常重启完成。

#### Scenario: 冷启动模块缓存不含禁用包
- **GIVEN** 一个干净解释器和空的条件配置
- **WHEN** Lite 完成首次模块发现
- **THEN** 禁用、未配置和未知候选包不在该发现路径产生的模块缓存中

#### Scenario: 热停用后业务实例不可用
- **GIVEN** 某允许包已经加载并运行
- **WHEN** 配置变化停用该包但进程不重启
- **THEN** 该包不再出现在运行模块或服务实例集合中，即使 Python 仍缓存其代码对象

### Requirement: 模块诊断 API 必须反映实际 Lite 发现集合
`/system/modulelist` MUST 保持既有路径、Token 校验、响应字段和名称国际化语义，但 MUST 只返回实际发现的 Lite 模块。`/system/moduletest/{moduleid}` MUST NOT 为禁用、未配置或未知模块返回虚假成功。模块发现门控 MUST NOT 改变保留模块测试方法的官方行为。

#### Scenario: 模块列表不展示禁用模块
- **GIVEN** Lite 使用包含历史下载器和 ZSpace 的配置
- **WHEN** 已认证调用方查询 `/system/modulelist`
- **THEN** 响应不包含下载器、PT、Redis、PostgreSQL 或 ZSpace 模块，并保留实际模块的既有字段和名称

#### Scenario: 未加载模块测试不伪造成功
- **GIVEN** 调用方提供一个已禁用或未配置的模块 ID
- **WHEN** 调用 `/system/moduletest/{moduleid}`
- **THEN** 系统沿用未运行模块的失败语义，不实例化该模块进行测试

#### Scenario: API 认证保持不变
- **GIVEN** 调用方没有有效 Token
- **WHEN** 查询模块列表或测试任一模块
- **THEN** 既有认证依赖拒绝请求，门控不提供绕过路径

### Requirement: 配置与回退必须保持无破坏性
本变更 MUST 只读取既有 Notifications、MediaServers、Storages 并保留未知或禁用历史配置，MUST NOT 新增数据库迁移、删除配置记录或修改真实凭据。回退同版本官方代码后，原数据 MUST 仍可由官方逻辑解释。

#### Scenario: 历史配置原样保留
- **GIVEN** `/config` 副本包含下载器、非目标媒体服务器和多个远端存储历史配置
- **WHEN** Lite 启动、重载并停止
- **THEN** 禁用内容不进入运行时，但持久化记录和值未被门控过程改写或删除

#### Scenario: 普通测试不使用真实秘密或外联
- **GIVEN** CI 运行模块发现、首次授权和配置重载测试
- **WHEN** 测试覆盖 U115、消息渠道和媒体服务器
- **THEN** 所有客户端、响应和配置均为 mock 或占位值，不访问真实外部服务且不记录 Token、Cookie 或密码
