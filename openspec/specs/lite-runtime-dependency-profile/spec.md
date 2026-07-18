# lite-runtime-dependency-profile Specification

## Purpose
TBD - created by archiving change trim-lite-runtime-dependencies. Update Purpose after archive.
## Requirements
### Requirement: Lite 基础运行依赖必须使用固定禁止集合
系统 MUST 保证 `requirements.in` 及其解析后的基础运行环境不包含以下 24 个直接发行包：`langchain`、`langchain-core`、`langchain-community`、`langchain-anthropic`、`langchain-aws`、`boto3`、`langchain-openai`、`langchain-google-genai`、`langchain-deepseek`、`langgraph`、`anthropic`、`openai`、`google-genai`、`ddgs`、`qbittorrent-api`、`transmission-rpc`、`torrentool`、`fast-bencode`、`cloakbrowser`、`PyVirtualDisplay`、`redis`、`psycopg2-binary`、`asyncpg` 和 `pystray`。名称比较 MUST 规范化大小写、连字符、下划线和 extras，且上游或插件配置 MUST NOT 把这些包重新解释为基础运行依赖。

#### Scenario: 基础依赖入口不含禁止根
- **WHEN** 测试解析并规范化 `requirements.in` 的全部直接要求
- **THEN** 24 个固定禁止名称均不出现，且没有通过大小写、下划线或 extras 形式绕过

#### Scenario: 干净基础环境真实缺少禁止发行包
- **GIVEN** 一个只安装 `requirements.in` 的全新虚拟环境
- **WHEN** 测试枚举已安装发行包并尝试定位禁止模块
- **THEN** 24 个禁止发行包全部不存在，且 Playwright 等无保留根需要的专属传递包不在基础闭包中

#### Scenario: 上游重新加入禁止依赖
- **GIVEN** 上游同步在运行入口新增任一固定禁止根或等价规范化名称
- **WHEN** 候选同步运行依赖契约测试
- **THEN** 测试失败关闭并要求人工能力分类，不自动接受该依赖

### Requirement: 运行与开发依赖必须保持单一且明确的分层
系统 MUST 继续以 `requirements.in` 作为唯一正式运行依赖源，`requirements.txt` MUST 只委托该运行入口。`requirements-dev.in` MAY 为官方禁用源码兼容测试安装禁止包，但 MUST 明确分组、继续包含运行入口，且这些开发依赖 MUST NOT 被 Docker 正式运行安装、插件依赖修复或运行时自愈读取。

#### Scenario: 兼容入口保持运行时语义
- **WHEN** 解析 `requirements.txt`
- **THEN** 它只委托 `requirements.in`，不直接或间接委托开发入口

#### Scenario: 开发环境运行禁用源码测试
- **GIVEN** `requirements-dev.in` 明确列出官方 Agent、下载器、浏览器或外部数据库源码测试所需依赖
- **WHEN** 开发环境安装该入口并运行全量上游测试
- **THEN** 测试可收集禁用源码，同时正式运行依赖契约仍保持通过

#### Scenario: 插件依赖修复读取主程序入口
- **GIVEN** 管理员显式安装一个声明自身依赖的兼容插件
- **WHEN** 插件安装器检查主程序依赖与冲突
- **THEN** 主程序基线来自 `requirements.txt`/`requirements.in`，不会因此安装 `requirements-dev.in`

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

### Requirement: Lite 必须固定 SQLite 和进程内缓存
Lite MUST 在数据库与缓存工厂选择第三方后端前应用固定 capability，始终使用 SQLite 和进程内缓存。历史 `DB_TYPE=postgresql`、`CACHE_BACKEND_TYPE=redis`、连接 URL 或已保存模块状态 MUST NOT 导入驱动、创建连接池或恢复外部后端，也 MUST NOT 被删除或改写。

#### Scenario: 历史 PostgreSQL 配置安全失败关闭
- **GIVEN** `/config` 或环境中仍保存 PostgreSQL 类型和连接地址
- **WHEN** Lite 初始化数据库
- **THEN** 仅打开配置的 SQLite 数据库，不导入 `psycopg2`/`asyncpg`、不连接 PostgreSQL，并提供不含凭据的诊断

#### Scenario: 历史 Redis 配置安全失败关闭
- **GIVEN** 历史配置将同步或异步缓存设置为 Redis
- **WHEN** Lite 初始化、使用和关闭缓存
- **THEN** 只创建进程内缓存，不导入 Redis helper/客户端、不建立连接池，关闭时也不为清理而导入 Redis

#### Scenario: 配置保持可回退
- **WHEN** Lite 使用历史外部数据库或缓存配置完成启动、停止和再次启动
- **THEN** 原始类型、URL 和其他持久记录保持原样，同版本官方代码仍可读取

### Requirement: 保留能力依赖不得被体积优化误删
系统 MUST 保留 U115/其他官方存储适配器、Local/SMB/Rclone、元数据识别、文件整理、全部官方消息通知渠道、Emby/Jellyfin/Plex、管理员 OTP/Passkey 认证和容器重启所需的正式运行依赖。依赖保留 MUST 由实际导入或行为测试证明，不得仅按包大小删除。

#### Scenario: U115 与整理链可用
- **GIVEN** 禁止依赖全部缺失且 U115/Local 测试使用假的文件与网络适配器
- **WHEN** 导入存储并执行元数据识别和文件整理流程
- **THEN** `oss2` 等 U115 必需依赖可用，整理结果保持既有语义且零真实出站

#### Scenario: 通知与媒体服务器保留
- **GIVEN** 每个官方消息渠道和 Emby/Jellyfin/Plex 使用 mock 客户端
- **WHEN** 系统导入并发送通知或触发媒体服务器刷新
- **THEN** 对应保留 SDK 和响应语义可用，不因禁止依赖缺失失败

#### Scenario: 管理员认证与重启保留
- **GIVEN** 管理员使用既有密码、OTP/Passkey 或 Token 流程并请求容器重启
- **WHEN** 认证与重启路径使用 mock 系统客户端执行
- **THEN** 既有权限拒绝和成功语义保持，OTP/Passkey 与 Docker SDK未被移除

### Requirement: 插件依赖必须由显式手动安装管理
Lite MUST NOT 在基础依赖中预装 P115StrmHelper 或其第三方要求，也 MUST NOT 在启动阶段自动下载插件或补装依赖。经既有管理员认证的显式插件安装/升级 MAY 安装插件声明的兼容依赖；插件缺失、依赖冲突或安装失败 MUST NOT 阻止核心启动，也 MUST NOT 恢复固定禁用的核心能力。

#### Scenario: 未安装 P115StrmHelper
- **GIVEN** 本地没有 P115StrmHelper 代码及其专属依赖
- **WHEN** Lite 启动并初始化插件框架
- **THEN** 核心正常可用，不访问市场、不下载插件、不安装依赖且不伪造插件运行状态

#### Scenario: 管理员手动安装兼容插件
- **GIVEN** 已认证管理员显式请求安装一个声明 `numpy` 等自身依赖的兼容插件
- **WHEN** 插件安装器执行既有依赖流程
- **THEN** 依赖只作为插件部署状态安装并报告真实结果，不被写回主程序 `requirements.in`

#### Scenario: 插件试图恢复固定禁用能力
- **GIVEN** 一个插件依赖下载器、Redis、Workflow 或浏览器模拟并声明命令或定时服务
- **WHEN** Lite 进行兼容检查和加载
- **THEN** 插件被拒绝运行且命令/任务不注册，不能以安装第三方包绕过核心 capability

### Requirement: 依赖变更必须通过双环境、安全与资源验收
本变更 MUST 在开发依赖环境完成相关及全量测试、Pylint 和禁用源码兼容验证，并在只安装运行依赖的干净环境完成离线启动与保留功能验证。`requirements.txt` 与发生修改的 `requirements-dev.in` MUST 分别通过项目规定的 `safety` 扫描。资源报告 MUST 使用相同平台、解释器和测量方法，并分别标注基础环境与插件后环境。

#### Scenario: 开发环境完整回归
- **WHEN** 开发环境安装 `requirements-dev.in` 并运行质量门禁
- **THEN** 新增及全量 pytest、修改模块 Pylint 和全应用 Pylint 没有新增失败，已知平台基线被单独列出

#### Scenario: 干净运行环境离线验收
- **GIVEN** 临时配置、SQLite、进程内缓存和全部外部服务 mock
- **WHEN** 只安装 `requirements.in` 的环境连续启动并停止 Lite 两次
- **THEN** 保留 owner 正常工作，无真实出站、禁止包导入、外部数据库/缓存连接或残留后台线程

#### Scenario: 依赖安全扫描
- **WHEN** 对运行入口和已修改开发入口执行项目规定的安全扫描
- **THEN** 没有未解释的新漏洞，报告不包含 Token、Cookie、密码、真实连接地址或被提交的本地扫描产物

#### Scenario: 资源结果不夸大
- **WHEN** 比较变更前后发行包数量、安装体积、导入耗时、RSS、模块和线程
- **THEN** 报告说明平台与测量限制，基础环境和手动安装 P115StrmHelper 后状态分开，且不把 Windows 依赖估算声称为最终 Docker 镜像大小
