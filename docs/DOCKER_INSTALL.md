# MoviePilot Lite Docker 安装教程

`latest` 指向已验收的最新 MoviePilot Lite 镜像。建议新建独立容器测试，不要覆盖原版 MoviePilot，也不要让两个容器共用同一个 `/config`。

## 一、安装前准备

1. 在 NAS 上新建配置目录，例如 `/volume1/docker/moviepilot-lite/config`。
2. 如果已有 MoviePilot，先完整备份原来的 `/config`。
3. 确认准备使用的宿主机端口未被占用，本文使用 `3002`。

默认镜像：

```text
docker.io/zfl0087/moviepilot-lite:latest
```

当前已验收版本为 `v2.14.5-lite.1-rc.8`。回退或复现问题时，请改用固定版本标签，不要使用 `latest`。

## 二、NAS 图形界面安装

在飞牛、群晖或其他 NAS 的 Docker/容器管理器中：

1. 搜索 `zfl0087/moviepilot-lite`，拉取标签 `latest`。
2. 使用该镜像创建容器，并填写以下参数。

| 项目 | 设置值 |
|---|---|
| 容器名称 | `moviepilot-lite` |
| 自动重启 | 开启 |
| 宿主机端口 | `3002` |
| 容器端口 | `3000` |
| NAS 配置目录 | `/volume1/docker/moviepilot-lite/config`（按实际路径修改） |
| 容器目录 | `/config` |

添加环境变量：

| 变量 | 示例值 | 说明 |
|---|---|---|
| `TZ` | `Asia/Shanghai` | 时区 |
| `PUID` | `1000` | NAS 用户 UID |
| `PGID` | `1000` | NAS 用户 GID |
| `UMASK` | `022` | 文件权限掩码 |
| `SUPERUSER` | `admin` | 初始管理员用户名 |
| `SUPERUSER_PASSWORD` | 自己设置的强密码 | 只在全新 `/config` 首次初始化时生效 |

不知道 UID/GID 时，可通过 NAS SSH 查询：

```bash
id 你的NAS用户名
```

创建并启动容器，等待状态变为“健康”。

## 三、Docker Compose 安装

也可以创建 `compose.yaml`：

```yaml
services:
  moviepilot-lite:
    image: docker.io/zfl0087/moviepilot-lite:latest
    container_name: moviepilot-lite
    restart: unless-stopped
    ports:
      - "3002:3000"
    environment:
      TZ: Asia/Shanghai
      PUID: "1000"
      PGID: "1000"
      UMASK: "022"
      SUPERUSER: admin
      SUPERUSER_PASSWORD: "请改成自己的强密码"
    volumes:
      - /volume1/docker/moviepilot-lite/config:/config
```

修改配置目录、UID、GID 和密码后执行：

```bash
docker compose up -d
docker compose ps
```

为了避免密码进入命令历史或公开仓库，不要分享自己的 Compose 文件；安装完成后应在系统设置中修改密码。

## 四、打开和登录

浏览器访问：

```text
http://NAS局域网IP:3002
```

使用刚才设置的 `SUPERUSER` 和 `SUPERUSER_PASSWORD` 登录。如果挂载的是已有 `/config`，请继续使用原来的账号密码。

无法访问时查看日志：

```bash
docker logs --tail 200 moviepilot-lite
```

不要把管理端口直接映射到公网。

## 五、可选代理

需要通过 Mihomo 等代理访问外网时，增加环境变量：

```text
PROXY_HOST=http://NAS局域网IP:7890
```

容器内的 `127.0.0.1` 指向容器自身，因此不要填写 `http://127.0.0.1:7890`。修改环境变量后重建或重启容器。

## 六、安装115网盘STRM助手

1. 登录 MoviePilot Lite。
2. 打开“插件市场”。
3. 手动安装“115网盘STRM助手” `2.8.62`。
4. 打开插件配置，通过二维码登录115，设置独立的分享转存目录并保存。

该插件不是镜像内置组件。首次测试建议使用小文件和独立目录，并暂时关闭清理回收站、清理最近接收等删除功能。

## 七、升级

升级前先备份 `/config`，并记录当前固定版本标签和摘要以便回退。使用 `latest` 安装的 Compose 可执行 `docker compose pull` 后再执行 `docker compose up -d`。不要删除旧镜像和备份，直到新版本验证正常。

更完整的镜像校验、升级和回退说明见 [公开发布与安装](PUBLIC_RELEASE.md)。
