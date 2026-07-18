## Context

API 路由门控已经让 `/site`、`/auth` 和 `/mfa` 不进入 Lite，但 PT 站点认证仍从多个保留入口渗入运行时：`login.py` 和 `security.py` 读取 `SitesHelper.auth_level` 写入 Token，`PluginManager` 用同一等级及 RSA 私钥决定插件可见性，`modules_initializer.py` 在启动时导入站点资源、执行 `check_user()` 并发送失败通知，`Scheduler` 还注册 CookieCloud、用户认证和站点数据刷新任务。

这些调用不仅维持了被移除的在线认证语义，还使历史 `AUTH_SITE`、站点资源包和远程认证可用性影响管理员登录与插件启动。115 网盘的授权路径位于存储适配器及 `/storage/auth_url/{name}`，与 PT 站点认证无关，必须保持隔离。

审计同时发现 `SitesHelper` 仍被 PT 索引、系统版本展示、消息交互和部分待裁剪模块引用。本变更只移除 PT **用户认证**及与它绑定的启动/调度链路，不对所有 PT 站点源码做物理删除；模块发现、消息命令和剩余 PT 索引引用继续使用后续独立变更。

## Goals / Non-Goals

**Goals:**

- 让管理员登录、超级管理员 API Token 和资源 Token 完全不依赖 PT 站点认证等级或在线服务。
- 让 Lite 固定只接受插件认证等级 0/1，拒绝依赖站点认证或特殊密钥认证的等级 2/3/99。
- 正常模块启动不执行站点认证、认证失败通知或 PT 认证/索引资源包更新。
- 系统调度器不导入、实例化或注册 CookieCloud、PT 用户认证及站点数据刷新任务。
- 删除 `AUTH_SITE` 的有效配置入口，同时保留历史 `/config` 和数据库数据供官方版本回退。
- 保持 115 OAuth/API、管理员密码校验、会话和 `API_TOKEN` 拒绝语义不变。

**Non-Goals:**

- 不删除 `app.helper.sites`、站点 Endpoint、Chain、Indexer 或历史数据库模型。
- 不在本变更处理订阅、下载器、Agent、工作流、模块包预过滤或消息命令裁剪。
- 不实现完整插件 capability 兼容矩阵或缺少 P115StrmHelper 的用户提示；只固定认证等级门槛。
- 不移除 Python 依赖、资源文件、前端页面、Docker 层或配置数据库字段。
- 不改写 115、Alipan、Alist 等存储适配器各自的 OAuth 或登录逻辑。

## Decisions

### 1. 使用固定本地认证等级 1

在 `app/core/security.py` 定义共享常量 `LITE_AUTH_LEVEL = 1`。管理员登录响应、JWT、资源 Token 和超级管理员 API Token 统一使用该值，保留现有 Token Schema 和 `level` 字段，避免前端或插件因字段消失而发生非必要兼容问题。

选择等级 1 是因为官方语义中它代表不依赖 PT 站点认证的基础用户，且与 `docs/COMPATIBILITY.md` 已确认的插件等级规则一致。没有通过构造假的 `SitesHelper.auth_level` 来模拟成功，因为那仍保留在线认证依赖和误导性高等级语义。

能力清单版本保持 2：本变更没有新增、删除或重新分类 `Capability`，只是落实已禁用的 `pt-site-auth`。若将固定认证等级加入机器能力清单才需要递增版本，本变更不这样做。

### 2. `AUTH_SITE` 从模型移除但历史值不清理

从 `ConfigModel` 删除 `AUTH_SITE` 字段。模型已经使用 `extra="ignore"`，因此旧环境变量或配置输入不会恢复行为，也不会阻止启动。`SystemConfigKey.UserSiteAuthParams` 暂时保留，数据库记录不删除、不迁移，满足 `/config` 回退要求。

没有把字段保留并强制为空，因为这仍会让 API、文档和配置枚举把它宣传为有效 Lite 设置。

### 3. 插件等级使用纯本地确定性判断

`PluginManager.__set_and_check_auth_level()` 继续从插件或市场元数据读取 `auth_level`，但只允许缺省、0 或 1。等级 2、3、99 返回不兼容，且不导入 `SitesHelper`、不读取 `PLUGIN_*_PRIVATE_KEY`、不执行 RSA 配对。与认证有关的私钥辅助代码和未使用导入一并删除。

这只完成认证门槛。插件是否依赖下载器、PT、工作流、Redis、FFmpeg 等能力仍由后续插件兼容变更判断，不能把“等级 1”宣传为已经完全兼容。

### 4. 模块启动删除认证和资源副作用

`app/startup/modules_initializer.py` 删除 `SitesHelper`、`ResourceHelper`、认证配置和认证通知相关顶层导入及调用。正常 `init_modules()` 仍启动 DoH、经过后续预过滤的 `ModuleManager`、事件、消息、插件统计初始化和平台前端；本变更不改变这些其他所有者。

关闭路径不需要为站点认证释放资源。已有 `/config` 中的认证参数不读取、不覆盖。

### 5. 调度器移除三类站点任务并保留数据

`app/scheduler.py` 删除以下系统 Job 定义、触发器和对应顶层依赖：

- `cookiecloud`
- `user_auth`
- `sitedata_refresh`

同时从数据清理计划移除 `siteuserdata` 表，避免 Lite 在功能禁用后主动删除官方回退可能需要的历史站点数据。运行配置中的 `COOKIECLOUD_INTERVAL`、`SITEDATA_REFRESH_INTERVAL`、`UserSiteAuthParams` 或旧认证状态不能重新注册任务。

媒体服务器同步、缓存清理、插件市场、整理及其他尚未裁剪的任务保持原状，后续按能力逐项处理。没有给禁用任务保留空函数或虚假成功状态。

### 6. API 路由门控与 115 授权保持独立

前一规范继续保证 PT 认证路由返回 404。本变更只改保留登录和 Token 内部实现，不改变 `/storage/auth_url/{name}` 路由及 U115 配置。测试通过路由清单和源码依赖同时证明二者没有被混淆。

### 7. 测试以调用阻断和确定性结果为主要证据

pytest 将覆盖：

- `AUTH_SITE` 输入被忽略且字段不再枚举。
- 管理员登录、超级管理员 Token 和资源 Token 的等级恒为 1，并且错误密码或错误 API Token仍被拒绝。
- 用会抛错的站点认证替身运行保留认证、插件和模块启动路径，确认不读取 `auth_level` 或调用 `check_user()`。
- 插件等级 0/1 允许、2/3/99 拒绝。
- Scheduler Job 清单和数据清理计划不含站点相关项，旧运行配置不能恢复。
- 115 存储授权路由继续注册。

所有测试使用临时配置和 mock，不访问真实 PT、GitHub、115 或其他网络。

## Risks / Trade-offs

- [部分前端仍依据 Token `level` 展示站点功能] → 固定返回 1，并由后续配对前端门控彻底移除站点页面；不得返回伪造的高等级。
- [等级 2/3/99 插件过去可用，现在被拒绝] → 这是预期不兼容；保留插件配置和数据，回退官方后可恢复，后续插件兼容页显示明确原因。
- [仍有非认证用途的 `SitesHelper` 引用] → 在规范和报告中明确本变更只完成 `pt-site-auth`；PT 站点模块、系统版本字段、消息交互和索引依赖由后续变更继续裁剪。
- [删除 `AUTH_SITE` 影响旧部署环境] → Pydantic 忽略未知输入，启动不中断；文档标明该字段在 Lite 无效，回退官方无需数据迁移。
- [Scheduler 大文件与上游冲突概率较高] → 只删除三个 Job、一个清理计划及其专属导入，保留其余结构和顺序，并通过精确 Job 集测试约束。
- [跳过站点资源更新后残留文件仍占镜像] → 本变更只停止运行时检查；资源和依赖在 Docker 裁剪变更中删除并测量镜像体积。

## Migration Plan

1. 先添加失败测试，证明旧实现仍读取站点等级、执行认证或注册站点任务。
2. 实施固定等级、本地插件门槛、启动及调度清理，并通过定向与全量回归。
3. 首次候选使用官方 `/config` 副本启动，确认旧 `AUTH_SITE` 和 `UserSiteAuthParams` 不触发外联或报错。
4. 不需要数据库迁移；部署前仍按发布流程备份 `/config` 和 SQLite。
5. 回退时恢复对应源码并使用同一 `/config` 启动官方版本，历史认证参数和数据仍在。

## Open Questions

无。剩余 PT 站点源码、模块发现、消息命令和前端设置已经明确进入后续独立变更，不作为本变更完成条件。
