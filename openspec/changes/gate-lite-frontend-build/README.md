# gate-lite-frontend-build

将 MoviePilot Lite 前端从官方完整页面集合收敛为与后端 capability profile 一致的构建：保留网盘、元数据、文件整理、插件、消息通知、媒体服务器和必要设置，移除 PT、下载器、订阅、搜索发现、Agent、Workflow 及辅助认证页面和专属构建依赖。

## 当前状态

Lite 路由、菜单、PWA、动态导入和构建裁剪已经实施并提交到前端 `lite` 分支；当前配对后端导航验收已完成。本变更仍不代表 Docker 双架构候选、资源指标或真实 115 Canary 已完成。

## 实施摘要

- 路由、主菜单、应用中心、首页、PWA 和 Service Worker 已消费后端生成的 Lite capability manifest version 2。
- PT、下载器、订阅、搜索发现、Agent、Workflow、辅助认证和多用户页面不再注册或进入生产构建产物。
- 插件模块联邦和远程页面机制继续保留，P115StrmHelper 页面不编译进 Lite 核心；插件缺失或不可用时显示明确原因。
- 前端类型检查、56 个测试、覆盖率、生产构建和产物扫描已通过；配对后端导航已在生产静态产物上完成。
- 后端通过 `/api/v1/system/global` 提供非敏感 profile/version 配对信息，禁用 API 继续由后端能力门控返回 404。

本变更不构建或发布 Docker 镜像；后端 Docker 消费 Lite 前端产物另设独立集成检查点。

## 配对导航验收记录

- 验收日期：2026-07-19；平台：Windows 本地临时配置；后端提交：`c37a2763`；前端提交：`af29e494`。
- 配对清单：`profile=lite`、manifest version `2`；后端和前端能力集合一致。
- 通过项：管理员登录、`/filemanager`、`/history`、`/plugins`、`/setting`、插件缺失提示、网盘/整理设置、通知设置、Emby/Jellyfin/Plex 入口、根路径重定向和完整历史禁用 URL 404。
- API 证据：保留页面 API 返回 `200`；站点、下载器、订阅、工作流、Agent、搜索和 MCP 前缀返回 `404`；生产产物导航没有控制台错误或 `4xx/5xx` 请求。
- 未覆盖：真实 115 授权/转存、Docker `amd64/arm64` 候选、资源指标和 Canary。
- 已知限制：后端启动仍记录 `No module named 'app.helper.sites'` 数据库更新告警；Vite 开发服务器扫描已移除页面时会报告缺失的 `@vue-flow/*` 与 `@fullcalendar/*` 依赖并触发依赖重优化，验收使用已通过生产构建的静态产物；通知页面保留下载、订阅、站点和智能体等历史通知分类；仓库内 `dist/service.js` 在 `type=module` 环境中直接运行会遇到 CommonJS `require` 兼容问题，Docker 运行尚未验证。
