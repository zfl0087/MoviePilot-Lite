## Context

MoviePilot Lite 的候选镜像由固定后端和前端提交构建到私有 GHCR，再按摘要同步到公开 Docker Hub。公开分发需要同时满足 GPLv3 源码可得性、不可变产物追溯、预览/稳定门禁和敏感信息边界。

## Goals / Non-Goals

### Goals

- 让每个公开镜像都能追溯到官方基线、Lite 前后端提交和 OCI 摘要。
- 为不熟悉 GitHub 或 Docker 的用户提供可执行的安装与回退说明。
- 明确 rc.7 已验证和未验证项目，避免把部分 Canary 证据宣传成完整兼容。
- 保证公开文档符合 GPLv3，不增加非商业或禁止再分发条款。

### Non-Goals

- 本变更不修改应用运行时功能。
- 本变更不自动改变 GitHub 仓库可见性、创建标签或 Release。
- 本变更不把 rc.7 提升为稳定版，也不补做真实 115 工作流验收。

## Decisions

### 使用仓库内 JSON 作为机器可读发布记录

`releases/<version>.json` 固定记录官方与 Lite 提交、能力配置版本、镜像仓库、标签、摘要、平台、插件版本、Canary 状态和回退要求。测试拒绝浮动标签、不完整 SHA、无摘要或把未完成 Canary 的版本标为 stable。

### 保留私有 GHCR，公开 Docker Hub

GHCR 继续作为受控候选源。Docker Hub 只接受按摘要的人工同步；已有同名标签若指向不同摘要则失败。同步报告额外写入 Lite 前后端完整提交。

### RC 只发布 preview

带 `-rc.<n>` 的版本只能成为 GitHub Pre-release/preview。只有真实 115 转存、完整 STRM、消息回传、媒体服务器刷新和其他稳定门禁完成后，才可创建无 RC 的 stable 版本。

## Risks / Trade-offs

- 文档中的源码链接在仓库真正改为 Public 前不可匿名访问；可见性变更必须在秘密扫描后单独批准。
- Docker Hub 标签本身可被仓库所有者改写，因此安装说明同时固定 digest，用户必须保存并核对摘要。
- P115StrmHelper 是独立第三方插件，Lite 只能记录经过测试的版本和范围，不能替插件承诺所有功能或隐私行为。

## Migration Plan

1. 在隔离分支完成文档、发布记录、测试和工作流追溯字段。
2. 验证后提交并推送，但不立即公开仓库。
3. 扫描后端和前端完整历史、Actions 产物与发布上下文中的秘密。
4. 经单独批准后同时公开两个源码仓库，并验证匿名访问。
5. 经单独批准后创建不可变标签和 GitHub Pre-release。
