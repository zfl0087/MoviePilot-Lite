## ADDED Requirements

### Requirement: 公开镜像必须可追溯到完整对应源码

每个公开 MoviePilot Lite 镜像 MUST 记录官方后端和前端基线、Lite 后端和前端完整 SHA、能力配置版本、OCI 摘要和平台；对应 GPLv3 源码 MUST 可由接收者取得。记录 MUST NOT 包含 Token、Cookie、密码或真实 `/config` 数据。

#### Scenario: 用户验证公开镜像来源

- **GIVEN** 一个公开 Docker Hub Lite 镜像
- **WHEN** 用户查看该版本的仓库发布记录
- **THEN** 用户能够找到镜像摘要、官方基线和 Lite 前后端完整提交

### Requirement: 公开镜像必须使用不可变版本合同

公开安装说明 MUST 同时给出完整版本标签和 `sha256:` 摘要，MUST NOT 推荐 `latest`。同步工作流 MUST 拒绝覆盖已经指向不同摘要的同名标签，并 MUST 验证 `linux/amd64` 和 `linux/arm64`。

#### Scenario: 同名标签摘要不一致

- **GIVEN** Docker Hub 已存在相同标签但摘要不同
- **WHEN** 维护者执行同步工作流
- **THEN** 工作流失败且不覆盖既有标签

### Requirement: RC 必须与稳定版分离

带 `-rc.<n>` 的版本 MUST 标记为 `preview` 和 GitHub Pre-release。只有发布记录的 Canary 状态为 `complete` 且稳定门禁全部通过时，版本 MAY 标记为 `stable`。

#### Scenario: 部分真实工作流尚未验证

- **GIVEN** 真实 115 转存、完整 STRM、消息回传或媒体服务器刷新仍有未完成项
- **WHEN** 维护者创建发布记录
- **THEN** 版本保持 preview，并明确列出未验证项目

### Requirement: 公开发布必须清晰标记非官方身份

README、安装文档和 Release MUST 明确 MoviePilot Lite 是非官方社区构建，不代表 MoviePilot 官方。核心镜像 MUST NOT 声称内置 P115StrmHelper；文档 MUST 说明受支持插件版本需要手动安装。

#### Scenario: 新用户阅读安装说明

- **GIVEN** 用户首次打开公开安装文档
- **WHEN** 用户准备部署镜像
- **THEN** 用户可以看到非官方声明、固定镜像、备份与回退要求、手动插件版本和未验证范围

### Requirement: 公开前必须完成秘密审计

后端和前端仓库在改为 Public 前 MUST 扫描当前文件和完整 Git 历史，并审查 Actions 日志、Artifacts、Release 和 Docker 构建上下文。发现真实凭据、数据库或真实 `/config` 数据时 MUST 阻止公开。

#### Scenario: 历史中发现疑似秘密

- **GIVEN** 秘密扫描产生未解释的高置信度结果
- **WHEN** 维护者准备改变仓库可见性
- **THEN** 公开步骤被阻止，直到凭据处置和历史清理完成

### Requirement: GPLv3 声明不得增加商业限制

维护者 MAY 声明自己不销售支持或不运营 SaaS，但公开文档 MUST NOT 禁止接收者依据 GPLv3 使用、修改、再分发或收费分发。

#### Scenario: 维护者声明运营选择

- **GIVEN** README 说明维护者不运营 SaaS
- **WHEN** 用户阅读许可证段落
- **THEN** 同一段落明确该选择不限制 GPLv3 授予的权利
