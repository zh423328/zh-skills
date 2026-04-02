---
name: article-auto-publisher
description: 接收用户给出的文章主题，先由大模型生成标题与 HTML 正文，再使用配置好的管理员账号登录并调用本地 AI BI System 的文章发布接口完成自动发布。适用于主题驱动的一键写作发布场景。
---

# 自动写作发布文章

这个 skill 更推荐的工作流是：用户只提供一个主题，大模型先生成结构化文章结果，再由脚本登录后台并自动发布到文章模块。

## 能做什么

1. 接收用户给出的文章主题。
2. 先由大模型生成标题、摘要和 HTML 正文。
3. 支持把大模型输出的 JSON 载荷直接交给发布脚本。
4. 按 `category_id` 或分类名称选择文章分类。
5. 使用预设管理员账号登录本地后端。
6. 调用文章发布接口创建文章。
7. 返回文章 ID、标题、摘要和关键发布结果。

## 默认本地约定

- 后端基础地址为 `http://localhost:8000/api`。
- 默认登录账号为 `admin`。
- 默认登录密码为 `Xasz@202604`。
- 当前 MVP 默认由本地手动触发，除非用户明确要求草稿，否则直接发布。

## HTML 内容要求

- 输出可直接存入 `content` 字段的合法 HTML 片段。
- 结构尽量清晰，至少包含 `<h1>`、`<p>`、`<h2>`、`<ul>` 等基础层级，并带一个简短结语。
- 不要包裹完整页面标签，例如 `<html>`、`<body>`。
- 内容要能直接用于业务测试，不要出现占位文本。

## 推荐工作流

1. 用户只给一个主题，例如“AI BI 在企业运营中的应用”。
2. 大模型根据主题先生成一份结构化 JSON：
   - `title`
   - `summary`
   - `content`
   - `category_name` 或 `category_id`
3. `content` 必须是 HTML，不是 Markdown。
4. skill 使用 `scripts/publish_article.py --payload-stdin` 或 `--payload-file` 发布。
5. 发布完成后返回文章 ID 和接口结果。

## 最终推荐入口

如果你已经准备接大模型，优先使用：

`python3 .agents/skills/article-auto-publisher/scripts/generate_and_publish_article.py`

这个脚本会一步完成：

1. 读取主题
2. 调用 OpenAI 兼容接口模型
3. 要求模型返回 JSON
4. 自动调用发布脚本
5. 返回发布结果

## 发布 JSON 约定

推荐大模型输出这个结构：

```json
{
  "title": "AI BI 在企业运营中的应用价值与落地建议",
  "summary": "聚焦 AI BI 在企业运营中的业务价值、落地路径和执行建议。",
  "category_name": "科技",
  "content": "<h1>AI BI 在企业运营中的应用价值与落地建议</h1><p>...</p>",
  "is_published": true,
  "is_active": true,
  "sort_order": 0
}
```

## 发布流程

1. 如果用户没有提供分类 ID，先用发布脚本通过 `--list-categories` 或 `--category-name` 确定分类。
2. 如果已经有大模型生成的 JSON 载荷，优先直接发布这个 JSON。
3. 如果只有 HTML，则直接发布 HTML。
4. 如果只有主题，脚本也可以做本地模板化生成，但这只是兜底能力，不是最推荐方案。
5. 只有在命令执行更方便时，才把 HTML 或 JSON 写入本地文件。
6. 运行 `scripts/publish_article.py`，把 JSON、标题和 HTML 正文传给它。
7. 清晰返回接口结果，成功时带上文章 ID。

## 常用命令

- 查看分类：
  `python3 .agents/skills/article-auto-publisher/scripts/publish_article.py --list-categories`
- 按主题直接调用大模型并发布：
  `python3 .agents/skills/article-auto-publisher/scripts/generate_and_publish_article.py --topic "AI BI 在企业运营中的应用" --category-name 科技`
- 用大模型 JSON 结果直接发布：
  `cat /tmp/article.json | python3 .agents/skills/article-auto-publisher/scripts/publish_article.py --payload-stdin`
- 从 JSON 文件发布：
  `python3 .agents/skills/article-auto-publisher/scripts/publish_article.py --payload-file /tmp/article.json`
- 一键生成并发布：
  `python3 .agents/skills/article-auto-publisher/scripts/publish_article.py --topic "AI BI 在企业运营中的应用" --category-name 科技`
- 按分类 ID 发布：
  `python3 .agents/skills/article-auto-publisher/scripts/publish_article.py --title "示例标题" --category-id 1 --content-file /tmp/article.html`
- 按分类名称发布：
  `python3 .agents/skills/article-auto-publisher/scripts/publish_article.py --title "示例标题" --category-name 科技 --content-file /tmp/article.html`
- 只生成 HTML 预览，不发布：
  `python3 .agents/skills/article-auto-publisher/scripts/publish_article.py --topic "内容自动化" --category-name 科技 --print-html`

## 参考资料

- 需要确认接口字段和响应结构时，读取 `references/api.md`。
- 需要了解自动写作规则和可调参数时，读取 `references/writing-guide.md`。
- 需要接入模型服务时，读取 `references/llm-integration.md`。
- 需要做本地冒烟测试时，直接使用 `assets/sample-article.html`。
