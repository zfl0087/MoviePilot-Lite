## Why

MoviePilot Lite 后端已经在 API、模块、启动、消息、依赖和 Docker 运行时建立固定 capability profile，但前端仍是官方完整页面和构建图。仅依赖权限过滤或隐藏菜单会让禁用页面继续注册、动态导入并进入最终 bundle，无法满足 Lite 的资源目标，也会让用户通过历史 URL 看到不属于产品范围的入口。

## What Changes

- 让前端消费后端生成的 profile、version、enabled 和 disabled capability manifest，不维护第二份 Lite 功能清单。
- 在路由、菜单、应用中心、搜索入口、首页重定向、PWA 快捷方式和 Service Worker 预缓存之前完成能力筛选。
- 保留管理员登录、网盘/文件管理、元数据识别、文件整理与历史、插件机制、消息通知、媒体服务器和必要系统设置。
- 从前端路由和构建图移除 PT 站点/认证、下载器、订阅、搜索发现、Agent/LLM/MCP/Skills、Workflow、多用户/SSO/MFA/Passkey、Radarr/Sonarr 和 CookieCloud 入口。
- 仅删除经过使用点审计、确认不服务保留页面或插件模块联邦的禁用专属依赖；共享依赖继续保留。
- 使用现有 `/api/v1/system/global` 的非敏感 profile/version 字段进行运行时配对检查，版本不一致时失败关闭并显示可诊断错误。
- 保留插件动态路由和远程组件边界，插件页面只能在后端确认已安装、启用且兼容后加载。
- 为前端类型检查、路由矩阵、构建产物和依赖排除增加自动化验证。

## Capabilities

### New Capabilities

- `lite-frontend-build-profile`: 定义 Lite 前端统一能力清单、路由/PWA/构建裁剪、插件边界和前后端版本配对合同。

### Modified Capabilities

- `lite-capability-profile`: 明确后端 manifest 是前端唯一能力来源，并通过系统初始化响应提供 profile/version 配对信息。

## Impact

- 前端仓库：修改路由组合、菜单生成、应用中心、PWA/Service Worker 配置、构建输入和相关测试；不改变 MoviePilot 基础视觉语言。
- 后端仓库：扩展现有非敏感系统初始化响应以返回 capability profile/version，并补充 manifest 合同测试；不新增认证绕过或数据库迁移。
- API：保留接口路径和认证语义不变，仅在既有 `/system/global` 响应增加非敏感配对字段；后端仍是禁用能力的安全边界。
- 插件：保留模块联邦、远程组件和动态插件路由；P115StrmHelper 继续手动安装，不进入核心 bundle。
- 依赖：只移除确认仅服务禁用页面的前端依赖，任何共享或插件联邦依赖必须保留并记录原因。
- Docker：本变更定义 Lite 前端产物合同，但不修改 Dockerfile；后续变更负责固定消费对应 Lite 前端提交或产物。
- 上游同步：集中修改前端路由/菜单/构建组合点，保留官方页面源码历史；上游新增页面默认未启用，必须先完成能力分类。
- 资源：目标是减少禁用页面、专属依赖、PWA 预缓存和 bundle 体积；最终镜像、启动和 RSS 指标留待前端与 Docker 集成后统一测量。
