# Change: 准备 MoviePilot Lite 公开预览发布

## Why

当前 Docker Hub 镜像已经可以公开拉取，但源码、镜像摘要、前后端提交、Canary 证据和安装边界尚未形成统一、机器可读且符合 GPLv3 的公开发布合同。直接分享会让使用者难以验证镜像来源、判断已验证范围并可靠回退。

## What Changes

- 将项目定位更新为非官方社区精简构建，允许公开自托管分发。
- 明确 GPLv3 权利，不把维护者“不运营 SaaS、不销售支持”的选择写成附加许可限制。
- 为 `v2.14.5-lite.1-rc.7` 建立固定镜像、摘要、官方基线、Lite 前后端提交和 Canary 状态记录。
- 增加公开安装、备份、升级、回退和安全报告文档。
- 要求 Docker Hub 同步工作流校验并记录 Lite 前后端完整提交。
- 将未完成真实 115 工作流验收的 RC 固定标记为 preview，不发布 `latest`。

## Impact

- Affected docs: `PROJECT_BRIEF.md`, `README.md`, `docs/UPSTREAM_SYNC.md`, `docs/COMPATIBILITY.md`, `docs/PUBLIC_RELEASE.md`, `SECURITY.md`.
- Affected automation: `.github/workflows/lite-dockerhub-sync.yml`.
- New release contract: `releases/*.json` and its regression test.
- No application runtime behavior changes in this change.
