# FastAPI 生产热更新方案：gunicorn + UvicornWorker 与容器化滚动发布

> 本文是 `fastapi-init-skill` 生成项目的生产部署参考。脚手架默认已落地方案一（gunicorn master-worker + HUP 热更新），方案二（容器化滚动发布）为进阶路线。

---

## 一、背景：为什么 Python 需要"热更新方案"

PHP（php-fpm 模式）是 share-nothing 架构：每个请求重新加载代码文件，覆盖文件即生效。FastAPI（及整个 Python Web 生态）是**常驻进程模型**——代码在启动时一次性 import 进内存，之后不再读磁盘。因此：

- 改代码后必须让进程重新 import（重启进程或热替换）；
- 生产环境直接重启会造成请求中断，所以需要"优雅换代"的机制。

两类主流方案对比：

| | 方案一：gunicorn + UvicornWorker | 方案二：容器化滚动发布 |
|---|---|---|
| 换代单位 | 进程（worker） | 容器（整机） |
| 是否需要额外设施 | 不需要，一个 master 自己搞定 | 需要健康检查 + 流量切换（LB / 编排器） |
| 适用规模 | 单机 / 少量机器 | 多实例、集群 |
| 脚手架支持 | ✅ 默认内置 | Dockerfile 已就绪，编排自行接入 |

---

## 二、方案一：gunicorn + UvicornWorker（脚手架默认）

### 2.1 架构：master / worker

gunicorn 是**进程管理器**，自己不处理请求：

```
gunicorn (master, 只管人不干活)
 ├── worker-1: uvicorn + FastAPI   ← 处理请求
 ├── worker-2: uvicorn + FastAPI   ← 处理请求
 └── ...
```

`UvicornWorker` 是适配器，让 gunicorn 的 worker 内部跑 uvicorn（ASGI）。

为什么不用 `uvicorn --workers N` 直接上生产？功能上可以，但 uvicorn 自带的进程管理很弱——没有成熟的信号体系，做不了优雅换代码。gunicorn 的价值全在 master 那一层：**改代码、调 worker 数、换配置，都是给 master 发一个信号的事，全程不断服务**。

### 2.2 安装与配置

```bash
pip install gunicorn uvicorn-worker
```

> 注：worker 适配器官方已拆到独立的 `uvicorn-worker` 包（导入名 `uvicorn_worker.UvicornWorker`）；旧文章里的 `uvicorn.workers.UvicornWorker` 是老写法。

脚手架生成的 `gunicorn.conf.py`（逐项解释）：

```python
# 端口与 worker 数来自环境变量，与 restart.sh 的约定保持一致
bind = "0.0.0.0:" + os.getenv("APP_PORT", "8080")
workers = int(os.getenv("APP_WORKERS", "2"))
worker_class = "uvicorn_worker.UvicornWorker"

# master 进程 PID 写入 app.pid，restart.sh 的热更新判断与 kill -HUP 依赖它
pidfile = "app.pid"

# ⚠️ 保持 False：HUP 热更新依赖 worker 重新 import 磁盘上的新代码；
# 开启 True 会导致 HUP 出来的新 worker 仍跑 master 内存中的旧代码
preload_app = False

graceful_timeout = 30   # 优雅退出最长等待（秒），超时强杀
timeout = 60            # worker 无响应判定（秒），超时被 master 自动拉起
keepalive = 5           # keepalive 长连接保持（秒）
```

启动命令（脚手架的 `./restart.sh prod` 内部就是这条）：

```bash
APP_PORT=8080 APP_WORKERS=2 nohup gunicorn app.main:app -c gunicorn.conf.py > logs/app.log 2>&1 &
```

### 2.3 热更新实操：`kill -HUP`

```bash
# 1. 拉取新代码
git pull

# 2. 给 master 发 HUP 信号（脚手架：直接再执行一次 ./restart.sh prod，效果相同）
kill -HUP $(cat app.pid)
```

master 内部依次发生：

1. 重读 `gunicorn.conf.py`；
2. fork 出新 worker——新 worker 从零启动，重新 import，**加载的就是磁盘上的新代码**；
3. 旧 worker 停止接新请求，把手头正在处理的请求做完（最长等 `graceful_timeout` 秒）后退出；
4. 换代完成。期间端口一直由 master 监听，新请求在内核连接队列排队，新 worker 起来后立即消费——**用户零感知**，整个过程一两秒。

### 2.4 gunicorn 信号速查表

| 信号 | 作用 |
|------|------|
| `HUP` | 重读配置 + 用新代码重启所有 worker（**热更新主力**） |
| `USR2` | 启动一套全新 master+worker（跑新代码），旧的照常服务（配合 `QUIT` 完成切换，用于 `preload_app=True` 场景） |
| `QUIT` | 优雅退出（处理完存量请求再停） |
| `TTIN` / `TTOU` | 增加 / 减少 worker 数量 |

### 2.5 注意事项与坑

1. **`preload_app` 必须保持 `False`**（默认）。开了 True，代码在 master 启动时预加载进内存，HUP 出来的新 worker 从 master 内存 fork，拿到的还是旧代码；那套场景要走 `USR2` 流程，操作更绕。
2. **长连接会拖慢换代**：SSE / WebSocket 这类长连接在旧 worker 退出前必须断开，否则要等满 `graceful_timeout`。脚手架未内置长连接接口，无此问题；将来加了 SSE 需注意。
3. **改端口 / 改 `gunicorn.conf.py` 里的 bind**：HUP 会用新配置重启 worker，但 master 的监听端口绑定不变——改端口请完全重启（脚手架脚本会自动检测：端口没在监听就走完全重启）。
4. **Windows 不支持 gunicorn**：脚手架的 `restart.bat` prod 模式仍用 `uvicorn --workers`，无热更新能力。
5. **dev 模式不要换 gunicorn**：`uvicorn --reload` 是开发专用（监视文件自动重启），生产开它有性能与安全隐患。

### 2.6 脚手架的集成方式

`./restart.sh prod` 的判断逻辑（三条全满足才热更新，否则完全重启）：

```
app.pid 存在
  └─ 进程存活且命令行包含 gunicorn（ps -o command=；comm 在未装 setproctitle 时显示为 python3）
       └─ APP_PORT 正在监听
            └─ kill -HUP → 输出"热更新完成"
三条任一不满足（首次启动 / 进程挂了 / 改了端口）→ 安全停止旧进程 → gunicorn 全新启动
```

即：**日常发版 = `git pull` 后再跑一遍 `./restart.sh prod`**，脚本自动选热更新或完全重启。

---

## 三、方案二：容器化滚动发布

### 3.1 原理

思路从"进程内换代"升级为"整机替换"：

```
1. 用新代码构建新镜像，起一个新容器
2. 对新容器做健康检查（GET /api/health，脚手架已内置）
3. 健康后把流量切给新容器
4. 旧容器停止接新请求 → 处理完存量 → 销毁
5. 如需多副本，逐个重复（滚动），期间服务不中断
```

### 3.2 单机 docker compose 的朴素做法

compose 本身没有滚动更新器，单机想零停机需要"双实例 + 反向代理切换"：

1. `docker compose` 起 app-v1 + nginx（nginx upstream 指向 v1）；
2. 发版时起 app-v2 容器，健康检查通过后改 nginx upstream 指向 v2，`nginx -s reload`；
3. 旧容器 `docker stop`（默认 10 秒优雅停止，存量请求处理完才退出）。

可以跑通但操作繁琐，单机更推荐直接用方案一；想要"推镜像即发版"的体验，上编排器。

### 3.3 Kubernetes 滚动发布（主场）

Deployment 关键参数：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # 滚动时最多多起 1 个新副本
      maxUnavailable: 0  # 滚动时至少保持全部旧副本可用（零容量损失）
  template:
    spec:
      containers:
        - name: app
          image: registry/my-api:v2   # 换镜像 tag 即触发滚动
          readinessProbe:             # 就绪检查：通过才接流量
            httpGet: { path: /api/health, port: 8080 }
          livenessProbe:              # 存活检查：失败自动重启容器
            httpGet: { path: /api/health, port: 8080 }
          lifecycle:
            preStop:                  # 收到终止信号先sleep，给网卡/负载均衡摘流时间
              exec: { command: ["sleep", "5"] }
      terminationGracePeriodSeconds: 30  # 优雅退出窗口，配合 gunicorn graceful_timeout
```

滚动过程由 K8s 自动完成：起新 pod → readiness 通过 → 加流量 → 杀旧 pod（先 preStop 摘流，再 SIGTERM 优雅退出）。注意容器内进程收到 SIGTERM 要能优雅退出——gunicorn 对 SIGTERM 默认快速退出，容器内建议 `QUIT` 语义或保持默认（K8s 有 30 秒宽限期兜底）。

> 小提示：K8s 场景惯例是**一个容器一个 worker**（`APP_WORKERS=1`），横向扩缩容交给 replicas；单容器多 worker 会干扰 HPA 的指标判断。

### 3.4 与方案一的关系

- 上了 K8s：滚动发布替代 gunicorn 的换代职责，容器内仍可保留 gunicorn（多 worker 压榨单机）或直接单 uvicorn worker；
- 单机 Docker：容器内用 gunicorn 多 worker + HUP（进容器发信号），或者干脆重建容器；
- 两者不冲突，按规模选：**单机 → 方案一；多实例/集群 → 方案二**。

---

## 四、方案对比与选型

| 维度 | gunicorn + HUP | compose 双实例 | K8s 滚动发布 |
|------|----------------|----------------|--------------|
| 零停机 | ✅ | ✅（手工切流） | ✅（自动） |
| 上手成本 | 低 | 中 | 高 |
| 依赖 | 无 | docker + nginx | K8s 集群 |
| 回滚 | 再 HUP 一次旧版本 | 切回 upstream | `kubectl rollout undo` |
| 健康检查 | 非必需 | 建议接 `/api/health` | 必需（readiness） |
| 适合 | 单机/小规模，脚手架默认 | 单机容器化 | 团队/生产集群 |

**选型建议**：单机部署用脚手架默认的方案一，发版就是 `git pull && ./restart.sh prod`；等上了 K8s，Dockerfile 和 `/api/health` 已经就位，按 3.3 的模板补上 Deployment 即可平滑迁移。

---

## 五、脚手架对照速查

| 场景 | 命令 | 背后 |
|------|------|------|
| 本地开发 | `./restart.sh dev` | uvicorn --reload，改代码自动重启 |
| 生产启动（首次） | `./restart.sh prod` | gunicorn master + N worker |
| 生产发版（热更新） | `git pull` 后再跑 `./restart.sh prod` | kill -HUP，服务不中断 |
| 生产发版（改了端口/配置绑定） | `./restart.sh prod`（自动走完全重启） | 停旧 → gunicorn 全新启动 |
| 容器内 | Dockerfile CMD | `gunicorn app.main:app -c gunicorn.conf.py` |
| Windows 生产 | `restart.bat prod` | uvicorn --workers（无热更新） |
