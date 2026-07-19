## 1. 方案与权限基线

- [ ] 1.1 审阅当前后端 `lite` 提交、前端 `lite` 提交和 Docker 内容合同，记录候选输入与已知环境限制
- [ ] 1.2 确认私有前端仓库只读访问方式、GHCR 包名、`lite-candidate` Environment 和人工审批人，不创建个人长期 Token
- [ ] 1.3 为工作流建立最小权限清单：`contents: read`、受保护推送步骤的 `packages: write`，签名需要时才增加 `id-token: write`

## 2. 前端固定产物

- [ ] 2.1 在候选工作流中检出指定前端完整 SHA，并运行既有 Lite 测试、类型检查、覆盖率、生产构建和产物扫描
- [ ] 2.2 生成带前端 SHA、文件数、字节数和哈希的不可变前端归档
- [ ] 2.3 增加失败测试，证明前端 SHA 不存在、门禁失败或产物哈希变化时不会进入 Docker 构建

## 3. Docker 候选输入

- [ ] 3.1 为 `docker/Dockerfile` 增加候选前端产物输入，并保留非候选源码安装路径的既有行为
- [ ] 3.2 在 Docker 合同测试中断言候选构建不下载官方前端 Release，不消费未验证工作区 `dist`
- [ ] 3.3 在镜像 labels 和 Doctor/版本诊断输出中记录后端 SHA、前端 SHA 和候选版本

## 4. 手动双架构工作流

- [ ] 4.1 创建 `.github/workflows/lite-candidate.yml`，只使用 `workflow_dispatch` 和完整 SHA 输入
- [ ] 4.2 使用 Buildx 构建 `linux/amd64` 与 `linux/arm64`，分别保存 digest 和平台日志
- [ ] 4.3 添加镜像内容扫描、物理缺失检查、干净容器连续启动/停止和保留能力模拟测试
- [ ] 4.4 添加资源测量步骤，记录相同官方版本/配置下的镜像体积、冷启动、空闲 RSS/CPU 原始值与方法
- [ ] 4.5 配置 `lite-candidate` Environment 审批后才允许写入 `ghcr.io/zfl0087/moviepilot-lite`
- [ ] 4.6 将候选清单、报告和 digest 作为 Actions artifact 保存，失败时不得写入 `latest` 或公开渠道

## 5. 验证与收尾

- [ ] 5.1 在无真实凭据的 CI 运行前端门禁、后端相关 pytest、OpenSpec 严格校验和秘密扫描
- [ ] 5.2 在具备 Docker Buildx 的受控环境运行一次不推送的双架构候选演练
- [ ] 5.3 检查工作流权限、日志和 artifacts 不含 Token、Cookie、`/config` 或消息渠道秘密
- [ ] 5.4 提交并推送实现前停下，向用户报告差异、测试结果、候选 digest 生成方式和下一审批点
- [ ] 5.5 获得单独批准后才运行 GHCR 候选推送；推送后仍不得自动部署 Canary
