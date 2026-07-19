## ADDED Requirements

### Requirement: 候选输入必须固定且可追溯

候选构建 MUST 使用完整后端 SHA、完整前端 SHA 和显式候选版本。构建报告、OCI labels 和镜像清单 MUST 能互相追溯到同一组输入。

#### Scenario: 分支或浮动标签被拒绝

- **GIVEN** 工作流输入包含分支名、`latest` 或非完整 SHA
- **WHEN** 候选构建开始
- **THEN** 工作流在检出或构建前失败，不生成或推送镜像

#### Scenario: 前后端提交配对可审计

- **GIVEN** 后端和前端完整 SHA 均存在且门禁通过
- **WHEN** 生成候选镜像
- **THEN** 镜像 labels、候选报告和多架构清单记录相同的前后端 SHA

### Requirement: 候选必须消费固定前端产物

候选 Docker 构建 MUST 使用由指定前端 SHA 生成且通过 Lite 门禁的产物。候选路径 MUST NOT 再次下载官方浮动 Release 或使用未验证的工作区 `dist`。

#### Scenario: 前端 SHA 不存在

- **GIVEN** 私有前端仓库中不存在指定 SHA 或仓库读取权限不足
- **WHEN** 工作流准备前端产物
- **THEN** 工作流失败且不回退到官方 Release

#### Scenario: 前端门禁失败

- **GIVEN** 前端类型检查、Lite 测试、覆盖率、构建或产物扫描任一失败
- **WHEN** 工作流进入 Docker 构建阶段
- **THEN** Docker 构建和 GHCR 推送步骤不执行

### Requirement: 候选工作流必须手动触发且权限最小化

候选工作流 MUST 仅声明 `workflow_dispatch` 触发；默认只读仓库内容，只有受保护的推送步骤可以写入 GHCR。工作流 MUST NOT 向 `upstream`、Docker Hub 或公开 Release 写入。

#### Scenario: 普通提交不会自动发布

- **GIVEN** `lite` 分支收到普通提交或上游同步提交
- **WHEN** GitHub Actions 事件触发
- **THEN** 候选工作流不自动构建或推送镜像

#### Scenario: 未经过环境审批

- **GIVEN** 构建和验证通过但 `lite-candidate` 环境尚未批准
- **WHEN** 工作流到达推送步骤
- **THEN** 工作流暂停在保护环境，不向 GHCR 写入候选

### Requirement: 候选必须同时通过双架构和内容门禁

候选 MUST 使用同一组固定输入构建 `linux/amd64` 与 `linux/arm64`。两平台均 MUST 通过 Lite Docker 内容合同、干净容器启动/停止和保留能力模拟测试；任一失败都 MUST 阻止候选推送。

#### Scenario: 单架构构建失败

- **GIVEN** `linux/amd64` 或 `linux/arm64` 构建失败、缺少 digest 或元数据不一致
- **WHEN** 工作流汇总平台结果
- **THEN** 候选状态为失败且不推送多架构标签

#### Scenario: 禁止内容重新进入镜像

- **GIVEN** 最终镜像包含浏览器、`ffmpeg`、PT 资源、预装插件或原地更新器
- **WHEN** 内容合同扫描运行
- **THEN** 候选失败且不进入 Canary

### Requirement: 候选报告必须区分模拟证据与真实验证

候选报告 MUST 记录前后端提交、平台 digest、构建产物、门禁结果和资源测量原始值。报告 MUST 明确标注真实 115、P115StrmHelper、媒体服务器和消息渠道尚未在 CI 验证，并不得把模拟结果写成生产支持承诺。

#### Scenario: 报告缺少资源或平台证据

- **GIVEN** 任一平台 digest、资源原始值或门禁结果缺失
- **WHEN** 工作流准备候选摘要
- **THEN** 候选不可发布，推送步骤不执行

#### Scenario: 真实凭据进入 CI

- **GIVEN** 日志或报告检测到真实 115、消息渠道或媒体服务器凭据
- **WHEN** 秘密扫描运行
- **THEN** 工作流失败并阻止产物发布
