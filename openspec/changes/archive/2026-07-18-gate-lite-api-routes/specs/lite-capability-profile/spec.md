## MODIFIED Requirements

### Requirement: 稳定且完整的能力分类
系统 MUST 定义稳定、唯一的 MoviePilot Lite 能力标识。启用能力 MUST 为 `system`、`admin-auth`、`cloud-storage`、`metadata`、`media-organization`、`plugins`、`messaging`、`notifications` 和 `media-server`；禁用能力 MUST 为 `pt-sites`、`pt-site-auth`、`torrent-search`、`downloaders`、`subscriptions`、`content-discovery`、`agent`、`llm`、`mcp`、`skills`、`voice-processing`、`workflow`、`cookiecloud`、`browser-automation`、`redis`、`postgresql`、`multi-user`、`sso`、`auxiliary-auth`、`arr-compat` 和 `ffmpeg-transcoding`。每个已定义能力 MUST 恰好归入启用或禁用集合之一。

#### Scenario: 能力被完整分类
- **WHEN** 系统枚举 Lite 配置中的全部能力
- **THEN** 每个能力恰好出现于启用集合或禁用集合之一，且两个集合没有交集

#### Scenario: 保留能力查询
- **WHEN** 调用方查询 `cloud-storage`、`metadata` 或 `plugins`
- **THEN** 系统返回这些能力已启用

#### Scenario: 移除能力查询
- **WHEN** 调用方查询 `pt-site-auth`、`auxiliary-auth`、`downloaders`、`agent` 或 `workflow`
- **THEN** 系统返回这些能力未启用

### Requirement: 固定且不可变的 Lite 配置
系统 MUST 使用固定名称 `lite` 和正整数配置版本标识该能力配置。能力分类、清单字段或对外契约发生变化时，配置版本 MUST 递增；本能力分类的配置版本 MUST 为 2。启用与禁用集合 MUST 在进程生命周期内不可变，且环境变量、用户设置和 `/config` 内容 MUST NOT 改写能力状态。

#### Scenario: 运行配置不能恢复禁用能力
- **WHEN** 环境变量、用户设置或历史 `/config` 中存在与 `agent` 或 `downloaders` 同名的启用值
- **THEN** Lite 能力查询仍返回相应能力未启用

#### Scenario: 调用方尝试修改能力集合
- **WHEN** 调用方尝试向启用集合添加能力或从中删除能力
- **THEN** 修改失败，后续查询结果保持不变

#### Scenario: 能力分类变更递增版本
- **WHEN** `auxiliary-auth` 被加入固定能力分类并出现在机器可读清单中
- **THEN** 清单中的配置版本为 2，且高于变更前的版本 1

## REMOVED Requirements

### Requirement: 本变更不改变现有运行行为
**Reason**: 该要求仅用于能力配置首次落地时约束变更范围；API 路由门控现已按独立变更获批、实现并验证，继续保留会与正式 `lite-api-route-gating` 规范冲突。

**Migration**: API 导入与注册行为由 `lite-api-route-gating` 正式规范约束；模块、服务、任务、命令、插件和前端仍须分别通过后续独立变更接入能力门控。
