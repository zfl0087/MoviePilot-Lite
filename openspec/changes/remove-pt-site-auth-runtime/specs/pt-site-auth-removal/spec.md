## ADDED Requirements

### Requirement: 本地管理员认证必须独立于 PT 站点等级
Lite 的管理员密码登录、登录 Token、资源 Token 和超级管理员 API Token MUST 使用固定本地认证等级 1，MUST NOT 读取 `AUTH_SITE`、`UserSiteAuthParams`、`SitesHelper.auth_level` 或调用 PT 在线认证。既有用户名、密码、会话、Token Schema 和管理员权限校验 MUST 保持有效。

#### Scenario: 管理员密码登录成功
- **WHEN** 管理员提交正确的本地用户名和密码，且 PT 认证服务不可访问
- **THEN** 登录按既有响应模型成功并返回等级 1 的 Token

#### Scenario: 错误密码仍被拒绝
- **WHEN** 调用方提交错误的管理员密码
- **THEN** 系统按既有认证语义拒绝请求，不因移除 PT 认证而绕过密码校验

#### Scenario: API Token 权限保持不变
- **WHEN** 调用方使用正确或错误的 `API_TOKEN` 访问受保护接口
- **THEN** 正确 Token 获得原有管理员权限且等级为 1，错误 Token 仍被拒绝

#### Scenario: PT 认证等级不可用
- **WHEN** 测试替身在读取站点认证等级或调用在线认证时抛出错误
- **THEN** 本地管理员登录和 Token 验证仍成功完成，且测试替身未被调用

### Requirement: AUTH_SITE 必须从 Lite 配置契约移除
Lite 配置模型 MUST NOT 定义、枚举或使用 `AUTH_SITE`。历史环境变量、配置文件输入或 `/config` 中的同名值 MUST 被忽略且 MUST NOT 恢复 PT 认证；系统 MUST NOT 主动删除历史数据库配置和未知字段。

#### Scenario: 历史环境变量被忽略
- **WHEN** 启动环境仍包含 `AUTH_SITE` 值
- **THEN** Lite 正常加载配置，但有效配置字段中不存在 `AUTH_SITE`，且不发起站点认证

#### Scenario: 历史数据库数据被保留
- **WHEN** SQLite 中存在 `UserSiteAuthParams` 或其他旧站点认证记录
- **THEN** Lite 不读取其执行认证，也不删除或改写该记录

#### Scenario: 回退官方版本
- **WHEN** 用户使用升级前备份回退到匹配的官方版本
- **THEN** 原有历史配置仍可由官方版本按其自身语义解释

### Requirement: 插件认证等级必须使用固定 Lite 策略
插件管理器 MUST 在不导入或查询 PT 站点认证的情况下判断插件认证等级。未声明等级、等级 0 和等级 1 MUST 继续进入后续能力与版本兼容检查；等级 2、3 和 99 MUST 被拒绝，且私钥、环境变量或在线认证 MUST NOT 提升其等级。

#### Scenario: 等级 1 插件进入兼容检查
- **WHEN** 插件声明 `auth_level=1`
- **THEN** 认证门槛通过，但系统不据此声称插件已经完全兼容 Lite

#### Scenario: 高等级插件被拒绝
- **WHEN** 插件声明认证等级 2、3 或 99
- **THEN** 插件认证门槛失败，不实例化为运行插件，也不执行 PT 在线校验

#### Scenario: 特殊私钥不能恢复等级 99
- **WHEN** 环境中存在旧的插件私钥且插件声明等级 99
- **THEN** Lite 仍拒绝该插件，且不读取私钥或执行 RSA 配对

#### Scenario: 认证服务故障不影响等级 1 插件
- **WHEN** PT 认证服务和认证资源均不可用且插件声明等级 1
- **THEN** 插件仍可进入后续兼容检查，不因外部认证故障失败

### Requirement: 正常模块启动不得执行 PT 认证
正常 Lite 模块启动 MUST NOT 实例化站点认证检查器、调用 `check_user()`、读取认证等级、发送认证失败通知或检查/下载 PT 认证与索引资源包。启动 MUST 保持事件、消息、插件、元数据、网盘、整理和媒体服务器所需的其他所有者不变。

#### Scenario: 离线启动
- **WHEN** PT 认证服务、认证资源仓库和认证参数均不可用
- **THEN** Lite 模块启动继续执行保留所有者，且不产生 PT 认证网络请求或认证失败通知

#### Scenario: 旧认证参数不能触发校验
- **WHEN** `/config` 中仍有 `UserSiteAuthParams`
- **THEN** 模块启动不读取该参数、不调用 `check_user()`，也不根据结果重新初始化插件

#### Scenario: 保留所有者失败仍按原语义处理
- **WHEN** 与 PT 认证无关的必要模块、事件或消息所有者初始化失败
- **THEN** 系统沿用该所有者的原有失败语义，不把必要故障静默当作认证裁剪

### Requirement: 系统调度器不得恢复站点认证及相关任务
系统调度器 MUST NOT 导入、实例化、注册或执行 `cookiecloud`、`user_auth` 和 `sitedata_refresh` 系统任务，也 MUST NOT 把 `siteuserdata` 纳入 Lite 自动数据清理计划。环境变量、用户设置和历史配置 MUST NOT 恢复这些任务。

#### Scenario: 固定 Lite Job 清单
- **WHEN** 系统调度器在非开发模式初始化
- **THEN** Job 与内部服务清单均不包含 `cookiecloud`、`user_auth` 或 `sitedata_refresh`

#### Scenario: 旧运行配置不能恢复任务
- **WHEN** `COOKIECLOUD_INTERVAL`、`SITEDATA_REFRESH_INTERVAL` 或历史认证配置仍为非空值
- **THEN** 调度器仍不注册对应任务

#### Scenario: 站点历史数据不被自动清理
- **WHEN** Lite 执行通用数据清理任务
- **THEN** 清理计划不包含 `siteuserdata`，历史站点数据保持不变

#### Scenario: 手工运行禁用任务被拒绝
- **WHEN** 内部调用方尝试按 `cookiecloud`、`user_auth` 或 `sitedata_refresh` 标识运行任务
- **THEN** 调度器找不到可执行服务，不返回虚假成功结果

### Requirement: 115 网盘授权必须与 PT 认证隔离
移除 PT 站点认证 MUST NOT 删除、重命名或改写 115 网盘所需的 `U115_APP_ID`、`U115_AUTH_SERVER`、存储适配器 OAuth/API 或 `/storage/auth_url/{name}` 路由。115 的真实凭据 MUST 继续只存在部署实例中，普通测试 MUST 使用 mock。

#### Scenario: 115 授权路由保持注册
- **WHEN** Lite 构建主 API 路由
- **THEN** `/storage/auth_url/{name}` 仍存在并沿用既有管理员认证依赖

#### Scenario: PT 认证配置缺失不影响 115
- **WHEN** `AUTH_SITE` 和 PT 认证资源均不存在
- **THEN** 115 存储适配器仍可依据自身配置生成授权请求，不查询 PT 站点认证等级

#### Scenario: 普通测试不使用真实凭据
- **WHEN** CI 验证 115 授权与 PT 认证隔离
- **THEN** 测试只使用模拟响应和占位配置，不访问真实 115 或记录真实 Token

### Requirement: PT 认证源码保留不得被误报为完整 PT 裁剪
为降低上游同步成本，本变更 MAY 保留已被 API 门控的 PT Endpoint、`SitesHelper` 和历史模型源码，但正常认证、插件、模块启动和系统调度路径 MUST NOT 调用其认证行为。系统 MUST NOT 因本变更声称 PT 站点模块、消息命令、依赖或前端已经全部裁剪。

#### Scenario: 直接源码测试仍可导入
- **WHEN** 开发测试显式直接导入已禁用的 PT 端点或 helper
- **THEN** 本变更不要求物理删除源码，但该导入不代表正常 Lite 运行路径会调用认证

#### Scenario: 后续边界仍被标记为未完成
- **WHEN** 审查模块发现、消息命令、前端或 Docker 依赖状态
- **THEN** 这些边界继续标记为待后续变更，不以本次认证移除替代其验收
