## Why

MoviePilot 当前会在 API 路由注册前静态导入全部端点及独立兼容接口，使已经在 Lite 能力配置中禁用的 PT、下载器、订阅、Agent 等代码仍被加载，并可能因其专属依赖缺失而阻止应用启动。现在需要把统一能力配置接入 API 导入边界，形成第一层真实运行时裁剪。

## What Changes

- 将主 API 路由改为有序、声明式的能力映射，并且只在对应能力已启用后导入和注册端点模块。
- 在应用启动路由初始化阶段，按能力配置决定是否导入和注册 Radarr/Sonarr 兼容接口及 CookieCloud 接口。
- 新增 `auxiliary-auth` 禁用能力，用于覆盖 SSO、PassKey、MFA 等辅助认证接口；管理员密码登录、登录 Token、`API_TOKEN` 及 115 OAuth/API 链路继续保留。
- 将能力配置版本从 1 递增到 2，明确标识能力分类契约发生变化。
- 新增 API 路由存在性、禁用模块未导入、缺失禁用依赖仍可启动以及路由顺序保持稳定的自动化测试。
- **BREAKING**：禁用能力对应的 API 路径以及 Radarr/Sonarr、CookieCloud 独立接口不再注册，请求这些路径将返回 404。
- 本变更不删除端点源码，不拆分保留端点内部对禁用业务的历史引用，不裁剪后台服务、任务、消息命令、依赖或前端页面。

## Capabilities

### New Capabilities

- `lite-api-route-gating`: 定义 Lite 在模块导入前筛选主 API 和独立兼容接口的路由注册契约。

### Modified Capabilities

- `lite-capability-profile`: 在禁用能力分类中新增 `auxiliary-auth`，并将配置版本递增到 2。

## Impact

- 后端：修改 `app/api/apiv1.py`、`app/startup/routers_initializer.py` 和 `app/core/capability.py`，新增对应 pytest 测试。
- API：保留能力的路径、标签、顺序和既有认证语义保持不变；禁用能力端点不再出现在 OpenAPI 或运行时路由中。
- 文档：更新 MCP/REST API 文档和 `moviepilot-api` skill 的 Lite 兼容说明，防止自动化继续调用返回 404 的上游接口。
- 认证：仅移除辅助认证 API；管理员密码登录、Token、会话安全和 115 所需 OAuth/API 不受影响。`login.py` 内部历史站点引用留待独立变更处理。
- 前端与插件：本变更不修改前端或插件加载机制；直接导入端点模块的开发测试仍可运行，正常应用启动路径才实施门控。
- 依赖、配置、数据库与 Docker：不新增或删除依赖，不新增环境变量，不修改 `/config`、数据库结构或 Docker 构建。
- 资源占用：减少禁用 API 模块及其传递依赖的导入和初始化开销；完整资源指标仍需后续服务、任务和依赖裁剪后统一测量。
- 安全与兼容：减少不需要的攻击面；依赖已移除 API 的客户端或插件会收到 404，需依据插件兼容矩阵处理。
- 上游同步：保留官方端点文件和目录，仅集中修改两个路由组合点；同步新增路由时必须先分类能力再注册，回退时可恢复这两个组合点及能力配置版本。
