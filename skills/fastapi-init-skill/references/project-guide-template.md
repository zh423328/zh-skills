# {{PROJECT_NAME}} 项目介绍 & 拓展性文档

本文件是 `fastapi-init-skill` 生成项目的默认项目指南：管「怎么跑、怎么加功能」。

## 1. 项目简介

| 项 | 值 |
|----|-----|
| 定位 | {{PROJECT_DESC}} |
| 技术栈 | {{STACK}} |
| 数据库 | {{DATABASE}} |
| 中间件 | {{MIDDLEWARES}}（无则写"无"） |
| 默认端口 | {{APP_PORT}}（环境变量 `APP_PORT` 可改） |

## 2. 快速开始

```bash
# 1. 安装依赖、生成 .env 并启动（首次）
./restart.sh dev

# 或手动：
cp .env.example .env          # 按需修改 DB / JWT / CORS 配置
docker run -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=app_db mysql:8.0  # 起数据库（如选择数据库）
./restart.sh dev              # 开发模式启动

curl http://localhost:{{APP_PORT}}/api/health
# 期望：{ "code": 0, "message": "success", "data": { "status": "ok" } }
```

环境变量全量说明见 `.env.example`（命名规范：`APP_` / `DB_` / `JWT_` / `CORS_ORIGINS`）。

## 3. 目录结构

```
{{DIRECTORY_TREE}}
```

分层职责：{{LAYER_RESPONSIBILITY}}

## 4. 接口范式

- 基础路径：所有接口挂在 `/api` 下，路由为 `/api/<资源复数>`（如 `/api/items`、`/api/orders`）。
- 方法语义：

| 方法 | 语义 | 示例 |
|------|------|------|
| GET | 查询（列表/详情），无副作用 | `GET /api/items`、`GET /api/items/1` |
| POST | 新建资源 / 登录注册等业务动作 | `POST /api/auth/login`、`POST /api/items` |
| PUT | 更新 | `PUT /api/items/1` |
| PATCH | 部分更新（预留） | `PATCH /api/items/1` |
| DELETE | 删除（预留软删除） | `DELETE /api/items/1` |

- Content-Type：JSON 接口统一 `application/json`。
- 字段级定义以 Swagger（`/docs`）为准，本文件不复述。

## 5. 入参范式

| 入参位置 | 用途 | 约定 |
|----------|------|------|
| 路径参数 | 定位单个资源 | 整数 ID，如 `/api/items/{id}` |
| 查询参数 | 过滤、分页、排序 | 分页固定 `page`（从 1 起）+ `pageSize`（≤ 100）；模糊搜索用 `keyword` |
| 请求体 | 创建/更新数据 | JSON；必填/可选/校验规则见 Swagger |
| 请求头 | 鉴权、链路 | `Authorization: Bearer {access_token}`；可传 `X-Request-Id` 做链路串联 |

规则：
1. 校验失败统一返 `-1001`，`message` 指出首个不合法字段。
2. 时间入参用 ISO 8601（如 `2026-07-10T08:00:00Z`），时区 UTC。
3. 可选字段省略即取默认值，**禁止传 `null` 占位**。

## 6. 出参范式

所有接口返回统一信封（HTTP 状态码一律 200，业务状态看 `code`）：

```json
{ "code": 0, "message": "success", "data": {} }
```

- `code === 0` 成功，`< 0` 失败；`data` 永远存在，无数据为 `null`。
- 列表接口 `data` 固定四字段：

```json
{ "page": 1, "pageSize": 20, "total": 100, "list": [] }
```

- 时间字段：`created_at` / `updated_at`，ISO 8601 + UTC；后端存储 snake_case，API 字段以 Swagger 为准。
- 错误响应同样走信封：`{ "code": -1001, "message": "用户名不能为空", "data": null }`。

## 7. 请求生命周期（拦截器链路）

一个请求从进入到返回的处理顺序：

```
{{MIDDLEWARE_CHAIN}}
```

关键拦截器行为：

| 环节 | 行为 | 失败时 |
|------|------|--------|
| CORS | 按 `CORS_ORIGINS` 回写跨域头；`*` 时不开凭证 | 浏览器拦截 |
| 请求日志 | 生成 requestId，记录 method/path/status/耗时，回写响应头 `X-Request-Id` | - |
| 鉴权 | 校验 `Authorization: Bearer`，解析出当前用户注入上下文 | `-1002`（未登录/Token 失效） |
| 参数校验 | {{VALIDATION_WAY}} | `-1001` |
| 业务处理 | handler 只返数据或抛业务异常 | 业务异常带 `code+message` |
| 信封包装 | {{ENVELOPE_WAY}} | - |
| 异常兜底 | 未捕获异常转 `-2000`「系统繁忙，请稍后再试」，不暴露堆栈 | `-2000` |

## 8. 鉴权范式

1. `POST /api/auth/register` 注册；`POST /api/auth/login` 登录成功返回 `{ access_token, refresh_token, token_type }`。
2. 把 `access_token` 存本地，后续请求统一加 `Authorization: Bearer {access_token}`，禁止逐接口手拼。
3. `access_token` 过期/无效返 `-1002` → 用 `refresh_token` 调 `POST /api/auth/refresh` 换取新令牌；若 `refresh_token` 也失效，则清 token 重新登录。
4. 免登白名单：`/api/auth/login`、`/api/auth/register`、`/api/health`、`/api/health/db`，其余接口默认需登录。

## 9. 对接前端要点

- 统一 baseURL：`http://localhost:{{APP_PORT}}/api`。
- 请求拦截器统一加 `Authorization`；响应拦截器只看 `code`：`0` 取 `data`，`-1002` 清 token 跳登录，其余展示 `message`。
- 分页读 `page / pageSize / total / list` 四字段；时间按 UTC ISO 8601 解析。
- 接口字段、示例请求以 Swagger（`/docs`）为准。

## 10. 错误码

| 错误码 | 含义 | 处理建议 |
|--------|------|----------|
| 0 | 成功 | 正常处理 data |
| -1001 | 参数校验错误 | 展示 message 并定位字段 |
| -1002 | 未授权（未登录/Token 失效） | 清 token，重新登录 |
| -1003 | 无权限 | 提示无权限 |
| -1004 | 资源不存在 | 展示空态/404 页 |
| -1005 | 资源冲突（重复/旧密码错误） | 提示重复操作 |
| -2000 | 内部错误 | 提示系统繁忙 |

## 11. 拓展指南

### 11.1 新增一个业务模块（以「文章 Post」为例）

{{MODULE_STEPS}}

每张新表在 `app/db/base.py` 中确认已被汇总导入（新模型文件需要加一行 import），这样 `create_all` 才能发现它。

### 11.2 新增中间件/拦截器

{{MIDDLEWARE_STEPS}}。新增中间件后：
1. 在 `app/main.py` 中按正确顺序注册
2. 更新 `.env.example` 中相关环境变量
3. 在本文档「请求生命周期」中补充该中间件位置

### 11.3 数据库变更

{{MIGRATION_WAY}}

### 11.4 数据库启动方式

{{DB_START_WAY}}

### 11.5 接入 Redis / 对象存储

按需接入，连接信息只从环境变量读，接入后同步更新 `.env.example` 与本文档。

## 12. 一键启动

{{ONE_CLICK_WAY}}

## 13. 相关文档

| 文档 | 用途 |
|------|------|
| `README.md` | 项目快速开始 |
| `.env.example` | 环境变量全量说明 |
| Swagger `/docs` | 接口字段级唯一事实来源 |
