## ADDED Requirements

### Requirement: 稳定且完整的能力分类
系统 MUST 定义稳定、唯一的 MoviePilot Lite 能力标识。启用能力 MUST 为 `system`、`admin-auth`、`cloud-storage`、`metadata`、`media-organization`、`plugins`、`messaging`、`notifications` 和 `media-server`；禁用能力 MUST 为 `pt-sites`、`pt-site-auth`、`torrent-search`、`downloaders`、`subscriptions`、`content-discovery`、`agent`、`llm`、`mcp`、`skills`、`voice-processing`、`workflow`、`cookiecloud`、`browser-automation`、`redis`、`postgresql`、`multi-user`、`sso`、`arr-compat` 和 `ffmpeg-transcoding`。每个已定义能力 MUST 恰好归入启用或禁用集合之一。

#### Scenario: 能力被完整分类
- **WHEN** 系统枚举 Lite 配置中的全部能力
- **THEN** 每个能力恰好出现于启用集合或禁用集合之一，且两个集合没有交集

#### Scenario: 保留能力查询
- **WHEN** 调用方查询 `cloud-storage`、`metadata` 或 `plugins`
- **THEN** 系统返回这些能力已启用

#### Scenario: 移除能力查询
- **WHEN** 调用方查询 `pt-site-auth`、`downloaders`、`agent` 或 `workflow`
- **THEN** 系统返回这些能力未启用

### Requirement: 固定且不可变的 Lite 配置
系统 MUST 使用固定名称 `lite` 和正整数配置版本标识该能力配置。启用与禁用集合 MUST 在进程生命周期内不可变，且环境变量、用户设置和 `/config` 内容 MUST NOT 改写能力状态。

#### Scenario: 运行配置不能恢复禁用能力
- **WHEN** 环境变量、用户设置或历史 `/config` 中存在与 `agent` 或 `downloaders` 同名的启用值
- **THEN** Lite 能力查询仍返回相应能力未启用

#### Scenario: 调用方尝试修改能力集合
- **WHEN** 调用方尝试向启用集合添加能力或从中删除能力
- **THEN** 修改失败，后续查询结果保持不变

### Requirement: 未知能力安全失败
系统 MUST 拒绝未定义的能力标识和错误类型，不得因拼写错误、未知上游能力或宽松字符串比较而将其视为已启用。

#### Scenario: 查询未知能力
- **WHEN** 调用方查询一个未在能力枚举中定义的标识
- **THEN** 系统返回明确错误，且不改变任何能力状态

#### Scenario: 查询参数类型错误
- **WHEN** 调用方绕过能力枚举并传入不受支持的参数类型
- **THEN** 系统返回类型错误，而不是根据真值或字符串相等关系放行

### Requirement: 确定性的机器可读清单
系统 MUST 能生成不包含秘密信息的机器可读清单。清单 MUST 包含配置名称、配置版本、按标识排序的启用列表和按标识排序的禁用列表；相同代码版本的重复生成结果 MUST 完全一致，调用方修改返回对象 MUST NOT 改变内部能力状态。

#### Scenario: 重复生成清单
- **WHEN** 在同一代码版本中连续生成两次能力清单
- **THEN** 两次结果的字段、值和列表顺序完全一致

#### Scenario: 修改返回对象
- **WHEN** 调用方修改一次清单生成结果中的列表或字段
- **THEN** 下一次生成的清单及内部能力查询不受影响

#### Scenario: 清单不泄露部署信息
- **WHEN** 系统生成能力清单
- **THEN** 清单只包含能力契约字段，不包含密码、Cookie、Token、路径或其他部署配置

### Requirement: 能力模块保持导入隔离
能力配置模块 MUST 仅依赖 Python 标准库和静态常量。导入该模块 MUST NOT 导入 API、Chain、业务模块、数据库、插件管理器或外部服务，也 MUST NOT 访问网络、文件系统、数据库或 `/config`。

#### Scenario: 在最小环境中导入
- **WHEN** 测试进程仅导入能力配置模块且未安装非必要业务依赖
- **THEN** 导入成功，并且没有初始化数据库、插件、后台线程或外部连接

#### Scenario: 非目标依赖缺失
- **WHEN** PT、下载器、Agent、Redis、PostgreSQL 或浏览器自动化专属依赖不存在
- **THEN** 能力配置模块仍可正常导入并返回固定 Lite 配置

### Requirement: 本变更不改变现有运行行为
仅增加能力配置定义时，系统 MUST NOT 自动将该定义接入路由、模块、服务、任务、命令、插件或前端。实际裁剪 MUST 由后续经过独立审批和验证的变更完成。

#### Scenario: 引入配置后的应用行为
- **WHEN** 当前应用在尚未实施后续能力门控变更的情况下启动
- **THEN** 已有路由注册、模块扫描和生命周期行为保持不变

#### Scenario: 禁用能力尚未接入门控
- **WHEN** 能力清单将某项能力标记为禁用但对应后续门控尚未实施
- **THEN** 系统不会声称该能力已经完成运行时或构建期裁剪
