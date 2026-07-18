## Why

Lite 的 API 已在导入前门控，但 `ModuleManager` 仍扫描并导入 `app.modules` 下的全部包，`FileManagerModule` 也会导入全部存储适配器；因此未配置的 PT、下载器、Redis、PostgreSQL、消息渠道、媒体服务器及网盘依赖仍进入冷启动和内存。现在需要把固定能力配置落实到模块发现阶段，才能形成真正的运行时裁剪，并为后续依赖和镜像删除提供可验证边界。

## What Changes

- 为通用模块加载器增加真正发生在 `import_module()` 之前的包名过滤，不再把“导入后检查类”当作预过滤。
- 为 `app.modules` 建立固定、可审计的 Lite 包分类：元数据与文件整理模块保留；消息渠道和 Emby/Jellyfin/Plex 仅在存在启用配置时加载；PT 索引、下载器、Redis、PostgreSQL、非目标媒体服务器及其他禁用包在导入前拒绝；上游新增且未分类的包默认拒绝。
- 在文件整理模块内部对存储适配器执行第二层导入前过滤：本地文件系统作为必要基础适配器保留，115 及其他官方远端存储仅在已配置时加载；管理员首次配置或授权某个固定支持的存储时，只按明确类型延迟加载该适配器。
- 由模块管理器统一处理 Notifications、MediaServers、Storages 配置变化，停止旧实例后按最新配置重建模块集合，避免管理器与单个服务模块重复重载；运行期间停用的适配器停止服务，Python 已导入代码是否从解释器缓存卸载不作为承诺。
- 保留 TMDB、豆瓣、Bangumi、TVDB、Fanart、文件整理、官方消息权限逻辑、插件框架和 Emby/Jellyfin/Plex 既有业务语义；115 OAuth/API 与 P115StrmHelper 手动安装策略不变。
- 新增完全离线的 pytest 契约，证明禁用、未配置和未知包在正常启动时未导入，已配置的 115、消息和媒体服务器可加载，配置热更新不会重复初始化或遗留活动实例。
- **BREAKING**：`/system/modulelist` 等基于已发现模块生成的结果不再列出 PT、下载器、Redis、PostgreSQL、非目标媒体服务器或其他 Lite 禁用模块；历史配置不能恢复这些模块。
- 本变更不物理删除模块源码或 Python 依赖，不裁剪消息命令、剩余后台任务、插件兼容判断、前端页面或 Docker 层，也不宣称已经达到最终资源指标。

## Capabilities

### New Capabilities

- `lite-module-discovery-gating`: 定义 Lite 顶层模块和存储适配器在导入前按固定范围及实际配置门控、配置变更重载和未知包默认拒绝的契约。

### Modified Capabilities

无。

## Impact

- 后端核心：预计修改 `app/helper/module.py`、`app/core/module.py`、`app/modules/__init__.py` 和 `app/modules/filemanager/__init__.py`；通用 Helper 只提供包名预过滤机制，Lite 产品策略由 ModuleManager 和 FileManager 所有。
- API：不新增或删除路由，也不改变认证依赖；已有模块列表和模块测试接口只反映实际可发现的 Lite 模块，需要同步说明其响应集合收窄。
- 存储：Local 保持基础可用；U115、Alipan、Alist、Rclone、SMB 源码保留并按配置延迟加载。首次授权必须允许通过固定类型的管理员请求只加载目标适配器，不得扫描其他适配器。
- 消息与媒体服务器：所有官方消息渠道源码保留并按启用配置加载；核心媒体服务器只允许 Emby、Jellyfin、Plex，TriMeMedia、UGREEN、ZSpace 不进入 Lite 运行时。
- 插件与前端：插件加载机制和 P115StrmHelper 手动安装方式不变；前端仓库不在本变更修改，但后续配对前端不得依赖禁用模块仍出现在模块列表中。
- 依赖与 Docker：不修改依赖清单或镜像；本变更先用导入证据证明哪些依赖可安全移除，实际删除在后续独立变更完成。
- 配置与数据库：读取既有 SQLite `Notifications`、`MediaServers`、`Storages`；不新增数据库迁移、不删除历史 Downloaders 或其他禁用配置，方便回退官方版本。
- 资源占用：预期降低冷启动导入、空闲内存和未配置服务线程，但只记录可重复的前后基线，不把单次测量作为本变更完成后的最终产品指标。
- 安全与验证：未知模块默认拒绝；配置值只能选择固定允许的包，不能形成任意 Python 导入路径。普通测试不访问真实 115、元数据、消息或媒体服务器。
- 上游同步：保留上游目录和模块源码，将差异集中在加载器扩展及两个组合根；上游新增模块必须先分类和测试，不能因目录扫描自动进入 Lite。
