---
name: fastapi-init-skill
description: FastAPI 项目一键初始化技能。面向零基础小白，提供环境探测、自动安装、完整 Web 骨架生成、JWT 鉴权、示例 CRUD、统一响应封装、一键启动/重启脚本、Swagger 文档、Docker 支持，内置 MySQL（默认）/ PostgreSQL / MongoDB / 无数据库选择，目录结构对齐 FastAPI 官方模板主流分层（api / core / crud / models / schemas / db）。用户只需说"帮我搭一个 FastAPI 项目"即可一条命令完成从零到跑的完整链路。触发词："FastAPI 脚手架"、"FastAPI 一键生成"、"初始化 FastAPI 项目"、"FastAPI 快速开始"、"fastapi init"、"搭建 FastAPI 服务"、"Python Web 骨架"、"FastAPI 开箱即用"、"FastAPI 零基础"、"FastAPI 小白"、"帮我搭一个 FastAPI"、"新建 FastAPI"、"create fastapi project"、"fastapi starter"。
---

# FastAPI Init Skill

面向**完全不懂编程的小白**，一键生成标准化、开箱即用的 FastAPI Web 服务骨架。

**本 skill 只服务一件事：创建 FastAPI 项目框架。** 不涉及业务功能开发、前端对接规范或其他技能的联动；生成后项目如何扩展见交付的 `docs/project-guide.md`。

## 核心能力清单

| # | 能力 | 说明 |
|---|------|------|
| 1 | **环境探测** | 自动检测 Python 版本（>=3.9）、pip、操作系统类型 |
| 2 | **自动安装** | 创建 venv、安装依赖、编译检查 |
| 3 | **一键启动/重启** | `./restart.sh [dev|prod]`：环境搭建、拉代码、装依赖、安全停旧进程、启动、输出日志命令 |
| 4 | **开发模式** | `./restart.sh dev` 热重载，改代码自动重启，日志 `logs/dev.log` |
| 5 | **生产模式** | `./restart.sh prod` 后台多 worker，日志 `logs/app.log` |
| 6 | **JWT 鉴权** | 注册 / 登录 / 刷新令牌 / 登出 / 当前用户注入（`/api/auth/*`） |
| 7 | **示例 CRUD** | 条目管理 `/api/items`：分页列表、详情、创建、更新、删除，作为新模块的参照实现 |
| 8 | **统一响应** | `EnvelopeRoute` 自动包装 `{ code, message, data }` |
| 9 | **全局异常** | BusinessException / -1001 校验 / -2000 兜底 |
| 10 | **安全头** | 内置 X-Frame-Options / X-Content-Type-Options 等基础安全头 + 请求日志 |
| 11 | **Docker 支持** | Dockerfile（多阶段 + 非 root）+ 三套数据库 compose 编排 |
| 12 | **Swagger 文档** | `/docs`（Swagger UI）+ `/redoc`，中文说明 + 鉴权指引 |

## 生成流程

### 第一步：询问用户（只问 2 个问题）

```
1. 项目名叫什么？（默认 my-fastapi-app）
2. 用哪个数据库？
   A. MySQL（默认，推荐）
   B. PostgreSQL
   C. MongoDB
   D. 暂时不用数据库
```

**不做**：不问技术细节、不问版本号、不问目录结构——全部自动选最佳实践。

### 第二步：环境探测

按 `references/env-setup.md` 流程执行：

1. 检测 Python 是否安装 / 版本（需 >= 3.9）
2. 检测 pip 是否可用
3. 检测操作系统（Linux / macOS / Windows）
4. 若未安装：给出明确的中文提示 + 下载链接
5. 若已安装但版本过低：给出升级指引

### 第三步：生成项目骨架

按 `references/skeleton.md` 的目录结构与代码模板，现场生成全部文件。维护者可用本 skill 根目录的 `scripts/generate_project.py` 作为 canonical 生成器参考，确保所有文件一次生成、编码正确（`.bat` 为 UTF-8 with BOM + CRLF）。

生成顺序：
1. 创建目录结构
2. 写入依赖与配置（`requirements.txt`、`.env.example`、`.env`、`.gitignore`）
3. 写入核心模块（main.py、core/config.py、core/security.py、core/response.py、core/exceptions.py、db/session.py、db/base.py）
4. 写入数据层（models → schemas → crud）
5. 写入路由层（api/deps.py、api/routes/：health、auth、items）
6. 写入启动脚本（`restart.sh` / `restart.bat`，dev/prod 双模式）
7. 写入 Docker 配置（Dockerfile + docker-compose.yml / docker-compose.pg.yml / docker-compose.mongo.yml，按需启用）
8. 写入强制交付物（docs/project-guide.md）与项目说明（README.md）

### 第四步：自动安装与启动

生成完成后：
1. 创建 Python 虚拟环境（`python -m venv venv`）
2. 从 `.env.example` 复制生成 `.env`（如不存在）
3. 安装依赖（`pip install -r requirements.txt`）
4. 编译检查（`python -m compileall app`）
5. 检测数据库是否可用，有 Docker 则自动启动数据库容器
6. 提示用户运行 `./restart.sh [dev|prod]` 或 `restart.bat [dev|prod]` 一键启动

### 第五步：交付清单

向用户汇报完整交付物：

```
✅ 项目 {{project}} 生成完毕！

📁 生成的文件：
  - 入口与核心：app/main.py、app/core/（config / security / response / exceptions）
  - 数据层：app/db/（session / base）、app/models/、app/schemas/、app/crud/
  - API 路由：app/api/（deps + routes：health / auth / items）
  - 启动脚本：restart.sh, restart.bat（dev/prod 双模式）
  - 数据库：MySQL（已配置 docker-compose.yml，可选 PG / MongoDB / 无数据库）
  - 文档：docs/project-guide.md

🚀 启动方式：
  开发模式：  ./restart.sh dev        （热重载，日志 logs/dev.log）
  生产模式：  ./restart.sh prod       （后台多 worker，日志 logs/app.log）
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

## 生成项目的目录结构

参见 `references/skeleton.md` 的「目录结构」小节。对齐 FastAPI 官方模板的主流分层：

```
app/
├── main.py              # 应用入口
├── api/                 # 路由 + 依赖注入（deps.py、routes/）
├── core/                # 配置、安全、统一响应、业务异常
├── crud/                # 数据访问层
├── models/              # SQLAlchemy ORM 模型
├── schemas/             # Pydantic v2 出入参
└── db/                  # 引擎与 Session（session.py、base.py）
```

核心约定：

- 路由前缀：`/api`
- 认证路由：`/api/auth/*`
- 示例 CRUD：`/api/items`
- 应用端口：`8080`
- Swagger：`/docs`、`/redoc`
- 健康检查：`GET /api/health`、`GET /api/health/db`
- 表名：snake_case 单数（`user`、`item`）
- 数据库默认 MySQL，可选 PostgreSQL / MongoDB / 无数据库；MongoDB 与 none 模式仅 health 路由可用

## 引用索引

| 文件 | 内容 |
|------|------|
| `scripts/generate_project.py` | canonical 项目生成器：从 `skeleton.md` / `startup-scripts.md` 提取模板并生成完整项目，保证 `.bat` 编码与文件完整性 |
| `references/skeleton.md` | 完整目录结构 + 全部文件代码模板（main/api/core/db/models/schemas/crud/.env/Docker） |
| `references/env-setup.md` | 环境探测流程、自动安装逻辑、常见问题排错 |
| `references/db-guide.md` | 数据库选型、MySQL/PG/Mongo 连接配置、Docker 启动命令 |
| `references/middleware-guide.md` | 中间件链（安全头→日志→CORS→鉴权→校验→响应→异常）与鉴权流程 |
| `references/startup-scripts.md` | `restart.sh` / `restart.bat` 脚本模板（dev/prod 双模式，一条命令完成拉代码、装依赖、安全重启、日志输出） |
| `references/project-guide-template.md` | 生成项目 `docs/project-guide.md` 的模板，含栈说明、启动方式、拓展指南 |

## 强制交付物

生成项目时必须落地一份文档：

| 文档 | 位置 | 说明 |
|------|------|------|
| 项目指南 | `docs/project-guide.md` | 按本 skill `references/project-guide-template.md` 生成：栈说明、目录结构、请求生命周期、鉴权范式、拓展指南 |

## 红线（不可绕过）

1. **不硬编码版本号**：Python / FastAPI / 依赖版本一律现场查询官方源最新稳定版。
2. **不跳过环境探测**：生成前必须先检查用户环境，无法安装则给出明确提示。
3. **不强制安装系统级数据库**：若本机有 Docker，生成逻辑可自动拉起开发数据库容器（可选）；否则提供 `references/db-guide.md` 中的 Docker 命令，由用户自行启动。
4. **不替用户提交 git**。
5. **默认值必须安全**：`.env.example` 对 `JWT_SECRET` / `CORS` / `APP_DEBUG` 有醒目警告，安全头中间件强制开启。
6. **所有注释、文档用中文**：目标用户是中文小白，不要英文注释。
7. **`.env` 与 `.gitignore` 必须随脚手架一起生成，且 `.env` 中的配置必须被服务加载**：`app/core/config.py` 通过 Pydantic Settings 读取 `.env` 全部配置，禁止在代码中硬编码端口、数据库密码、JWT 密钥等运行时可变参数。
8. **目录结构不得偏离官方模板分层**：新增文件按 `api / core / crud / models / schemas / db` 归位，不引入新的顶层目录。

## 触发关键词清单

```
FastAPI 脚手架、FastAPI 一键生成、初始化 FastAPI 项目、FastAPI 快速开始、
fastapi init、搭建 FastAPI 服务、Python Web 骨架、FastAPI 开箱即用、
FastAPI 零基础、FastAPI 小白、帮我搭一个 FastAPI、新建 FastAPI、
create fastapi project、fastapi starter
```

## 不做

- 不做业务功能开发：骨架之外的新接口、鉴权模块扩展（如 RBAC）等，生成完成后按项目指南由后续开发完成
- 不询问技术细节（ORM 选择、目录结构等——全部自动选最佳实践）
- 不安装系统级依赖（如 MySQL Server），只提供 Docker 启动命令
- 不在 SKILL.md 锁定版本号
- 不替用户提交 git
- 不加未请求的中间件（如 Redis、Celery——除非用户明确说要）
