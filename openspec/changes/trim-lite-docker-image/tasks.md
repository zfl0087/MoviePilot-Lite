## 1. 提案、基线与实施批准

- [x] 1.1 只读审计 `.dockerignore`、`docker/Dockerfile`、`docker/entrypoint.sh`、`docker/update.sh`、Doctor、升级 API、CLI 自动更新、现有测试和最新 `upstream/v2`
- [x] 1.2 固定系统包、浏览器、媒体二进制、插件、PT 资源、源码排除和不可原地更新矩阵，并记录本机无 Docker/Bash 的验证限制
- [x] 1.3 创建 proposal、design、spec delta、tasks 和 README，明确不包含前端裁剪、外部 CI、镜像发布、真实 P115 或部署
- [x] 1.4 严格校验 OpenSpec、检查工作区只包含获批文档，并向用户展示最终范围
- [x] 1.5 在创建或修改任何实现/测试文件前停止，取得用户对 `trim-lite-docker-image` 实施的明确批准

## 2. Docker 产物合同与失败测试

- [x] 2.1 在 `tests/test_lite_docker_image_contract.py` 新增 Dockerfile 静态合同，断言不存在 Playwright/Chromium 安装、`ffmpeg` 复制、插件仓库和 PT 资源下载，且明确复制 `ffprobe`
- [x] 2.2 在同一测试建立允许/禁止 APT 直接包集合，解析 `prepare_package` 阶段并拒绝 `locales`、更新/调试/浏览器工具重新进入最终镜像
- [x] 2.3 在同一测试断言最终镜像不复制或调用 `docker/update.sh`、`mp_update.sh`、`scripts/local_setup.py update`，且不使用浮动前端 `latest`
- [x] 2.4 在 `tests/test_lite_docker_image_contract.py` 枚举首批最终镜像源码排除清单，模拟这些路径物理缺失后导入 `app.main`、保留 API、Scheduler、MessageChain、TransferChain 和 PluginManager
- [x] 2.5 运行 `pytest tests/test_lite_docker_image_contract.py -v`，确认新增断言在当前官方 Docker 定义上按预期失败，而不是因真实网络、Docker 缺失或测试夹具错误失败

## 3. Dockerfile 最小产物实现

- [x] 3.1 修改 `docker/Dockerfile` 的构建/运行阶段：构建工具只留在临时阶段，最终 APT 直接包固定为设计允许集合并显式安装 `tzdata`
- [x] 3.2 删除 Playwright/Chromium 系统依赖层，只从 `mwader/static-ffmpeg` 复制 `/ffprobe`，保留可执行权限和现有 PATH 语义
- [x] 3.3 修改 `prepare_code`：只下载 `version.py` 固定的前端发行产物，不下载 `MoviePilot-Plugins`、`user.sites.v2.bin` 或 `sites.*`
- [x] 3.4 保持 `/app/app/plugins` 空目录可写，保留 `uv`、pip 兼容包装、Rclone、Unar、Nginx、SSL、cron、gosu、tini、jemalloc 和健康检查
- [x] 3.5 通过 `.dockerignore` 或单一构建清理步骤排除设计批准的源码整块和本地更新/测试辅助文件；不得在 Git 工作树物理删除上游源码
- [x] 3.6 运行 `pytest tests/test_lite_docker_image_contract.py -v`，确认静态镜像合同转绿

## 4. Entrypoint、Doctor 与核心依赖修复

- [x] 4.1 在 `tests/test_docker_entrypoint_permissions.py` 删除 CloakBrowser HOME 测试并新增普通 HOME、插件目录、PUID/PGID、诊断 keepalive 和端口就绪回归测试
- [x] 4.2 在 `tests/test_doctor.py` 新增正式依赖集合测试：CloakBrowser 缺失不得产生 `dependencies.core_missing`，真实核心包缺失仍须失败
- [x] 4.3 修改 `docker/entrypoint.sh`：删除 `BROWSER_EMULATION`、浏览器安装、`.cloakbrowser` 权限分支、官方更新器和一次性升级标记消费
- [x] 4.4 将 `ensure_backend_runtime_dependencies` 探针收敛到 `requirements.in` 的真实核心包；修复命令继续只读 `/app/requirements.txt`，不得读取开发依赖或安装插件依赖
- [x] 4.5 修改 `app/doctor/checks.py` 的 `CORE_DEPENDENCIES`，与 entrypoint 探针和正式运行依赖合同保持一致
- [ ] 4.6 在 Linux/Bash 环境运行 `pytest tests/test_docker_entrypoint_permissions.py tests/test_doctor.py -v`；当前 Windows 结果只能记录为环境限制，不能替代此门禁

## 5. 升级链路失败关闭与普通重启回归

- [x] 5.1 在 `tests/test_lite_upgrade_policy.py` 新增管理员升级 API 测试，要求 `success=false`、稳定提示且 `SystemHelper.restart`、升级标记和停止事件均未调用/改写
- [x] 5.2 改写 `tests/test_cli_auto_update.py` 为 Lite 合同：`start/restart` 不查询 GitHub、不执行 `scripts/local_setup.py`，历史 `MOVIEPILOT_AUTO_UPDATE` 与一次性标记不能扩大能力
- [x] 5.3 在 `tests/test_lifecycle_shutdown.py` 保留普通 restart 成功/失败及停止状态测试，并明确升级拒绝不会改变运行状态
- [x] 5.4 修改 `app/helper/system.py`，让 Lite `upgrade()` 直接返回失败及固定候选镜像升级说明，不创建、消费或清理官方升级标记
- [x] 5.5 修改 `app/api/endpoints/system.py`，保留管理员认证并调用失败关闭策略；普通 `restart_system()` 不变
- [x] 5.6 修改 `app/cli.py`，移除 `start/restart` 的自动更新调用及无调用方的官方 Release/更新执行逻辑
- [x] 5.7 若 `moviepilot`/`docs/cli.md` 仍向 Lite 用户展示原地更新，按耦合规则改为明确不支持并同步测试；不得顺带重构其他本地 CLI 命令
- [x] 5.8 运行 `pytest tests/test_lite_upgrade_policy.py tests/test_cli_auto_update.py tests/test_lifecycle_shutdown.py -v`，确认升级拒绝和普通重启同时通过

## 6. 保留功能、中文路径与插件手动安装

- [x] 6.1 新增 `tests/test_lite_container_retained_tools.py`，在可控 PATH/mock 中证明 `ffprobe`、Rclone、Unar、Nginx/SSL/cron 和核心诊断调用仍有明确所有者
- [x] 6.2 新增 C.UTF-8 中文、空格和常见标点路径测试，覆盖创建、枚举、FileItem 往返、整理目标和 `ffprobe` 参数，不使用真实媒体或外部服务
- [x] 6.3 扩展插件测试，证明空内建插件目录可启动、管理员手动安装兼容插件仍可使用 `uv`/pip、安装失败不阻止核心
- [x] 6.4 用假的 P115StrmHelper 消费普通 115 分享链接事件，确认字段、渠道权限和结果回传保持官方语义且不触发自动安装
- [x] 6.5 运行 U115/Local、元数据、整理、通知、Emby/Jellyfin/Plex、插件 API/事件和普通重启相关 pytest，保持零真实出站

## 7. Docker 双架构候选验证（需单独批准）

- [ ] 7.1 在创建或触发任何私有候选构建工作流前停止，展示 workflow 范围、GHCR 命名、权限、缓存和秘密边界并取得用户批准
- [ ] 7.2 构建固定提交的 `linux/amd64` 和 `linux/arm64` 临时候选；不使用 DockerHub、`latest`、公开 Release 或正式标签
- [ ] 7.3 检查最终镜像：禁止 APT 包、Chromium/Playwright/CloakBrowser、`ffmpeg`、PT 资源、预装插件、更新器和批准排除源码均不存在；保留工具均可执行
- [ ] 7.4 使用临时 `/config` 和 mock 外部服务连续启动/停止两次，验证管理员登录、U115、整理、通知、媒体服务器、插件手动安装、健康检查、SSL 和普通重启
- [ ] 7.5 在相同设备/官方版本/前端/配置下重复测量镜像体积、冷启动、稳定空闲 RSS/CPU，分别记录空插件与手动安装 P115StrmHelper 后结果
- [ ] 7.6 要求镜像体积至少降低 25%、冷启动至少缩短 20%、空闲 RSS 至少降低 30%、空闲 CPU 长期接近 0；任一平台或指标不满足则停止候选

## 8. 质量、文档与版本控制检查点

- [x] 8.1 运行所有新增/相关 pytest，再运行全量 `pytest`；分开记录 Linux 必需门禁和当前 Windows 环境限制
- [ ] 8.2 对修改 Python 模块运行定向 Pylint，并运行 `pylint app/`；对 shell 文件运行项目采用的静态检查，不把未执行工具写成通过
- [x] 8.3 严格验证 OpenSpec，运行 `git diff --check`、秘密扫描和最终镜像合同检查
- [x] 8.4 更新 `PROJECT_BRIEF.md`、`docs/ARCHITECTURE.md`、`docs/COMPATIBILITY.md`、Docker/CLI 使用说明，记录不可原地更新、保留工具、插件手动安装、迁移与回退
- [x] 8.5 在创建实现提交前停止，展示完整差异、测试、双架构、镜像内容和资源证据并取得用户明确提交批准
- [x] 8.6 获批后创建单一目的实现提交；推送前再次停止并取得批准，只能推送私有 `origin/lite`
- [ ] 8.7 不得向 `upstream` 推送、创建公开 PR、发布镜像、部署 Canary 或升级生产实例；这些动作分别需要后续明确批准
- [ ] 8.8 实现推送后再请求 OpenSpec 归档、归档提交和归档推送批准

## 当前实现验证记录

- Windows 相关保留流程回归：140 项通过，覆盖升级拒绝、普通重启、插件入口、假 P115 消费与回传、U115/Local、元数据、整理、通知及 Emby/Jellyfin/Plex。
- Windows 全量 pytest：1989 项通过、29 项失败、39 项跳过；失败包含默认 GBK 解码、Linux 路径/命令、符号链接权限、Windows 临时文件锁及已禁用官方能力测试，未达到全量绿色门禁。
- 定向 Pylint：4 个修改 Python 模块 `10.00/10`、零消息；全包 Pylint 仅在 Windows 缺少 `fcntl` 的 Agent 终端模块报告既有导入错误。
- 当前主机无 Docker 且 PATH 中无 Bash；entrypoint Linux 权限测试、Shell 静态检查、双架构镜像内容、启动和资源指标均未完成，不能由 Windows 静态测试替代。
