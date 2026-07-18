## Context

此前四层 Lite 门控已经让禁用路由、模块、启动 owner、系统任务和消息交互不再运行，但依赖清单尚未收敛。当前 `requirements.in` 在 Windows 开发环境形成约 594.06 MiB 的 168 包闭包，其中 54 个发行包、约 280.28 MiB 只由 24 个非目标直接依赖引入。最大部分来自 Agent/LLM（约 157.64 MiB）和 CloakBrowser/Playwright（约 106.36 MiB）。

运行依赖删除不能仅根据模块目录判断。`app.chain.message` 的保留事件路径仍顶层引用 TorrentHelper，而数据库选择仍接受历史 PostgreSQL 配置。另一方面，U115 上传使用 `oss2`，官方消息渠道、Plex、SMB、Rclone、中文元数据处理、管理员 MFA 和容器重启均属于保留能力，不能因体积较大而顺带移除。

开发环境还需要运行官方禁用源码的回归测试。若把全部禁用包从所有入口删除，全量上游测试会在收集阶段失败；若继续让 `requirements.in` 引入这些包，正式镜像又不会真正变小。因此需要使用仓库已有的运行/开发依赖分层，而不是新建长期分叉的锁文件。

## Goals / Non-Goals

**Goals:**

- 固定基础运行依赖禁止集合，并证明解析后的正式环境不安装这些包。
- 解除所有保留启动与业务链对禁止包的顶层或无条件导入。
- 固定 SQLite 和进程内缓存，安全忽略历史 PostgreSQL/Redis 设置且不改写配置。
- 保留网盘、元数据、整理、插件、通知、媒体服务器和管理员认证所需依赖及官方行为。
- 保留上游禁用源码及其开发测试能力，让持续同步仍可发现官方回归。
- 保证插件手动安装可以声明和安装插件自身依赖，核心不预装 P115StrmHelper。
- 用干净运行环境、安全扫描和资源数据证明精简真实发生。

**Non-Goals:**

- 不修改 Dockerfile、entrypoint、容器内更新器、APT 包、Chromium 系统库、FFmpeg/FFprobe 或前端产物。
- 不物理删除 Agent、Workflow、下载器、站点、Redis、PostgreSQL 或浏览器源码目录。
- 不改变插件市场、消息渠道、媒体服务器、管理员认证、文件整理或元数据业务语义。
- 不预装、分叉或修改 P115StrmHelper，不在普通 CI 使用真实 115 凭据或访问真实插件市场。
- 不承诺本阶段达到最终 Docker 镜像体积目标；镜像构建和发布另行审批。

## Decisions

### 1. 使用官方依赖入口分层，不增加 Lite 专属运行清单

`requirements.in` 继续作为唯一正式运行依赖源，`requirements.txt` 继续通过 `-r requirements.in` 委托。禁用源码测试所需包放入 `requirements-dev.in` 的“Lite disabled upstream compatibility tests”分组，并由该文件继续引用运行入口。

拒绝新增 `requirements-lite.in`。平行运行清单会让插件依赖修复、Docker 构建、上游同步和本地诊断产生多个真相来源，长期冲突成本高于短期便利。

### 2. 固定 24 个禁止直接运行依赖

| 类别 | 禁止进入基础运行入口的根依赖 |
|---|---|
| Agent / LLM | `langchain`、`langchain-core`、`langchain-community`、`langchain-anthropic`、`langchain-aws`、`boto3`、`langchain-openai`、`langchain-google-genai`、`langchain-deepseek`、`langgraph`、`anthropic`、`openai`、`google-genai`、`ddgs` |
| PT / 下载器 | `qbittorrent-api`、`transmission-rpc`、`torrentool`、`fast-bencode` |
| 浏览器 | `cloakbrowser`、`PyVirtualDisplay` |
| 外部缓存 / 数据库 | `redis`、`psycopg2-binary`、`asyncpg` |
| Windows 托盘 | `pystray` |

测试必须同时解析规范化包名，防止大小写、连字符/下划线或 extras 绕过检查。开发入口可以包含这些包，但基础运行入口及其解析环境不得安装它们。`playwright` 等只由禁止根引入的传递包应自然从基础闭包消失，不维护易随上游变化的完整传递黑名单。

### 3. 先解除传递导入，再删除依赖

实现顺序固定为失败测试、导入边界调整、SQLite/缓存选择固定、依赖文件删除、干净环境验证。类型注解优先放入 `TYPE_CHECKING`，禁用功能所有者只允许在固定非 Lite 分支内延迟导入；不得用全局异常吞掉真实保留功能错误。

消息普通文本、插件事件和固定命令不得为了类型或 TorrentHelper 导入下载器包。数据库工厂在读取历史配置前先应用 Lite capability，始终选择 SQLite；缓存工厂同理始终选择进程内后端。原始配置值只读保留，便于回退官方版本。

### 4. 保留依赖采用正向能力证明

下列依赖即使体积较大也不在本变更删除范围：U115 使用的 `oss2`，SMB 与 Rclone 支持，元数据和中文识别组件，全部官方消息/通知渠道 SDK，PlexAPI，管理员 OTP/Passkey 认证，以及 `/restart` 使用的 Docker SDK。每类至少有一个保留功能测试或导入契约。

其他官方存储适配器源码继续保留；若某适配器依赖在首次显式使用时缺失，必须给出明确错误，不能影响 U115、Local 或核心启动。

### 5. 插件依赖与基础依赖严格分离

P115StrmHelper 仍由管理员手动安装。插件安装器可以在显式认证请求中安装插件声明的第三方依赖，包含基础镜像没有的 `numpy`；启动阶段不得自动下载插件或补装依赖。插件缺失或依赖安装失败时，核心必须继续运行并显示真实失败原因。

资源报告必须分别记录基础运行环境和安装目标插件后的环境，不能把插件会重新引入的包计入基础镜像永久节省，也不能为了插件便利把其依赖预装回 `requirements.in`。

### 6. 采用双环境验证

开发验证环境安装 `requirements-dev.in`，运行全量上游 pytest、Pylint 和禁用源码兼容测试。正式运行验证环境使用新的临时虚拟环境且只安装 `requirements.in`，在明确断言 24 个禁止发行包不存在后，完成以下离线验证：

- 导入应用生命周期、Scheduler、Command、MessageChain、Monitor、TransferChain、PluginManager、U115/Local 存储和保留 API；
- 使用临时 SQLite 与进程内缓存启动、停止并重复一次；
- 使用 mock 验证元数据识别、文件整理、通知、媒体服务器和插件事件，不访问真实服务；
- 模拟历史 PostgreSQL/Redis/浏览器/下载器配置，确认不导入、连接或改写；
- 模拟插件缺失及插件依赖安装失败，确认核心可用。

两个依赖入口都运行 `safety check`。测量使用同一解释器和脚本记录发行包数量、安装体积、导入耗时、RSS、新模块与线程，Windows 数据只作当前阶段比较，不冒充 Linux Docker 镜像结果。

### 7. 上游同步失败关闭

测试直接解析 `requirements.in` 并匹配固定 24 根集合。上游若重新加入任何禁止根、让保留模块重新无条件导入禁止包，或新增运行依赖与已禁用能力耦合，候选同步必须失败并进入人工分类。源代码目录保持官方结构，依赖调整集中在两个官方文件和少量导入边界，以降低重复合并成本。

## Risks / Trade-offs

- **开发环境掩盖缺失依赖**：开发入口仍安装禁用包。通过独立只装运行入口的临时虚拟环境消除掩盖。
- **插件把依赖重新装回部署环境**：P115StrmHelper 会安装自身依赖。分别测量基础和插件后状态，并保持显式管理员安装。
- **上游新代码恢复顶层导入**：固定禁止根测试、独立进程导入测试和同步检查失败关闭。
- **历史 PostgreSQL 用户误以为仍受支持**：Lite 固定 SQLite，诊断明确报告被忽略的历史设置；不删除或改写原配置，允许回退官方版本。
- **安全扫描受上游既有漏洞影响**：必须区分新增问题和预存基线，但不得无解释地忽略新漏洞或降低策略。

## Migration Plan

1. 备份 `/config` 并记录当前依赖、数据库类型、缓存类型与插件列表；不读取或提交秘密值。
2. 先在开发环境完成失败测试和导入解耦，再修改依赖入口。
3. 创建只安装 `requirements.in` 的临时环境，完成离线启动与保留功能验证。
4. 通过全量测试、Pylint、两个依赖入口的安全扫描和资源复测后才允许提交实现。
5. 后续 Docker 候选镜像阶段使用 `/config` 副本和手动安装 P115StrmHelper 的隔离 Canary；本变更不发布或升级实例。

## Rollback

回退本变更提交即可恢复官方完整运行依赖和原数据库选择代码。由于本变更不迁移、删除或改写数据库与 `/config`，同版本官方代码仍可解释原始 PostgreSQL/Redis/插件配置。临时虚拟环境可直接丢弃，不作为持久数据或发布产物。
