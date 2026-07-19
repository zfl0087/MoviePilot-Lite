## Context

后端私有仓库和前端私有仓库相互独立。后端 Dockerfile 当前可按 `version.py` 下载官方前端 `dist.zip`，但候选必须验证私有前端提交。当前开发主机没有 Docker CLI，不能把 Windows 静态检查当作 Linux 镜像证据。

## Decisions

### 1. 候选输入必须不可变

工作流只接受完整 40 位 SHA 和显式候选版本，例如：

```text
backend_sha=cb8e3f8bc44e696215f93200e2a6452e17e53979
frontend_sha=af29e494d7f468657eec263d5e05f66333e85aaf
candidate_version=v2.x.y-lite.1-rc.1
```

分支名、`latest`、Release 标签和未固定的依赖版本不能作为候选的唯一输入。工作流必须把两份 SHA 写入镜像标签、OCI labels 和候选报告。

### 2. 前端产物由固定 SHA 生成并注入

工作流先检出前端私有仓库的固定 SHA，运行既有 Lite 前端门禁并生成 `dist`。Docker 构建接口增加显式的候选前端产物输入；候选路径不得再次从官方 Release 下载前端。普通源码安装路径可以保留官方既有行为，但候选镜像必须使用已校验的归档或 BuildKit 命名上下文。

### 3. 工作流手动触发且权限最小化

工作流只使用 `workflow_dispatch`。默认权限为 `contents: read`，只有最终推送步骤获得 `packages: write`；如启用签名/证明，再单独授予 `id-token: write`。私有前端仓库读取使用 GitHub App 或仓库级只读凭据，不能把个人 Token 写入日志、命令参数或产物。

候选推送使用专门的 GitHub Environment，例如 `lite-candidate`，由环境保护规则提供人工审批。构建和验证失败时不得执行推送步骤。

### 4. 双架构必须同一候选配对

Buildx 使用同一后端 SHA、前端 SHA、Dockerfile 和构建参数生成 `linux/amd64`、`linux/arm64` 清单。任一平台失败、平台间标签/提交元数据不一致或只生成单架构，都判定候选失败。候选标签使用完整版本和 RC 号，不覆盖 `latest`。

### 5. 报告和门禁分层

工作流产物至少包括：

- 后端/前端 SHA、上游基线、候选版本和构建时间；
- 前端测试、类型检查、覆盖率、模块数、预缓存项数和产物字节数；
- 两个平台的镜像 digest、压缩/解压体积和内容合同结果；
- 干净容器连续启动/停止结果、保留 API/插件入口模拟结果和失败原因；
- 资源测量方法、设备/配置、空闲 RSS/CPU、冷启动时间和与相同官方版本的对比。

静态合同与模拟测试可以在 CI 完成；真实 115 转存、P115StrmHelper、媒体服务器和消息渠道只允许在后续隔离 Canary 完成。没有资源报告或真实 Canary，不得把候选称为正式支持版本。

### 6. 镜像命名与回滚

候选镜像使用私有 GHCR 包名 `ghcr.io/zfl0087/moviepilot-lite`，标签包含完整 Lite 版本和 RC 号。工作流输出 digest 作为部署唯一引用。回滚通过切换到上一个已验证 digest 完成，不修改 `/config`，不执行容器内原地更新。

## Failure Handling

- 前端构建、Docker 内容合同、任一架构构建、干净启动或资源门禁失败：停止流程，不推送候选。
- GHCR 推送成功但报告上传失败：候选标记为不可用，不进入 Canary，保留 digest 供维护者清理。
- 私有前端仓库不可读或 SHA 不存在：在构建前失败，不回退到官方 Release。
- 发现凭据出现在日志或报告：立即撤销候选、删除报告并轮换凭据；不得继续部署。

## Approval Checkpoints

1. 批准本 OpenSpec 变更及工作流权限范围。
2. 实现并验证工作流、Docker 前端产物输入和合同测试后，单独批准创建候选构建运行。
3. 候选 digest 和资源报告生成后，单独批准隔离 Canary；生产升级另行批准。
