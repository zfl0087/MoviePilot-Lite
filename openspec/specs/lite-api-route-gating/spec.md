# lite-api-route-gating Specification

## Purpose
定义 MoviePilot Lite 在正常 FastAPI 初始化路径中按固定能力配置执行端点导入与路由注册门控的契约。
## Requirements
### Requirement: 主 API 必须在端点导入前执行能力门控
系统 MUST 使用固定 Lite 能力配置逐项决定主 API 端点是否加载，并且 MUST 在导入端点模块之前完成能力检查。正常应用初始化期间，禁用能力对应的端点模块 MUST NOT 被导入、注册或实例化；开发测试显式直接导入端点模块不属于正常应用初始化路径。

#### Scenario: 禁用端点不会被正常启动导入
- **WHEN** 应用在固定 Lite 配置下初始化主 API，且禁用端点模块一旦导入就会抛出错误
- **THEN** 主 API 初始化成功，禁用端点模块不在正常启动产生的模块缓存中

#### Scenario: 启用端点在检查后导入
- **WHEN** 应用初始化一个对应能力已启用的主 API 端点
- **THEN** 系统先确认能力已启用，再导入并注册该端点路由

#### Scenario: 直接端点测试不受禁止
- **WHEN** 开发测试显式直接导入某个禁用端点模块而未执行正常应用路由初始化
- **THEN** 能力门控不要求阻止该显式导入

### Requirement: 主 API 路由矩阵必须与 Lite 范围一致
系统 MUST 注册 `/login`、`/user`、`/webhook`、`/message`、`/media`、`/douban`、`/tmdb`、`/history`、`/system`、`/notification`、`/plugin`、`/dashboard`、`/storage`、`/transfer`、`/mediaserver` 和 `/bangumi` 主 API 前缀下的既有路由。系统 MUST NOT 注册 `/auth`、`/mfa`、`/site`、`/message/agent`、`/subscribe`、`/search`、`/llm`、`/download`、`/discover`、`/recommend`、`/workflow`、`/torrent`、`/mcp`、`/openai/v1` 和 `/anthropic/v1` 主 API 前缀下的路由。

#### Scenario: 保留路由可发现
- **WHEN** 调用方枚举固定 Lite 配置下的主 API 路由
- **THEN** 每个规定保留的主 API 前缀至少存在一条既有路由

#### Scenario: 禁用路由不可发现
- **WHEN** 调用方枚举固定 Lite 配置下的主 API 路由或访问禁用路径
- **THEN** 禁用前缀下不存在对应端点路由，HTTP 访问按 FastAPI 未匹配路径语义返回 404

### Requirement: 独立兼容接口必须在导入前禁用
正常应用路由初始化 MUST 在导入独立兼容接口之前检查能力配置。`arr-compat` 禁用时，系统 MUST NOT 导入或注册 Radarr/Sonarr `/api/v3` 接口；`cookiecloud` 禁用时，系统 MUST NOT 导入或注册 `/cookiecloud` 接口。

#### Scenario: 独立接口模块缺失仍可初始化
- **WHEN** Radarr/Sonarr 与 CookieCloud 路由模块不可导入且对应能力均已禁用
- **THEN** 应用路由初始化成功，且不存在 `/api/v3` 或 `/cookiecloud` 路由

#### Scenario: 独立接口请求返回未匹配
- **WHEN** 客户端在 Lite 应用中请求 Radarr/Sonarr 或 CookieCloud 兼容路径
- **THEN** 请求按 FastAPI 未匹配路径语义返回 404，而不是返回空壳成功响应

### Requirement: 禁用能力专属依赖缺失不得阻止 API 启动
系统 MUST 能在 PT、辅助认证、订阅、下载器、Agent、LLM、MCP、工作流、内容发现、Radarr/Sonarr 或 CookieCloud 的端点模块及其专属依赖不可用时完成 API 路由初始化，只要这些能力在固定 Lite 配置中禁用。

#### Scenario: 禁用模块导入被阻断
- **WHEN** 测试环境阻断全部禁用端点模块及独立接口模块的导入
- **THEN** API 路由初始化仍然成功，并完整注册规定保留的路由

#### Scenario: 保留模块导入失败不被掩盖
- **WHEN** 一个规定保留的端点模块缺失或导入失败
- **THEN** API 路由初始化明确失败，不将必要能力静默降级为未注册

### Requirement: 保留路由必须维持官方兼容语义
对于仍启用的端点，系统 MUST 保持变更前的相对注册顺序、路径、标签、请求与响应模型以及认证依赖，不得因 Lite 门控绕过管理员身份或 `API_TOKEN` 校验。

#### Scenario: 保留路由顺序稳定
- **WHEN** 系统按固定 Lite 配置构建主 API 路由
- **THEN** 保留端点的相对注册顺序与门控前的官方顺序一致

#### Scenario: 未授权访问仍被拒绝
- **WHEN** 未携带有效管理员会话或 API 凭据的调用方访问一个原本受保护的保留端点
- **THEN** 系统沿用该端点原有认证依赖并拒绝访问

#### Scenario: 管理员登录保持可用
- **WHEN** 调用方使用既有管理员密码登录入口
- **THEN** `/login` 下的登录路由仍按官方既有请求、响应和会话语义处理

### Requirement: API 门控范围必须可审计且固定
主 API 端点到能力的映射 MUST 由代码中的固定声明定义，MUST NOT 从环境变量、用户设置、数据库或 `/config` 生成。上游新增主 API 端点在获得明确能力分类之前 MUST NOT 自动进入 Lite 路由。

#### Scenario: 运行配置不能恢复禁用路由
- **WHEN** 环境变量、用户设置或历史 `/config` 包含试图启用禁用 API 的值
- **THEN** 正常应用初始化仍不导入或注册相应端点

#### Scenario: 未分类的新端点默认不注册
- **WHEN** 上游增加端点模块但固定 Lite 路由声明尚未为其指定能力
- **THEN** 该端点不会自动出现在 Lite 主 API 中
