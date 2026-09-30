# fastapi-init-skill 功能规格说明书

> 本文档描述 fastapi-init-skill 的完整功能清单、生成内容、工作流程与技术细节。
>
> 三份文档分工：
> - `SKILL.md`：模型入口，短、准、狠，用于触发与红线；
> - `README.md`：用户说明书，侧重怎么用、怎么启动、生产注意什么；
> - `SPEC.md`：完整规格，用于维护、迭代时查阅。

---

## 一、技能定位

**一句话描述**：面向零基础用户的 FastAPI 项目一键初始化技能。用户只需说"帮我搭一个 FastAPI 项目"，即可获得一个**立即可运行**的标准化 Web 服务骨架。

**范围边界**：本 skill 只服务创建 FastAPI 框架本身——环境探测、骨架生成、一键启动。不涉及业务功能开发、前端对接规范或其他技能的联动。

**目标用户**：
- 完全不懂编程、想快速搭建 API 服务的小白
- 需要标准化 FastAPI 骨架的开发团队
- 需要内置 JWT 鉴权、Swagger 文档的原型项目

---

## 二、触发条件

### 2.1 关键词触发（14 个）

```
FastAPI 脚手架、FastAPI 一键生成、初始化 FastAPI 项目、FastAPI 快速开始、
fastapi init、搭建 FastAPI 服务、Python Web 骨架、FastAPI 开箱即用、
FastAPI 零基础、FastAPI 小白、帮我搭一个 FastAPI、新建 FastAPI、
create fastapi project、fastapi starter
```

### 2.2 自动触发逻辑

当用户消息包含上述任一关键词时，自动路由到本技能。

---

## 三、核心功能

| # | 功能 | 说明 |
|---|------|------|
| 1 | **环境探测** | 自动检测 Python 版本（>=3.9）、pip、操作系统类型 |
| 2 | **自动安装** | 创建 venv、安装所有依赖、编译检查 |
| 3 | **一键启动/重启** | `./restart.sh [dev|prod]`：检测、拉代码、装依赖、安全停止旧进程、启动、输出日志命令 |
| 4 | **开发模式** | `./restart.sh dev` 热重载，代码修改自动重启，日志 `logs/dev.log` |
| 5 | **生产模式 + 热更新** | `./restart.sh prod` 由 gunicorn master-worker 托管；服务运行中重复执行即热更新（HUP 优雅重启 worker，服务不中断），日志 `logs/app.log` |
| 6 | **JWT 鉴权** | 注册 / 登录 / 刷新令牌 / 登出 / 当前用户注入（`/api/auth/*`） |
| 7 | **示例 CRUD** | 条目管理 `/api/items`：分页列表、详情、创建、更新、删除，作为新模块参照实现 |
| 8 | **统一响应** | `EnvelopeRoute` 自动包装 `{ code, message, data }` |
| 9 | **全局异常** | BusinessException / -1001 校验 / -2000 兜底 |
| 10 | **请求日志** | requestId + method + path + status + duration（自动过滤敏感路径） |
| 11 | **CORS** | 可配置来源、凭证策略 |
| 12 | **参数校验** | Pydantic v2 自动校验，失败转 -1001 |
| 13 | **密码加密** | bcrypt，最小 8 位 |
| 14 | **Swagger** | `/docs`（Swagger UI）+ `/redoc`（ReDoc），中文说明 + 鉴权指引 |
| 15 | **数据库** | MySQL 默认 / PostgreSQL / MongoDB / 无数据库 可选 |
| 16 | **健康检查** | `/api/health`、`/api/health/db` 含 DB 连通检查 |
| 17 | **Docker 支持** | 内置 Dockerfile + docker-compose.yml（MySQL/PG/Mongo）模板，多阶段构建 + 非 root 运行 |
| 18 | **文档** | docs/project-guide.md 强制交付 |
| 19 | **生产安全配置** | 安全头中间件、.env 安全注释、资源限制 |
| 20 | **连接池保活** | `pool_recycle` + `pool_pre_ping` |

---

## 四、用户交互流程

### 4.1 第一步：询问（最多 2 个问题）

```
1. 项目名叫什么？（默认 my-fastapi-app）
2. 用哪个数据库？
   A. MySQL（默认，推荐）
   B. PostgreSQL
   C. MongoDB
   D. 暂时不用数据库
```

**不做**：不问技术细节、不问版本号、不问目录结构——全部自动选最佳实践。

### 4.2 第二步：环境探测

```
开始
  │
  ├─ 1. 检测操作系统（Linux/macOS/Windows）
  ├─ 2. 检测 Python 版本（需 >= 3.9）
  ├─ 3. 检测 pip 是否可用
  ├─ 4. 检测虚拟环境（已有则询问是否重建）
  └─ 5. 安装依赖（pip install -r requirements.txt）
```

环境不满足时给出中文提示 + 下载链接 + 安装指引。详见 `references/env-setup.md`。

### 4.3 第三步：生成项目骨架

**生成顺序**：

1. 创建目录结构
2. 写入依赖与配置（`requirements.txt`、`.env.example`、`.env`、`.gitignore`）
3. 写入核心模块（main.py、core/config.py、core/security.py、core/response.py、core/exceptions.py、db/session.py、db/base.py）
4. 写入数据层（models → schemas → crud）
5. 写入路由层（api/deps.py、api/routes/：health、auth、items）
6. 写入启动脚本（`restart.sh` / `restart.bat`，dev/prod 双模式）与 `gunicorn.conf.py`
7. 写入 Docker 配置（Dockerfile + docker-compose.yml / docker-compose.pg.yml / docker-compose.mongo.yml，按需启用）
8. 写入强制交付物（docs/project-guide.md）与项目说明（README.md）

> 维护者可用本 skill 根目录 `scripts/generate_project.py` 作为 canonical 生成器参考，从 `references/skeleton.md` 和 `references/startup-scripts.md` 自动提取模板并生成完整项目，确保文件无遗漏、`.bat` 编码正确。

### 4.4 第四步：自动安装与验证

```
1. 创建 Python 虚拟环境（python -m venv venv）
2. 从 .env.example 复制生成 .env（如不存在）
3. 安装依赖（pip install -r requirements.txt）
4. 编译检查（python -m compileall app）
5. 检测数据库可用性，有 Docker 则自动启动数据库容器
6. 提示用户运行 `./restart.sh [dev|prod]` 或 `restart.bat [dev|prod]` 一键启动
```

### 4.5 第五步：交付清单

向用户汇报完整交付物：

```
✅ 项目 {{PROJECT_NAME}} 生成完毕！

📁 生成的文件：
  - 入口与核心：app/main.py、app/core/（config / security / response / exceptions）
  - 数据层：app/db/（session / base）、app/models/、app/schemas/、app/crud/
  - API 路由：app/api/（deps + routes：health / auth / items）
  - 启动脚本：restart.sh, restart.bat（dev/prod 双模式）
  - 数据库：MySQL（已配置 docker-compose.yml，可选 PG / MongoDB / 无数据库）
  - 文档：docs/project-guide.md

🚀 启动方式：
  开发模式：  ./restart.sh dev        （热重载，日志 logs/dev.log）
  生产模式：  ./restart.sh prod       （gunicorn master-worker，日志 logs/app.log）
  热更新：    ./restart.sh prod       （服务运行中重复执行 = HUP 优雅热更新）
  默认：      ./restart.sh            （同 dev）

📖 接口文档：
  Swagger UI：  http://localhost:8080/docs
  ReDoc：       http://localhost:8080/redoc

🔑 鉴权示例：
  注册接口：POST /api/auth/register
  登录接口：POST /api/auth/login
  登录后携带 Authorization: Bearer <token> 调用 /api/items

⚠️ 安全提醒：
  请编辑 .env 文件修改 JWT_SECRET（搜索 change-me）
  生产环境务必使用随机密钥！
```

---

## 五、生成项目的目录结构

对齐 FastAPI 官方 full-stack 模板的主流分层：`api/`（路由 + 依赖）、`core/`（配置 / 安全 / 统一响应）、`crud/`（数据访问）、`models/`（ORM）、`schemas/`（出入参）、`db/`（会话）。

```
{{PROJECT_NAME}}/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口：lifespan、CORS、异常、中间件、路由注册
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py          # 依赖注入：get_db、get_current_user
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py    # 健康检查 GET /api/health、GET /api/health/db
│   │       ├── auth.py      # 注册/登录/刷新/登出/me /api/auth/*
│   │       └── items.py     # 示例 CRUD /api/items*
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Pydantic Settings：从 .env 读取全部配置
│   │   ├── security.py      # JWT 签发/解析 + bcrypt 密码哈希
│   │   ├── exceptions.py    # 业务异常：BusinessException
│   │   └── response.py      # 统一响应：EnvelopeRoute + api_response 兜底
│   ├── crud/
│   │   ├── __init__.py
│   │   ├── user.py          # 用户数据访问
│   │   └── item.py          # 条目数据访问
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py       # 数据库引擎：SQLAlchemy async / Motor client
│   │   └── base.py          # ORM 基类与模型汇总导入
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py          # User 表模型（SQLAlchemy ORM）
│   │   └── item.py          # Item 示例业务表模型
│   └── schemas/
│       ├── __init__.py
│       ├── user.py          # Pydantic 入参/出参（RegisterRequest/LoginRequest/TokenResponse/...）
│       └── item.py          # 条目出入参（ItemCreateRequest/ItemPageResponse/...）
├── docs/
│   └── project-guide.md     # 项目指南（强制交付物）
├── restart.sh               # 一键启动/重启（Linux/macOS，dev/prod 双模式）
├── restart.bat              # 一键启动/重启（Windows，dev/prod 双模式）
├── gunicorn.conf.py         # gunicorn 生产配置（master-worker + HUP 热更新，仅 Linux/macOS）
├── requirements.txt         # Python 依赖清单
├── .env.example             # 环境变量模板（含安全注释）
├── .env                     # 实际运行环境变量（首次从 .env.example 复制）
├── .gitignore               # Git 忽略规则
├── Dockerfile               # 容器镜像构建（多阶段 + 非 root）
├── docker-compose.yml       # 默认 MySQL 服务编排
├── docker-compose.pg.yml    # PostgreSQL 编排
├── docker-compose.mongo.yml # MongoDB 编排
└── README.md                # 项目说明
```

**核心约定**：
- 路由前缀：`/api`
- 认证路由：`/api/auth/*`
- 示例 CRUD：`/api/items`
- 应用端口：`8080`
- Swagger：`/docs`、`/redoc`
- 健康检查：`GET /api/health`、`GET /api/health/db`
- 表名：snake_case 单数（`user`、`item`）
- 数据库默认 MySQL，可选 PostgreSQL / MongoDB / 无数据库；MongoDB 与 none 模式仅 health 路由可用（认证与 CRUD 模板基于 SQLAlchemy）

---

## 六、技术栈与依赖

### 6.1 核心技术栈

| 组件 | 用途 | 版本策略 |
|------|------|---------|
| Python 3.9+ | 运行时 | 自动检测本机版本 |
| FastAPI | Web 框架 | PyPI 最新稳定版 |
| Uvicorn | ASGI 服务器 | PyPI 最新稳定版 |
| SQLAlchemy 2.0 | 异步 ORM（MySQL/PostgreSQL） | PyPI 最新稳定版 |
| Motor | 异步 MongoDB 驱动 | PyPI 最新稳定版 |
| Pydantic v2 | 数据校验与配置管理 | PyPI 最新稳定版 |
| python-jose | JWT 签发与验证 | PyPI 最新稳定版 |
| gunicorn | 生产进程管理器（master-worker、HUP 热更新，仅 Linux/macOS） | PyPI 最新稳定版 |
| uvicorn-worker | gunicorn 的 ASGI worker 适配器 | PyPI 最新稳定版 |
| bcrypt | 密码加密 | PyPI 最新稳定版 |
| Alembic | 数据库迁移（生产环境） | PyPI 最新稳定版 |

### 6.2 依赖清单（requirements.txt）

```txt
fastapi
uvicorn[standard]
gunicorn
uvicorn-worker
pydantic
pydantic-settings
python-dotenv
sqlalchemy[asyncio]
pymysql
aiomysql
asyncpg
motor
cryptography
bcrypt
python-jose[cryptography]
alembic
email-validator
```

**数据库变体**：
- MySQL：已包含 `pymysql` + `aiomysql` + `cryptography`
- PostgreSQL：已包含 `asyncpg`
- MongoDB：已包含 `motor`

---

## 七、核心模块详解

### 7.1 main.py（应用入口）

**职责**：
- `lifespan` 异步上下文：启动时初始化数据库（`create_all` 或 `connect_db`），关闭时释放资源
- 中间件注册顺序：CORS → 请求日志 → 安全头
- 异常处理器：`BusinessException` → `-1001` 校验错误 → `-2000` 兜底
- 路由注册：`health`（始终）、`auth` / `items`（仅当 `DB_TYPE` 为 mysql/postgresql）
- Swagger 自定义：增强中文说明、注册/登录指引

### 7.2 core/config.py（配置管理）

**职责**：Pydantic Settings 从 `.env` 读取全部配置，支持类型校验和默认值。

**配置项清单**：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `APP_NAME` | `{{PROJECT_NAME}}` | 应用名称 |
| `APP_PORT` | `8080` | 监听端口 |
| `APP_DEBUG` | `true` | 调试模式（⚠️ 生产必须 false） |
| `DB_TYPE` | `mysql` | 数据库类型 |
| `DB_HOST` | `localhost` | 数据库地址 |
| `DB_PORT` | `3306` | 数据库端口 |
| `DB_NAME` | `app_db` | 数据库名 |
| `DB_USER` | `root` | 用户名 |
| `DB_PASSWORD` | `root` | 密码（🔴 生产必须修改） |
| `DB_URL` | 空 | 完整连接串（优先级高于分项） |
| `JWT_SECRET` | `change-me-in-production` | JWT 密钥（🔴 生产必须修改） |
| `JWT_EXPIRES_IN` | `86400` | Access Token 有效期（秒） |
| `JWT_REFRESH_EXPIRES_IN` | `604800` | Refresh Token 有效期（秒） |
| `BCRYPT_ROUNDS` | `12` | bcrypt 轮数 |
| `CORS_ORIGINS` | `*` | 跨域来源（🔴 生产必须指定域名） |

**database_url 属性**：根据 `DB_TYPE` 自动拼接连接串
- MySQL：`mysql+aiomysql://...?charset=utf8mb4`
- PostgreSQL：`postgresql+asyncpg://...`
- MongoDB：`mongodb://...?authSource=admin`

### 7.3 db/session.py（数据库引擎）

**SQLAlchemy 变体**：
```python
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,      # 连接池保活
    pool_pre_ping=True,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**MongoDB 变体**：`AsyncIOMotorClient` + `connect_db()` / `close_db()` / `get_db()` 返回数据库对象。

**none 变体**：`DummyDB`，所有操作空实现，保证无数据库模式可启动。

**db/base.py**：汇总导入 Base 与全部模型文件，确保 `create_all` 能发现全部表。

### 7.4 core/response.py（统一响应）

**EnvelopeRoute**：自定义 APIRoute，自动包装响应为 `{ code, message, data }` 格式。

**规则**：
- handler 返回裸数据 → 自动包装为 `{ code: 0, message: "success", data: ... }`
- 非 JSON 响应（文件下载等）→ 自动透传，不包信封
- 异常处理器使用 `api_response()` 构造错误信封

### 7.5 api/deps.py（依赖注入）

**get_db()**：从 `db/session.py` 透出，获取数据库 Session（SQLAlchemy）或 Database 对象（MongoDB）
**get_current_user()**：解析 JWT Bearer Token，注入当前用户信息字典 `{ user_id, username }`

### 7.6 core/security.py（安全工具）

- `create_access_token(user_id, username)` → 签发 access_token（24h）
- `create_refresh_token(user_id, username)` → 签发 refresh_token（7d）
- `decode_token(token)` → 解析并验证 Token（失败抛 JWTError）
- `hash_password(password)` → bcrypt 哈希（12 rounds）
- `verify_password(plain, hashed)` → 验证密码

### 7.7 路由层（api/routes/）与数据层（crud/）

| 路由文件 | 前缀 | 端点 | 说明 |
|----------|------|------|------|
| health.py | `/api` | `GET /health` | 服务状态 |
| health.py | `/api` | `GET /health/db` | 数据库连通检查 |
| auth.py | `/api/auth` | `POST /register` | 用户注册 |
| auth.py | `/api/auth` | `POST /login` | 用户登录 |
| auth.py | `/api/auth` | `POST /refresh` | 刷新 Token |
| auth.py | `/api/auth` | `POST /logout` | 登出（清除 refresh_token） |
| auth.py | `/api/auth` | `GET /me` | 当前用户信息 |
| items.py | `/api/items` | `GET ""` | 条目列表（分页） |
| items.py | `/api/items` | `POST ""` | 创建条目 |
| items.py | `/api/items` | `GET /{item_id}` | 条目详情 |
| items.py | `/api/items` | `PUT /{item_id}` | 更新条目（仅 owner） |
| items.py | `/api/items` | `DELETE /{item_id}` | 删除条目（仅 owner） |

**分层职责**：
- `api/routes/`：接请求、做业务编排（参数校验、权限检查、异常抛出），返回裸数据或 Pydantic 模型
- `crud/`：纯数据访问（增删改查），不含业务判断
- `schemas/`：出入参模型；`models/`：ORM 表模型

---

## 八、启动脚本详解

### 8.1 脚本矩阵

| 脚本 | 平台 | 模式 | 启动方式 | 热更新 | 日志 |
|------|------|------|----------|--------|------|
| `restart.sh` | Linux/macOS | `dev`（默认） | `uvicorn --reload` | 文件变更热重载 | `logs/dev.log` |
| `restart.sh` | Linux/macOS | `prod` | `gunicorn -c gunicorn.conf.py` | ✅ HUP 优雅重启 worker | `logs/app.log` |
| `restart.bat` | Windows | `dev` / `prod` | uvicorn | ❌（gunicorn 不支持 Windows） | 同上 |

### 8.2 restart.sh / restart.bat 工作流程

```
[1/5] 检测 git 仓库，存在则 git pull（失败仅警告）
[2/5] 创建/激活虚拟环境，安装/更新依赖
[3/5] prod 且 gunicorn master 存活且端口在监听 → kill -HUP 热更新（跳过后续步骤）
      否则：安全停止旧进程（PID 文件 + 端口兜底）
[4/5] 启动服务（dev: uvicorn --reload / prod: gunicorn master-worker）
[5/5] 写入 PID 文件，输出日志查看命令
```

### 8.3 生产热更新机制

`restart.sh prod` 在服务运行中重复执行时，脚本检测 `app.pid` 进程存活、进程命令行包含 gunicorn（`ps -o command=`，gunicorn 的 comm 显示为 python3）、`APP_PORT` 在监听三个条件，全部满足则只发 `kill -HUP`：

1. master 重读 `gunicorn.conf.py`
2. fork 新 worker（重新 import 磁盘上的新代码）
3. 旧 worker 停止接新请求，处理完存量请求后退出（最长等 `graceful_timeout` 秒）
4. 端口始终由 master 监听，用户零感知

条件任一不满足（首次启动、进程已挂、改了端口）则走完全重启。**关键前提：`gunicorn.conf.py` 中 `preload_app=False`（默认），否则 HUP 出来的 worker 仍跑旧代码。**

### 8.4 安全停止旧进程（完全重启路径）

1. 读取 `app.pid`，若进程仍为 uvicorn/gunicorn/python，则 `kill` 优雅停止
2. 若 PID 文件丢失/失效，使用端口扫描清理占用 `APP_PORT` 的残留进程
3. 清理后等待 1 秒，确保端口释放

### 8.5 启动参数

```bash
./restart.sh        # dev 模式：uvicorn 热重载，日志 logs/dev.log
./restart.sh prod   # prod 模式：gunicorn master-worker，日志 logs/app.log
./restart.sh prod   # 服务运行中再次执行：热更新
```

环境变量（由 `gunicorn.conf.py` 与脚本共同约定）：

- `APP_PORT`：默认 8080
- `APP_WORKERS`：`prod` 模式 worker 数，默认 2

---

## 九、Docker 支持

### 9.1 Dockerfile（多阶段构建）

```dockerfile
# 构建阶段
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 运行阶段
FROM python:3.11-slim
WORKDIR /app
# 非 root 用户 + 仅安装产物
COPY --from=builder /root/.local /home/appuser/.local
COPY . .
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
```

### 9.2 docker-compose 编排

**默认 MySQL**：`docker-compose.yml`
**PostgreSQL**：`docker-compose.pg.yml`
**MongoDB**：`docker-compose.mongo.yml`

三份编排均只含数据库服务（带数据卷持久化），应用本体由 `restart.sh` 或 Dockerfile 启动。

---

## 十、错误码体系

| code | 含义 | 触发场景 |
|------|------|---------|
| 0 | 成功 | 正常响应 |
| -1001 | 参数校验失败 | Pydantic 校验不通过 |
| -1002 | 认证失败 | 未登录 / Token 无效 / 密码错误 |
| -1003 | 无权限 | 已登录但无操作权限（如操作他人条目） |
| -1004 | 资源不存在 | 用户/条目未找到 |
| -1005 | 资源冲突 | 用户名已存在 / 重复提交 |
| -1006 | 请求过于频繁 | 限流触发（预留） |
| -1031 | 请求体过大 | 超过请求体大小限制 |
| -2000 | 系统异常 | 未预期的内部错误 |

---

## 十一、强制交付物

生成项目时必须落地一份文档（模板位于本 skill `references/` 目录）：

| 文档 | 位置 | 说明 |
|------|------|------|
| 项目指南 | `docs/project-guide.md` | 按 `references/project-guide-template.md` 生成：栈说明、目录结构、请求生命周期、鉴权范式、对接要点、拓展指南 |

---

## 十二、红线（不可绕过）

1. **不硬编码版本号**：Python / FastAPI / 依赖版本一律现场查询官方源最新稳定版。
2. **不跳过环境探测**：生成前必须先检查用户环境，无法安装则给出明确提示。
3. **不强制安装系统级数据库**：若本机有 Docker，`restart` 脚本或用户可参照 `references/db-guide.md` 快速启动开发数据库；否则提供 Docker 启动命令，由用户自行启动。
4. **不替用户提交 git**。
5. **生产默认值必须安全**：Dockerfile 非 root 运行、安全头强制开启、`.env.example` 对 `JWT_SECRET` / `CORS` / `APP_DEBUG` 有醒目警告。
6. **所有注释、文档用中文**：目标用户是中文小白，不要英文注释。
7. **`.env` 与 `.gitignore` 必须随脚手架一起生成，且 `.env` 配置必须被服务加载**：`app/core/config.py` 通过 Pydantic Settings 读取 `.env` 全部配置，禁止在代码中硬编码端口、数据库密码、JWT 密钥等运行时可变参数。`.gitignore` 必须忽略 `.env` 及 `.env.*.local` 等敏感文件。
8. **目录结构不得偏离官方模板分层**：新增文件按 `api / core / crud / models / schemas / db` 归位，不引入新的顶层目录。

---

## 十三、后续扩展方向

| 方向 | 说明 | 优先级 |
|------|------|--------|
| 密码复杂度校验 | Pydantic validator 强制要求大小写+数字+特殊字符 | 🟡 |
| 速率限制（Rate Limiting） | 基于 Redis 的限流中间件 | 🟡 |
| 操作审计日志 | 登录/登出/密码修改等安全事件记录 | 🟡 |
| TLS/HTTPS 配置 | Nginx / Traefik 反向代理模板 | 🟡 |
| Alembic 迁移脚手架 | 生成 alembic/ 目录与首个迁移 | 🟡 |
| K8s 部署模板 | Deployment + Service + ConfigMap YAML | 🟢 |
| Prometheus 指标 | `prometheus-fastapi-instrumentator` 暴露 /metrics | 🟢 |
| Sentry 异常上报 | 生产环境自动上报未捕获异常 | 🟢 |

---

*文档版本：v3.0（2026-09-29）*
