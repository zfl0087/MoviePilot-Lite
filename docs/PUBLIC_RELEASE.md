# MoviePilot Lite 公开发布与安装

## 1. 发布性质

MoviePilot Lite 是非官方社区构建，不代表 MoviePilot 官方，也不由官方团队提供 Lite 支持。当前默认镜像已完成核心 115 工作流验收，适合个人或家庭自托管环境使用；升级前仍应备份 `/config`，并保留固定版本用于回退。

## 2. 固定版本

```text
image=docker.io/zfl0087/moviepilot-lite:v2.14.5-lite.1-rc.8
digest=sha256:f7acb73bd2abf510bac42a09838d3f91b558e4d11ab8dab4d438610b24b88d34
backend=81509ecc9e9ab09375f9b7745409a23585a5fe09
frontend=4aca2de078cae65b1e83af86a7b4abee04987d03
official_backend=8b5524a321c940f337873cefa54ba6a58462f9a4
official_frontend=435e9ecfdd4febf791fd581b3be9233816cebf7f
platforms=linux/amd64,linux/arm64
```

对应源码：

- [MoviePilot-Lite 后端](https://github.com/zfl0087/MoviePilot-Lite)
- [MoviePilot-Lite-Frontend 前端](https://github.com/zfl0087/MoviePilot-Lite-Frontend)
- 机器可读记录：`releases/v2.14.5-lite.1-rc.8.json`

`docker.io/zfl0087/moviepilot-lite:latest` 与以上固定版本指向同一摘要，可作为默认安装镜像。版本标签和摘要必须同时保存；回退和故障复现不得依赖 `latest`。

## 3. 安装前准备

1. 备份现有 `/config`，至少保留 `user.db`、配置文件和插件数据的可恢复副本。
2. 保留当前可正常运行镜像的完整标签和摘要，用于回退。
3. 新安装优先使用独立容器名称、端口和 `/config` 目录；不要直接覆盖原版 MoviePilot。
4. 管理端口只允许局域网或受控反向代理访问，不得直接暴露到公网。
5. 不把 115 Token、Cookie、消息渠道 Token、管理员密码或 `API_TOKEN` 写进 Compose 文件、日志或截图。

## 4. 拉取并核对镜像

按摘要拉取：

```bash
docker pull docker.io/zfl0087/moviepilot-lite:v2.14.5-lite.1-rc.8@sha256:f7acb73bd2abf510bac42a09838d3f91b558e4d11ab8dab4d438610b24b88d34
```

核对本地摘要：

```bash
docker image inspect docker.io/zfl0087/moviepilot-lite:v2.14.5-lite.1-rc.8 --format '{{json .RepoDigests}}'
```

输出应包含本页记录的 `sha256:f7ac...8d34` 摘要。

## 5. Compose 示例

将 `192.168.1.10`、`/你的路径/moviepilot-lite-config`、`PUID` 和 `PGID` 改为 NAS 的实际局域网地址、独立目录和非特权用户：

```yaml
services:
  moviepilot-lite:
    image: docker.io/zfl0087/moviepilot-lite:latest
    container_name: moviepilot-lite
    restart: unless-stopped
    ports:
      - "192.168.1.10:3002:3000"
    environment:
      TZ: Asia/Shanghai
      PUID: "1000"
      PGID: "1000"
      UMASK: "022"
    volumes:
      - /你的路径/moviepilot-lite-config:/config
      - /你的媒体路径:/media
```

`192.168.1.10:3002` 只是局域网示例绑定。`/你的媒体路径:/media` 使 MoviePilot Lite 和插件以统一的容器内路径访问媒体文件；插件配置中应使用 `/media/...`。若已有 MoviePilot 使用相同名称、端口或配置目录，必须改为不同值；不要把绑定地址改为公网接口。

## 6. 115网盘STRM助手

P115StrmHelper 不包含在核心镜像中，必须在插件市场手动安装。默认镜像记录已验证的 `P115StrmHelper 2.8.62`，不要自动追随未验证的新版本。

已验证：

- 插件手动安装、依赖安装和加载；
- 插件配置表单与已安装插件侧栏导航；
- 真实 115 分享链接转存；
- 完整 STRM 生成及文件可读；
- 消息渠道接收链接后的结果回传；
- Emby、Jellyfin、Plex 媒体库刷新。

## 7. 升级与回退

升级时先停止旧容器，保留旧容器定义和镜像，使用 `/config` 的备份副本启动新版本。确认健康检查、管理员登录、插件加载及关键数据正常后，再决定是否替换原实例。

出现异常时：

1. 停止新容器并保存不含敏感值的必要日志。
2. 恢复升级前的 `/config` 副本。
3. 使用已记录的旧镜像标签和摘要重建旧容器。
4. 确认数据库、插件和媒体路径恢复后再删除失败实例。

不要用 `latest` 作为回退依据，也不要在未备份时让新旧版本轮流写入同一个 `/config`。

## 8. 许可证

MoviePilot Lite 按 GNU GPLv3 提供。分发镜像或二进制时，必须同时提供对应完整源码、许可证、版权与修改说明。维护者目前不销售支持、不运营 SaaS；该运营选择不限制接收者依据 GPLv3 使用、修改、再分发或收费分发的权利。
