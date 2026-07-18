## 1. 提案、基线与实施批准

- [x] 1.1 只读审计 `requirements.in`、依赖闭包、保留功能导入、Docker 消费入口和最新 `upstream/v2`，确认工作区干净且上游推送禁用
- [x] 1.2 记录当前 Windows 开发环境的 168 包 / 594.06 MiB 基线、24 根候选、114 包 / 313.79 MiB 候选和 280.28 MiB 预计减少值
- [x] 1.3 严格验证 `trim-lite-runtime-dependencies` 的 proposal、design、specs 和 tasks，并确认不越过 Docker、前端、发布或真实 P115 边界
- [x] 1.4 在修改运行代码、依赖文件或创建临时虚拟环境前展示固定删除/保留矩阵、测试计划与已知风险，并取得用户明确实施批准

## 2. 依赖契约与失败测试

- [x] 2.1 新增解析 `requirements.in` 的规范化契约测试，精确拒绝 24 个禁止根依赖及大小写、连字符/下划线和 extras 绕过
- [x] 2.2 新增依赖分层测试，确认 `requirements.txt` 只委托 `requirements.in`，开发入口独立标注禁用源码兼容测试依赖
- [x] 2.3 新增独立进程导入测试，模拟 Agent/LLM、PT/下载器、浏览器、Redis/PostgreSQL 和 pystray 包全部缺失
- [x] 2.4 新增历史 PostgreSQL/Redis/浏览器/下载器配置测试，证明 Lite 仍固定 SQLite/进程内缓存且不导入、连接或改写配置
- [x] 2.5 新增保留依赖契约，覆盖 U115/oss2、Local/SMB/Rclone、元数据、整理、官方通知渠道、媒体服务器、管理员认证和容器重启
- [x] 2.6 新增插件缺失、插件依赖缺失/安装失败和兼容插件消息/命令/任务测试，全程使用 mock 且零真实出站

## 3. 传递导入与运行后端实现

- [x] 3.1 移除 MessageChain、Command、TransferChain 和公共 Chain 类型中的 TorrentHelper、下载器客户端及其他禁止包顶层导入
- [x] 3.2 使用 `TYPE_CHECKING`、协议、最小 resolver 或固定禁用分支处理类型与历史方法，不以宽泛异常隐藏保留功能错误
- [x] 3.3 在数据库选择入口先应用固定 Lite capability，始终选择 SQLite，并对历史 PostgreSQL 设置提供无秘密诊断
- [x] 3.4 确认缓存选择始终使用进程内后端，历史 Redis 设置不能恢复同步/异步 Redis helper、连接池或模块初始化
- [x] 3.5 逐个修复干净运行环境暴露的其他传递导入，保持上游源码目录和公开数据结构不变

## 4. 依赖入口精简

- [x] 4.1 从 `requirements.in` 删除固定 24 个禁止根依赖，不删除任何经正向保留功能证明需要的依赖
- [x] 4.2 在 `requirements-dev.in` 建立清晰的“Lite disabled upstream compatibility tests”分组，保留官方禁用源码测试所需依赖
- [x] 4.3 保持 `requirements.txt` 的运行入口委托和插件依赖安装行为，不生成或提交平台相关锁文件
- [x] 4.4 检查解析后的基础运行依赖闭包不含 24 个禁止发行包及无其他保留根需要的 Playwright 等传递包

## 5. 干净运行环境与保留能力验证

- [x] 5.1 经批准创建临时虚拟环境，只安装 `requirements.in`，记录解释器、平台、安装结果和禁止包缺失证据
- [x] 5.2 在临时 SQLite、临时 `CONFIG_DIR` 和进程内缓存下完成两次启动/停止，验证无 Redis/PostgreSQL/浏览器/下载器连接或线程
- [x] 5.3 离线验证 U115/Local 存储导入、元数据识别、文件整理、插件 API/事件/命令/任务、通知和媒体服务器 mock 流程
- [x] 5.4 验证 P115StrmHelper 未安装时核心正常；用假的兼容插件验证分享链接事件，不下载真实插件或接触真实 115
- [x] 5.5 使用临时 `/config` 验证历史禁用配置不被改写、SQLite 数据可回退同版本官方代码解释

## 6. 质量、安全与资源复测

- [x] 6.1 在开发依赖环境运行所有新增/相关 pytest，随后运行全量 pytest 并与已知 Windows 基线逐项比较
- [x] 6.2 对所有修改 Python 模块运行定向 Pylint，并运行 `pylint app/` 区分新增问题与已知 Windows `fcntl` 基线
- [x] 6.3 对 `requirements.txt` 和 `requirements-dev.in` 分别运行项目规定的 `safety check`，审查新增漏洞且不提交秘密或本地报告
- [x] 6.4 在相同 Windows 解释器下复测发行包数量、安装体积、导入耗时、RSS、新模块和线程，清楚标注非 Docker 数据
- [x] 6.5 严格验证 OpenSpec，运行 `git diff --check`、秘密信息扫描和依赖分层检查

## 7. 文档与下一阶段边界

- [x] 7.1 更新依赖分层、开发环境和兼容文档，记录固定禁止根、SQLite/内存缓存、插件依赖与回退策略
- [x] 7.2 输出基础环境与手动安装 P115StrmHelper 后环境的后续 Canary 测量计划，不在本变更安装真实插件
- [x] 7.3 固化下一阶段 `trim-lite-docker-image` 边界：容器更新器、浏览器系统包、FFmpeg、PT 资源、预置插件和 APT 包另行提案

## 8. 版本控制检查点

- [x] 8.1 在创建运行代码/依赖实现提交前停止，展示差异、测试、安全扫描、资源变化和已知基线，取得用户明确提交批准
- [x] 8.2 获批后创建单一目的实现提交，并在推送前再次停止取得明确批准
- [x] 8.3 获批后仅推送到私有 `origin/lite`；不得推送 `upstream`、创建公开 PR、构建/发布镜像或升级实例
- [ ] 8.4 实现提交推送后再请求 OpenSpec 归档、归档提交和归档推送批准
