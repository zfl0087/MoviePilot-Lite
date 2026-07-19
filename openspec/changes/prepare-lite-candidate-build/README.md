# prepare-lite-candidate-build

为 MoviePilot Lite 建立私有、可追溯的双架构候选镜像构建流程。该变更只定义候选构建与证据合同，不执行镜像构建、GHCR 推送、Canary 部署或生产升级。

## 当前状态

前后端 Lite 实现已经分别推送到私有 `origin/lite`：后端固定提交为 `cb8e3f8b`，前端固定提交为 `af29e494`。本机没有 Docker CLI，因此候选构建必须在受控 GitHub Actions 环境完成。

## 关键边界

- 只允许手动触发候选工作流，不因普通 push、上游同步或定时检查自动发布镜像。
- 构建必须同时覆盖 `linux/amd64` 和 `linux/arm64`，并将前端固定提交构建出的产物注入镜像；不得仅下载官方浮动 Release 作为配对证明。
- 镜像目标为私有 GHCR 候选包，禁止 Docker Hub、公开 Release、`latest` 或推送 `upstream`。
- 构建、静态内容合同、干净启动和资源报告全部通过后，才允许进入后续 Canary 讨论。
- 本变更不接触真实 115 Token、消息渠道凭据、媒体服务器凭据或生产 `/config`。
