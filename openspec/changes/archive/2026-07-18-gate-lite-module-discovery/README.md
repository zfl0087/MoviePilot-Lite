# gate-lite-module-discovery

在导入前裁剪 Lite 顶层模块与存储适配器，并保持配置热更新和首次网盘授权。

## 资源验证记录

在同一 Windows 主机、同一虚拟环境和空条件配置的独立 Python 进程中，旧版 `ModuleHelper.load("app.modules")` 全扫描耗时 4.8441 秒、RSS 增量 202,493,952 字节，导入 30 个顶层包和 106 个 `app.modules.*` 模块；接入导入前门控后，同口径扫描耗时 0.6178 秒、RSS 增量 33,153,024 字节，只导入 6 个顶层包和 45 个 `app.modules.*` 模块，活动线程均无增量。发现阶段耗时降低约 87.2%，RSS 增量降低约 83.6%，顶层包数量降低 80%。

通过实际 `ModuleManager` 冷启动复测，耗时 0.7526 秒、RSS 增量 34,816,000 字节，仅发现 Bangumi、Douban、Fanart、FileManager、TheMovieDb、TheTvDb 六个核心模块。以上数据只验证本次发现层门控方向，不替代后续完整 Docker 候选的最终资源验收。
