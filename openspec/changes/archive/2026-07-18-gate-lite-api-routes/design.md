## Context

当前 `app/api/apiv1.py` 在模块顶层静态导入全部端点，再无条件注册到主 `APIRouter`；`app/startup/routers_initializer.py` 也会无条件导入并注册 Radarr/Sonarr 与 CookieCloud 独立路由。即使 Lite 能力配置已将相关功能标为禁用，端点模块及其传递依赖仍会在应用启动时加载，既浪费资源，也会让后续删除专属依赖变得不安全。

本变更位于 Entrypoint 层的路由组合边界，不改变 Chain、Module、Helper 或数据库层的依赖方向。受影响对象包括正常 FastAPI 启动、OpenAPI 路由清单、依赖禁用接口的客户端和插件，以及后续上游同步时新增的 API 路由。

## Goals / Non-Goals

**Goals:**

- 在导入端点模块之前查询固定 Lite 能力配置，禁用能力对应模块既不导入也不注册。
- 保持启用路由的官方相对顺序、路径、标签和认证依赖不变。
- 在正常启动路径中不导入 Radarr/Sonarr 与 CookieCloud 独立接口。
- 为辅助认证补充明确能力分类，并通过配置版本 2 暴露契约变化。
- 为后续删除禁用能力专属依赖建立可测试的 API 启动边界。

**Non-Goals:**

- 不删除或改写任何端点文件、Schema、Chain、Module 或历史数据库数据。
- 不处理保留端点内部仍引用站点、下载器等禁用业务的历史耦合；例如 `login.py` 的站点辅助逻辑留待独立变更。
- 不裁剪后台服务、定时任务、消息命令、插件兼容、Python 依赖、Docker 镜像或前端路由。
- 不增加完整版/Lite 运行时切换开关，也不允许环境变量恢复禁用 API。
- 不禁止开发测试或工具显式直接导入某个端点模块；门控契约只约束正常应用路由初始化路径。

## Decisions

### 1. 主 API 使用有序声明表并延迟导入

`app/api/apiv1.py` 将维护一个与官方现有注册顺序一致的私有路由声明表。每项声明包含端点模块名、路径前缀、标签和所需 `Capability`。构建主路由时先调用 `is_capability_enabled()`，只有结果为真才通过标准库 `importlib.import_module()` 导入模块并包含其 `router`。

选择集中声明表，是为了让上游新增路由的能力归类在代码审查中清晰可见，同时保持改动集中在官方路由组合点。没有选择在每个端点文件内部条件返回空路由，因为那仍会执行模块导入；也没有物理删除端点文件，因为会显著增加上游同步冲突。

主路由映射如下：

| 能力 | 主 API 前缀 |
|---|---|
| `admin-auth` | `/login`、`/user` |
| `system` | `/webhook`、`/system`、`/dashboard` |
| `messaging` | `/message` |
| `metadata` | `/media`、`/douban`、`/tmdb`、`/bangumi` |
| `media-organization` | `/history`、`/transfer` |
| `notifications` | `/notification` |
| `plugins` | `/plugin` |
| `cloud-storage` | `/storage` |
| `media-server` | `/mediaserver` |
| `auxiliary-auth` | `/auth`、`/mfa` |
| `pt-sites` | `/site` |
| `agent` | `/message/agent` |
| `subscriptions` | `/subscribe` |
| `torrent-search` | `/search` |
| `llm` | `/llm`、`/openai/v1`、`/anthropic/v1` |
| `downloaders` | `/download`、`/torrent` |
| `content-discovery` | `/discover`、`/recommend` |
| `workflow` | `/workflow` |
| `mcp` | `/mcp` |

### 2. 独立兼容接口在启动初始化器中条件导入

`app/startup/routers_initializer.py` 始终导入并注册已经完成内部门控的主 API 路由，但仅在 `arr-compat` 或 `cookiecloud` 启用时才分别导入对应独立路由。条件判断必须位于 import 语句之前。

没有把独立接口搬入 `apiv1.py`，因为它们使用不同的顶级前缀和兼容协议，保留官方结构能降低同步成本。

### 3. 辅助认证与必要认证分离

新增禁用能力 `auxiliary-auth`，覆盖 `/auth` 的第三方认证提供者、PassKey 票据交换以及 `/mfa`。它与既有 `admin-auth`、`pt-site-auth`、`sso` 分开，避免误删管理员密码登录或把 115 OAuth/API 归入辅助认证。能力分类发生变化，因此 `LITE_PROFILE_VERSION` 从 1 递增到 2。

没有复用 `sso`，因为现有 `/auth` 同时包含 PassKey 和插件认证提供者，语义大于单一 SSO；也没有复用 `pt-site-auth`，因为该能力只描述 PT 站点用户认证。

### 4. 测试同时验证路由结果与导入边界

pytest 用例将验证启用/禁用路径矩阵和相对顺序，并通过临时 import blocker 与 `sys.modules` 快照证明正常 API 初始化不会触碰禁用端点及独立接口。所有 `sys.meta_path`、`sys.modules` 等进程状态必须在用例结束时恢复。

路由存在性测试防止“模块未导入但错误路由仍注册”，导入阻断测试防止“路由被隐藏但模块仍加载”。两类证据缺一不可。

### 5. 能力版本仍是前后端和插件兼容契约

本变更只更新后端配置版本；配对 Lite 前端在后续前端门控变更中必须消费版本 2。插件兼容检查尚未接入时不宣称插件已完成裁剪，依赖禁用 API 的插件继续标记为不兼容。不存在第二份可由环境变量修改的路由白名单。

## Risks / Trade-offs

- [上游新增路由未加入声明表会缺失] → 上游同步清单必须把 `app/api/apiv1.py` 和启动路由作为人工审查点，并用路径矩阵测试发现变化。
- [动态导入降低静态分析可见性] → 使用固定常量声明表、稳定模块名和定向 import blocker 测试，不接受运行配置拼接模块名。
- [保留端点仍可能在内部导入禁用业务] → 本变更只承诺禁用端点的导入边界；对保留端点逐项解耦并建立独立 OpenSpec，避免范围失控。
- [第三方客户端访问被移除 API 收到 404] → 将其作为预期的不兼容变化记录在规范和发布说明中，插件安装检查后续依据能力清单阻止不兼容插件。
- [测试操作 `sys.modules` 污染其他用例] → 使用 fixture/finally 完整保存和恢复模块缓存及 import hook，并运行全量 pytest 验证隔离性。
- [能力版本 2 暂时与尚未改造的前端不一致] → 当前尚未发布正式 Lite 组合；前端变更完成并验证版本配对后才构建候选镜像。
- [仅 API 门控不足以达到资源指标] → 不在本变更宣称最终内存、镜像或启动时间目标；后续完成服务、任务和依赖裁剪后在同版本基线上统一测量。

## Migration Plan

1. 先合入能力分类和路由门控，并通过定向与全量测试。
2. 在后续前端门控、服务门控和依赖裁剪完成前，不生成正式候选版本。
3. 首次候选启动时检查 OpenAPI 及启动日志，确认禁用接口不存在、管理员登录和 115 相关存储接口可用。
4. 本变更不修改数据库或 `/config`，无需数据迁移；部署前仍按项目发布流程备份 `/config`。
5. 回退时恢复 `app/api/apiv1.py`、`app/startup/routers_initializer.py` 和能力配置版本即可；数据库和用户配置无需转换。

## Open Questions

无。保留端点的内部禁用业务解耦、前端配对版本和插件兼容门控均已明确留给后续独立变更。
