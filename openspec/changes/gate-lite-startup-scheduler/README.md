# gate-lite-startup-scheduler

在应用生命周期、消息命令和 Scheduler 导入之前执行固定 Lite 门控，保留网盘整理、插件、通知和媒体服务器所需运行链路。

## 审计基线

在独立临时 `CONFIG_DIR` 和未提供动态站点资源的干净进程中，单独导入 `app.scheduler` 会沿 `SubscribeChain → SearchChain` 访问缺失的 `app.helper.sites` 并直接失败。加入仅供审计的站点垫片后，导入 `app.scheduler` 耗时 2.6324 秒、RSS 增量 150,302,720 字节、新增 1,887 个模块并创建一个批处理写入线程；新增模块包含 Agent/LLM/MCP/Skills、站点、搜索、订阅、下载、推荐、工作流及 Redis 链路。

同口径导入 `app.startup.lifecycle` 耗时 2.5716 秒、RSS 增量 153,280,512 字节、新增 1,990 个模块并创建一个批处理写入线程；除上述禁用链路外，还会通过命令和模块初始化器导入虚拟显示、完整消息动作及其他非目标依赖。以上数据是实施前导入基线，不代表完整应用冷启动指标。
