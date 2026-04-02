# 本地文章发布接口说明

本地 MVP 默认基础地址：

- `http://localhost:8000/api`

## 登录接口

- 接口：`POST /v1/auth/login`
- 请求体：

```json
{
  "username": "admin",
  "password": "Xasz@202604"
}
```

- 成功响应结构：

```json
{
  "code": 200,
  "msg": "登录成功",
  "result": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer",
    "user_id": 1,
    "username": "admin",
    "is_superuser": true,
    "tenant_id": null
  }
}
```

## 查询文章分类

- 接口：`GET /v1/articles/categories?page=1&size=100`
- 请求头：`Authorization: Bearer <access_token>`
- 当前本地已有分类：
  - `1`: `科技`
  - `2`: `美食`

## 创建文章

- 接口：`POST /v1/articles/posts`
- 请求头：`Authorization: Bearer <access_token>`
- JSON 请求体：

```json
{
  "title": "文章标题",
  "category_id": 1,
  "cover_image": "",
  "content": "<h1>文章标题</h1><p>HTML 正文</p>",
  "is_published": true,
  "is_active": true,
  "sort_order": 0
}
```

必填字段：

- `title`
- `category_id`
- `content`

说明：

- `content` 存储的是 HTML。
- 虽然 OpenAPI 没有显式声明鉴权方案，但后端实际会校验文章相关权限。
- 当前 MVP 的做法是先登录，再复用返回的 `access_token` 调后续接口。

## 推荐脚本入口

统一入口脚本：

- `scripts/publish_article.py`

支持两种模式：

1. 自动写作并发布
   - 提供 `--topic` 和分类参数
2. 直接发布现成 HTML
   - 提供 `--title` 和 `--content` 或 `--content-file`
