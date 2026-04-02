# 大模型接入说明

这个 skill 新增了一个真正的一键入口：

- `scripts/generate_and_publish_article.py`

它负责：

1. 接收文章主题
2. 调用 OpenAI 兼容接口的大模型
3. 要求模型返回结构化 JSON
4. 把 JSON 交给 `publish_article.py`
5. 自动登录并发布文章

## 推荐环境变量

当前脚本已经内置了默认模型配置：

- `LLM_BASE_URL`
  - `https://api.minimaxi.com/v1`
- `LLM_API_KEY`
  - `sk-api-QLurOWidiU395CdhYDWxw1cJx6LutY96U12ZEQOnMZ7MZUYJ807KyNlyp8iVrur4ol0dAV1UAhneoF0n7NBKCVVd4QdDe4NVyMjHZ1WMjls9R58UF1fkiHQ`
- `LLM_MODEL`
  - `MiniMax-M2.7`

也就是说，如果你暂时不改模型配置，直接运行脚本即可。

当然，你也仍然可以用环境变量覆盖：

- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

脚本也兼容这组环境变量：

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

## 最常见用法

```bash
python3 .agents/skills/article-auto-publisher/scripts/generate_and_publish_article.py \
  --topic "AI BI 在企业运营中的应用" \
  --category-name 科技
```

## 调试建议

如果你暂时还没接好模型，可以先用：

```bash
python3 .agents/skills/article-auto-publisher/scripts/generate_and_publish_article.py \
  --topic "AI BI 在企业运营中的应用" \
  --dry-run
```

这样会只输出准备发给模型的请求，不会实际调用模型，也不会发布文章。

## 重试与 JSON 修复

这个脚本已经内置两层容错：

1. 模型请求失败自动重试
   - 默认重试 `3` 次
   - 默认每次间隔 `2` 秒
2. 模型输出不是合法 JSON 时自动修复
   - 会把原始输出再发给模型
   - 要求模型只返回修复后的 JSON

你也可以手动控制重试参数：

```bash
python3 .agents/skills/article-auto-publisher/scripts/generate_and_publish_article.py \
  --topic "AI BI 在企业运营中的应用" \
  --retry-times 5 \
  --retry-delay 3
```

如果模型接口响应慢，还可以调大单次请求超时：

```bash
python3 .agents/skills/article-auto-publisher/scripts/generate_and_publish_article.py \
  --topic "AI BI 在企业运营中的应用" \
  --llm-timeout 120
```

## 输出约定

脚本要求模型返回 JSON，字段至少包括：

- `title`
- `summary`
- `category_name`
- `content`
- `is_published`
- `is_active`
- `sort_order`

其中 `content` 必须是 HTML。
