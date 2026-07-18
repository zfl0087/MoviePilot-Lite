## 1. 规划、基线与运行代码批准

- [x] 1.1 严格验证 `gate-lite-startup-scheduler` 的 proposal、design、specs 和 tasks，并确认与已归档 Lite 能力、API、认证和模块发现规范一致
- [x] 1.2 在独立临时 `CONFIG_DIR` 记录 `app.scheduler` 与 `app.startup.lifecycle` 的干净导入失败、垫片后耗时、RSS、新模块和线程基线
- [x] 1.3 核对 `lite` 与 `origin/lite` 一致、工作树在本变更前干净、全量 pytest 41 个已知 Windows 失败及 Pylint `fcntl` 基线
- [x] 1.4 在修改运行代码前展示启动 owner、系统任务、内建命令、插件启动、消息事件和 Monitor/Transfer 固定矩阵，并取得用户明确批准

## 2. 导入与精确集合失败测试

- [x] 2.1 新增 pytest-native 独立进程导入测试，在不提供 `app.helper.sites`、Agent、Workflow、Redis、Display 和下载器依赖时导入 lifecycle、Scheduler、Command、MessageChain、Monitor、TransferChain
- [x] 2.2 断言正常导入和空配置启动后 `sys.modules` 不含 Agent/LLM/MCP/Skills、Workflow、Subscribe/Search/Site/Download/Recommend、Redis、Display 及动态站点资源禁止前缀
- [x] 2.3 新增生命周期 owner 参数化测试，覆盖正常模式、安全模式、DoH 条件、初始化失败、实际 owner 逆序关闭和每个关闭阶段异常隔离
- [x] 2.4 新增 Scheduler 精确任务矩阵测试，覆盖空配置、媒体服务器/清理/GC 条件、全部历史禁用配置、未知任务注入和配置重载
- [x] 2.5 新增 Command 精确内建矩阵与插件命令测试，证明构造/重载不实例化 Scheduler 或禁用 Chain
- [x] 2.6 新增 MessageChain 插件事件测试，覆盖 115 普通链接 `UserMessage`、插件输入/取消/超时 `MessageAction`、固定命令及 AI/Voice/Skills 禁用路径
- [x] 2.7 新增 Monitor/Transfer 导入和行为测试，覆盖无目录零后台资源、Local 文件事件、U115 快照、配置移除停止资源及禁用依赖缺失
- [x] 2.8 新增插件启动测试，证明 P115StrmHelper 缺失时不访问市场、不自动下载/装依赖，本地兼容插件及显式管理员安装仍工作

## 3. 生命周期与启动所有者实现

- [x] 3.1 将 lifecycle 模块顶层收敛到轻量核心依赖，按固定 capability 矩阵延迟导入 Router、Module、Plugin、Scheduler、Monitor、Command 和条件 DoH owner
- [x] 3.2 从 modules initializer 的导入与启动/停止路径移除 Agent、Display、Redis、订阅/插件统计、GitHub 用户预取和使用统计副作用
- [x] 3.3 保留 ModuleManager、EventManager、Thread/Message/Database/HTTP 清理及现有安全模式，记录实际启动 owner 并保证关闭对称
- [x] 3.4 将启动完成任务收敛为本地系统状态收尾，不调用插件自动同步、缺失依赖安装或非必要外联

## 4. Lite Scheduler 实现

- [x] 4.1 把 Scheduler 顶层 Subscribe、Recommend、Transfer、Workflow 等禁用 owner 导入改为固定任务选择后的最小延迟工厂
- [x] 4.2 实现保留系统任务矩阵：`mediaserver_sync`、`scheduler_job`、`clear_cache`、`data_cleanup`、`full_gc` 及兼容插件任务
- [x] 4.3 删除禁用系统任务注册、Workflow 事件任务和 Agent heartbeat，收窄 `CONFIG_WATCH` 并阻止历史配置恢复
- [x] 4.4 让 list/progress/start 对实际集合工作，未知或禁用任务明确失败且不临时导入 owner
- [x] 4.5 验证 stop/init 和插件重载串行、旧 Scheduler 释放、插件任务只注册一次且不会恢复周期市场刷新

## 5. Lite Command 与 MessageChain 实现

- [x] 5.1 将 Command 内建集合固定为 `/mediaserver_sync`、`/clear_cache`、`/restart`、`/version`，保留兼容插件命令并删除其他预设
- [x] 5.2 移除 Command 构造期 Scheduler、MessageChain 和禁用业务 Chain 实例，使用固定 resolver 在执行保留命令时延迟获取所有者
- [x] 5.3 收敛 MessageChain 顶层依赖和普通消息路由，保留渠道字段、插件输入/回调、固定命令、通知和 `UserMessage`/`MessageAction`
- [x] 5.4 固定拒绝 Agent/LLM/Voice、Site/Search、Subscribe、Download、Skills、Workflow 和传统媒体搜索回退，历史会话不能恢复禁用路径
- [x] 5.5 使用假的 P115 插件消费者验证分享链接事件、回复目标字段、插件命令与定时服务完整，插件缺失时不自动安装或伪造成功

## 6. Monitor 与 Transfer 整理链实现

- [x] 6.1 移除 TransferChain 顶层 Agent 与 Subscribe 依赖，逐个审计相关方法并在固定禁用能力下延迟导入或明确失败关闭
- [x] 6.2 保持 Monitor 使用现有 TransferChain，不复制整理实现；验证 Local/U115 元数据识别、命名、文件操作和历史记录语义
- [x] 6.3 确保无有效 Directories 时不创建 watcher/Scheduler/快照，配置移除或 stop 时关闭并 join 所有资源
- [x] 6.4 验证未知 storage、历史下载器目录和禁用业务字段不能触发网盘、下载器或动态模块导入

## 7. 插件、API、文档与兼容

- [x] 7.1 保留本地兼容插件的初始化、API、事件、命令和服务注册；阻止不兼容插件借声明恢复禁用核心能力
- [x] 7.2 回归插件显式安装、升级和依赖操作的管理员认证，确认关闭启动自动同步不改变手动入口的成功/失败语义
- [x] 7.3 扩展 Scheduler 列表/进度/手动运行 API 测试，验证 Token 权限、响应字段、实际 Lite 集合和禁用 ID 失败语义
- [x] 7.4 更新 `PROJECT_BRIEF.md`、`docs/ARCHITECTURE.md`、`docs/COMPATIBILITY.md` 和 `docs/mcp-api.md`，记录启动 owner、任务、命令、插件手动安装及消息事件矩阵
- [x] 7.5 确认本变更不修改前端仓库、数据库 Schema、依赖清单或 Docker；输出下一阶段安全依赖删除候选和仍需前端裁剪的接口证据

## 8. 质量、集成与资源验证

- [x] 8.1 运行 lifecycle、Scheduler、Command、MessageChain、Monitor、TransferChain、PluginManager 和 Scheduler API 定向 pytest，测试全程零真实出站
- [x] 8.2 对所有修改 Python 模块运行定向 Pylint，确认无新增错误且公开接口中文 docstring 完整
- [x] 8.3 因修改启动、共享 Chain 和长期后台所有者，运行全量 pytest 并逐项比较 41 个已知 Windows 基线失败
- [x] 8.4 运行 `pylint app/`，区分本变更新问题与已知 Windows `fcntl` 基线
- [x] 8.5 在相同解释器、依赖和空条件配置下复测 lifecycle/Scheduler 导入耗时、RSS、新模块和线程，并启动/停止两次实际 Lite owner 集合检查泄漏
- [x] 8.6 使用官方 `/config` 副本离线验证历史 Agent、Workflow、Subscribe、Download、Redis、统计、命令和目录配置不被改写，不连接外部服务
- [x] 8.7 严格验证完成后的 OpenSpec，运行 `git diff --check` 和秘密信息检查；本变更不改依赖，因此不运行依赖安全扫描

## 9. 版本控制检查点

- [x] 9.1 在创建运行代码提交前停止，展示固定矩阵、实现差异、测试结果、资源变化、已知基线和后续依赖/Docker/前端边界，取得用户明确批准
- [x] 9.2 获批后创建单一目的实现提交，并在推送前再次停止取得明确批准
- [x] 9.3 获批后仅推送到私有 `origin/lite`；不得推送 `upstream`、创建公开 PR、发布版本、构建公开镜像或升级生产实例
- [x] 9.4 实现提交推送后归档 OpenSpec；归档提交和推送分别再次遵守用户批准检查点
