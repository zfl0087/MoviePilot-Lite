## MODIFIED Requirements

### Requirement: 禁止依赖缺失时保留运行链必须可导入和启动
Lite MUST 在全部固定禁止包均未安装时导入并运行应用生命周期、Scheduler、Command、MessageChain、Monitor、TransferChain、PluginManager、保留存储、元数据、整理、通知、媒体服务器、管理员认证链、Doctor 和 Docker 启动探针。类型注解、公共 Schema、模块 `__init__`、历史禁用方法、Doctor 或容器依赖修复 MUST NOT 在模块顶层或启动阶段恢复禁止依赖；Doctor 与 entrypoint 的核心依赖集合 MUST 从正式 `requirements.in` 合同派生或由同一测试约束。

#### Scenario: 干净解释器导入保留链
- **GIVEN** 解释器只安装正式运行依赖且禁止包导入会立即失败
- **WHEN** 独立进程导入全部保留启动和业务模块
- **THEN** 导入成功，`sys.modules` 不包含 Agent/LLM、PT/下载器、浏览器、Redis/PostgreSQL 或 pystray 专属模块

#### Scenario: Doctor 不要求浏览器依赖
- **GIVEN** 正式运行环境没有 CloakBrowser、Playwright 或虚拟显示包
- **WHEN** 执行 `moviepilot doctor`
- **THEN** 浏览器缺失不产生核心依赖错误，真实核心 Python 包缺失仍按既有严重级别报告

#### Scenario: 容器依赖修复不恢复禁用包
- **GIVEN** entrypoint 启动前检查正式核心依赖
- **WHEN** 探针失败并从 `/app/requirements.txt` 执行允许的依赖修复
- **THEN** 只恢复 Lite 主程序依赖，不读取 `requirements-dev.in`、不安装 CloakBrowser/Playwright，也不为未安装插件补依赖

#### Scenario: 普通消息进入插件事件
- **GIVEN** 消息渠道收到普通 115 分享链接且存在假的兼容插件消费者
- **WHEN** MessageChain 处理并派发既有插件事件
- **THEN** 事件字段和权限语义保持官方行为，且不导入 TorrentHelper、下载器客户端、Agent 或浏览器包

#### Scenario: 禁用历史方法被误调用
- **GIVEN** 调用方通过历史内部入口尝试执行下载器、Agent、浏览器或外部数据库路径
- **WHEN** 固定 Lite capability 检查该请求
- **THEN** 在解析对应第三方包之前返回明确不支持结果，不以 `ModuleNotFoundError` 或宽泛异常作为正常控制流
