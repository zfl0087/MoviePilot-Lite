## ADDED Requirements

### Requirement: Lite 前端必须消费后端唯一能力清单
Lite 前端构建 MUST 使用后端 `get_lite_capability_manifest()` 的序列化结果作为唯一能力来源，至少校验 `profile`、`version`、`enabled` 和 `disabled` 字段。前端源码 MUST NOT 再维护一份独立的 Lite 启用/移除列表；manifest 缺失、格式错误、未知能力或版本不匹配 MUST 失败关闭并提供明确诊断。

#### Scenario: 配对 manifest 生成构建输入
- **GIVEN** 后端生成 profile 为 `lite`、version 为 2 且 enabled/disabled 集合与 `Capability` 完整一致
- **WHEN** 前端执行生产构建
- **THEN** 构建成功，并将同一 profile/version 固定写入可验证的构建元数据

#### Scenario: manifest 缺失或不完整
- **GIVEN** 构建输入没有 manifest，或缺少 `profile`、`version`、`enabled`、`disabled` 任一字段
- **WHEN** 执行生产构建
- **THEN** 构建失败，不回退到官方完整页面集合，也不使用前端硬编码默认清单

#### Scenario: 运行时版本不匹配
- **GIVEN** 前端构建 profile/version 与 `/api/v1/system/global` 返回的 Lite profile/version 不一致
- **WHEN** 登录前初始化完成
- **THEN** 显示明确的前后端版本不匹配错误，不加载业务路由或插件页面，且不尝试启用禁用能力

### Requirement: 路由和菜单必须在注册前按能力裁剪
Lite 前端 MUST 在路由、主菜单、应用中心、全局搜索、首页重定向和权限判断之前筛选 capability。禁用页面 MUST NOT 注册、动态导入或通过历史 URL 进入；未知路由应返回明确的 404/能力不可用状态，而不是把能力缺失伪装成普通权限拒绝。

#### Scenario: 保留页面集合保持可用
- **GIVEN** 配对 manifest 启用 system、admin-auth、cloud-storage、metadata、media-organization、plugins、messaging、notifications 和 media-server
- **WHEN** 构建路由和主导航
- **THEN** 登录、网盘/文件管理、识别整理、整理历史、插件、消息通知、媒体服务器和必要设置入口存在，官方相对路径和认证语义保持

#### Scenario: 禁用入口不注册
- **GIVEN** manifest 禁用 pt-sites、pt-site-auth、downloaders、subscriptions、torrent-search、content-discovery、agent、llm、mcp、skills、workflow、auxiliary-auth、multi-user、sso、arr-compat 和 cookiecloud
- **WHEN** 构建并加载路由、菜单、应用中心和全局搜索
- **THEN** PT、认证、下载、订阅、发现、Agent、Workflow、辅助认证和兼容接口入口均不存在，直接访问其历史路径不会导入页面组件

#### Scenario: 首页和无效路径安全回退
- **GIVEN** 已登录管理员或普通用户访问根路径、被移除路径或旧收藏链接
- **WHEN** 路由守卫解析目标
- **THEN** 根路径只重定向到已启用页面，被移除路径进入明确 404/能力不可用状态，不循环跳转或调用禁用 API

### Requirement: PWA 和 Service Worker 不得缓存禁用能力
Lite 前端 MUST 从 PWA manifest、快捷方式、Service Worker 预缓存和离线导航回退中排除禁用页面、入口和专属静态资源；保留页面在刷新、离线壳和更新提示中的官方行为保持。

#### Scenario: PWA 清单只包含保留入口
- **WHEN** 生成 PWA manifest 和快捷方式
- **THEN** 不包含 PT、下载器、订阅、搜索发现、Agent、Workflow、辅助认证或多用户页面链接

#### Scenario: 预缓存清单排除禁用 chunk
- **WHEN** 构建 Service Worker 和最终静态资源清单
- **THEN** 禁用页面的 chunk、专属图标和入口不在预缓存集合，保留插件联邦远程地址不被复制为核心资源

### Requirement: 禁用页面及专属依赖不得进入最终 bundle
Lite 生产构建 MUST 证明禁用页面、其专属动态 chunk 以及仅服务这些页面的生产依赖不进入最终 bundle。共享组件、构建工具、插件模块联邦运行时和保留页面所需依赖 MUST NOT 因体积优化误删。

#### Scenario: 构建产物内容合同
- **WHEN** 在干净依赖环境执行生产构建并检查输出目录、chunk 名称和模块清单
- **THEN** 禁用页面路径和批准排除依赖不存在，保留文件管理、整理、插件、通知、媒体服务器和登录流程的资源存在

#### Scenario: 不确定依赖保持并记录
- **GIVEN** 一个依赖同时被禁用页面和保留页面、测试、构建工具或插件联邦引用
- **WHEN** 生成依赖裁剪清单
- **THEN** 该依赖保持可用，并在审计记录中说明原因，不得按包大小猜测删除

### Requirement: 插件远程页面必须保持手动兼容边界
Lite 前端 MUST 保留官方模块联邦、插件侧栏、动态路由和错误展示机制。P115StrmHelper 及其他插件页面 MUST NOT 编译进核心 bundle；插件未安装、未启用或未通过兼容检查时，核心仍 MUST 启动并显示具体原因。

#### Scenario: 手动安装 P115StrmHelper 后加载页面
- **GIVEN** 后端确认 P115StrmHelper 已手动安装、启用并通过 Lite 兼容检查
- **WHEN** 用户打开对应插件导航
- **THEN** 前端通过既有远程组件机制加载页面，核心构建不包含插件源码副本

#### Scenario: 插件缺失不阻止核心
- **GIVEN** P115StrmHelper 未安装或依赖失败
- **WHEN** Lite 前端启动并刷新插件导航
- **THEN** 登录、网盘、整理、通知和媒体服务器页面仍可用，插件入口显示明确手动安装/兼容原因，不出现白屏

### Requirement: 前后端权限和安全边界必须保持官方语义
前端 capability 筛选 MUST NOT 绕过现有管理员、白名单、用户绑定或消息权限判断，也 MUST NOT 通过 manifest 重新开启后端禁用 API。所有用户可见错误必须经现有多语言机制提供，不得把 Token、Cookie、密码或真实配置写入构建产物。

#### Scenario: 前端隐藏不替代后端拒绝
- **GIVEN** 客户端构造指向已禁用 API 的请求
- **WHEN** Lite 后端处理该请求
- **THEN** 后端仍按既有能力门控返回拒绝/不存在结果，前端不提供绕过路径

#### Scenario: 权限语义保持
- **GIVEN** 用户没有某个保留页面的官方权限，或消息渠道不满足官方白名单
- **WHEN** 前端渲染入口或执行动作
- **THEN** 继续使用官方权限判断和错误语义，不因 Lite 单管理员目标而扩大权限

### Requirement: 前端候选必须通过类型、测试和产物门禁
Lite 前端变更 MUST 通过 TypeScript 类型检查、pytest 之外的仓库现有 `yarn test:run` 和生产 `yarn build`，并 MUST 记录配对后端提交、前端提交、manifest version、构建产物检查和已知限制。未启用页面注册/导入、PWA 资源和插件远程边界 MUST 有自动化覆盖。

#### Scenario: 生产构建和路由测试
- **WHEN** 在锁定 Yarn 1 依赖的干净环境运行 `yarn typecheck`、`yarn test:run` 和 `yarn build`
- **THEN** 三项命令成功，路由矩阵、版本配对、禁用 chunk 和保留插件入口测试全部通过

#### Scenario: 构建失败停止候选
- **GIVEN** 任一类型、测试、产物合同或版本配对检查失败
- **WHEN** 生成 Lite 前端候选
- **THEN** 不上传、不让 Docker 消费该产物、不进入双架构镜像或 Canary 流程
