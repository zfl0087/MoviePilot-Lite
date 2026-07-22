## 1. 公开发布文档

- [x] 1.1 更新 `PROJECT_BRIEF.md` 的项目性质、分发边界和当前状态。
- [x] 1.2 更新 `README.md` 的预览状态、固定镜像、插件说明和 GPLv3 声明。
- [x] 1.3 更新 `docs/UPSTREAM_SYNC.md` 的公开 Docker Hub、preview/stable 和追溯流程。
- [x] 1.4 更新 `docs/COMPATIBILITY.md` 的 rc.7 证据和未验证范围。
- [x] 1.5 创建 `docs/PUBLIC_RELEASE.md` 与 `SECURITY.md`。

## 2. 机器可读发布记录

- [x] 2.1 先创建失败的 `tests/test_public_release_records.py`。
- [x] 2.2 创建 `releases/v2.14.5-lite.1-rc.7.json`。
- [x] 2.3 验证 preview、完整 SHA、双架构、固定摘要和无 `latest`。

## 3. Docker Hub 同步追溯

- [x] 3.1 先扩展同步工作流测试并确认失败。
- [x] 3.2 在工作流中校验 Lite 前后端完整 SHA 并写入同步报告。
- [x] 3.3 运行同步、候选和发布记录合同测试。

## 4. 公开前秘密与产物审计

- [x] 4.1 扫描后端和前端当前文件及完整 Git 历史。
- [x] 4.2 检查 Actions 日志、Artifacts、Release 和 Docker 构建上下文。
- [x] 4.3 记录工具、范围、结果、误报和未完成项。
- [x] 4.4 停在仓库公开可见性审批点。
- [x] 4.5 加固 `.dockerignore` 的本地敏感文件排除规则并增加合同测试。

## 5. 公开源码仓库

- [x] 5.1 确认固定提交已经推送且工作树没有敏感文件。
- [ ] 5.2 经单独批准后将前后端仓库改为 Public。
- [ ] 5.3 匿名验证固定提交、LICENSE、构建脚本和发布记录可读。
- [ ] 5.4 更新 Docker Hub 描述并链接公开源码和安装文档。

## 6. 创建公开预览 Release

- [ ] 6.1 经单独批准后创建不可变前后端标签。
- [ ] 6.2 创建 GitHub Pre-release，写明摘要、源码、安装、回退和未验证项。
- [ ] 6.3 从匿名环境完成端到端公开访问与拉取验证。
