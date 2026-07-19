# gate-lite-frontend-build

将 MoviePilot Lite 前端从官方完整页面集合收敛为与后端 capability profile 一致的构建：保留网盘、元数据、文件整理、插件、消息通知、媒体服务器和必要设置，移除 PT、下载器、订阅、搜索发现、Agent、Workflow 及辅助认证页面和专属构建依赖。

## 当前状态

只读审计已完成，前端 `lite` 仍基于官方提交 `435e9ec`，尚未实施 Lite 路由、菜单、PWA、动态导入或构建裁剪。本变更先建立跨后端/前端的能力清单与产物合同，后续再按独立审批实施前端代码和测试。

## 审计摘要

- `src/router/index.ts` 仍直接注册搜索、订阅、下载、站点、发现和 Workflow 页面；当前守卫只按用户权限处理，未消费 Lite capability profile。
- `src/router/i18n-menu.ts`、应用中心和搜索面板共享官方完整菜单集合，PWA 快捷方式及 Service Worker 预缓存尚未按 Lite 能力裁剪。
- `package.json` 仍包含官方完整前端依赖；`@vue-flow/*`、`@vue-js-cron/vuetify`、日历、编辑器等是否专属于禁用页面，必须逐项审计后才能删除。
- 插件模块联邦和远程页面机制必须继续保留，P115StrmHelper 页面不得编译进 Lite 核心。
- 后端已提供固定 `get_lite_capability_manifest()`，并可通过现有 `/api/v1/system/global` 初始化响应完成 profile/version 配对检查。

本变更不构建或发布 Docker 镜像；后端 Docker 消费 Lite 前端产物另设独立集成检查点。
