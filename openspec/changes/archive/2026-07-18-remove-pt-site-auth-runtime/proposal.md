## Why

Lite 已经不注册 PT 站点和认证 API，但保留的管理员登录、API Token、插件加载、模块启动和定时器仍会导入 `SitesHelper`、读取站点认证等级并执行在线认证或资源检查。这会让被移除的 PT 认证继续成为正常启动依赖，也与用户明确要求的“只保留本地管理员认证和 115 OAuth”冲突。

## What Changes

- 从 Lite 配置模型中移除 `AUTH_SITE`；历史环境变量或 `/config` 中的同名值被忽略，但不主动删除原始配置和数据库数据。
- 管理员密码登录、超级管理员 API Token 和资源 Token 使用固定本地认证等级 1，不再导入或查询 `SitesHelper.auth_level`。
- 插件认证等级沿用官方数值含义，但 Lite 固定只允许无等级、等级 0 或等级 1 的插件进入后续兼容检查；等级 2、3、99 不再通过站点在线认证或 RSA 私钥校验恢复运行。
- 从正常模块启动中移除站点认证检查、认证失败通知以及 PT 认证/索引资源包检查，不再为认证目的初始化 `SitesHelper` 或访问认证资源服务。
- 从系统定时器的导入和注册阶段移除 CookieCloud、PT 用户认证和站点数据刷新任务；对应运行配置不能恢复这些任务。
- 新增离线测试，证明保留的登录、Token、插件和启动路径不读取站点认证等级、不调用 `check_user()`，并在认证服务不可访问时仍可工作。
- **BREAKING**：`AUTH_SITE` 不再是有效 Lite 配置；依赖 PT 站点认证等级 2、3 或 99 的插件不能加载；旧的 PT 认证状态不再影响 Token 中的 `level` 字段。
- 本变更不删除 115 的 `U115_APP_ID`、`U115_AUTH_SERVER`、`/storage/auth_url/{name}` 或任何官方网盘 OAuth/API 代码。
- 本变更不顺带裁剪下载器、订阅、Agent、工作流、模块发现、消息命令、Python 依赖或前端页面；`app.helper.sites` 源码及仍待裁剪的 PT 站点/索引调用也暂时保留，按后续独立 OpenSpec 处理。

## Capabilities

### New Capabilities

- `pt-site-auth-removal`: 定义 Lite 正常运行路径彻底脱离 `AUTH_SITE`、PT 站点认证等级、在线校验和认证资源包的契约。

### Modified Capabilities

无。

## Impact

- 后端认证：预计修改 `app/core/config.py`、`app/api/endpoints/login.py`、`app/core/security.py` 和相关测试；请求/响应模型及管理员身份校验保持不变，Token 的 `level` 固定为 1。
- 插件：预计修改 `app/core/plugin.py` 的认证等级判断；等级 1 仍可继续进入能力与版本兼容检查，P115StrmHelper 仍由用户手动安装。
- 启动与调度：预计修改 `app/startup/modules_initializer.py` 和 `app/scheduler.py`，移除认证、站点资源、CookieCloud 及站点数据任务的正常导入、实例化和调度。
- API：PT 站点、辅助认证和 MFA 路由已由前一变更排除；本变更保持 `/login`、`API_TOKEN` 与网盘存储 API 可用。
- 前端：本变更不修改前端仓库；配对前端后续必须移除 `AUTH_SITE` 和站点认证设置展示，不能依据 `level > 1` 恢复 PT 页面。
- 依赖与 Docker：本变更不修改依赖清单或镜像；它先解除保留认证与插件策略对站点认证等级和在线资源的调用要求，为后续 PT 站点模块及依赖裁剪建立门控证据。
- 配置与数据库：不产生数据库迁移，不删除 `UserSiteAuthParams` 等历史数据；回退官方版本后仍可由官方代码解释。
- 资源占用：取消启动期站点资源联网检查、认证校验以及周期性认证/站点任务；最终内存和镜像指标仍需后续模块、任务和依赖裁剪完成后统一测量。
- 安全：不伪造高等级认证成功，不记录真实 Cookie、Token 或 115 凭据；普通测试不访问外部认证、GitHub、115 或其他网络服务。
- 上游同步：保留站点端点和 helper 源码以降低冲突，Lite 改动集中在保留入口的组合和策略点；上游新增认证调用默认不得进入 Lite。
