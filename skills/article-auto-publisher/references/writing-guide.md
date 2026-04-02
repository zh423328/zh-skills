# 自动写作策略

这个 skill 现在有两种写作模式：

1. 推荐模式：大模型生成标题和 HTML，脚本负责发布
2. 兜底模式：脚本本地模板化生成 HTML，再发布

推荐模式更接近你想要的产品形态，因为生成质量和发布流程可以解耦。

## 推荐的模型输出格式

建议让大模型输出 JSON，而不是自由文本。推荐字段：

- `title`
- `summary`
- `category_name` 或 `category_id`
- `content`
- `is_published`
- `is_active`
- `sort_order`

其中：

- `content` 必须是 HTML
- `title` 必须是纯文本标题
- `summary` 用于回显和记录

推荐输出示例：

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

## 推荐提示词思路

如果你是让大模型先生成内容，再调用 skill 发布，提示词建议明确要求：

- 输入只有一个主题
- 输出必须是 JSON
- `content` 必须是 HTML
- 不要输出 Markdown 代码块
- 不要输出解释说明

可用的提示词骨架：

```text
请围绕我提供的主题生成一篇可直接发布到后台系统的文章。
要求：
1. 输出 JSON，不要输出解释。
2. JSON 字段必须包含：title、summary、category_name、content、is_published、is_active、sort_order。
3. content 必须是 HTML 片段，至少包含 h1、p、h2、ul。
4. category_name 默认输出“科技”。
5. is_published=true，is_active=true，sort_order=0。
主题：{{topic}}
```

## 默认写法

- 标题：如果没有显式传入 `--title`，根据 `--topic` 和 `--article-type` 自动生成。
- 导语：优先使用 `--summary`，否则由脚本自动生成一段摘要。
- 正文结构：
  - 文章标题
  - 发布时间、栏目分类、文章类型、目标读者
  - 导语
  - 为什么现在值得写
  - 核心信息
  - 落地建议
  - 风险提醒
  - 结语
- 输出格式：标准 HTML 片段，可直接写入文章接口 `content` 字段。

## 支持的文章类型

- `insight`
  - 适合趋势观察、行业分析、运营观点
- `guide`
  - 适合操作指南、流程拆解、内部培训
- `announcement`
  - 适合功能上线说明、版本更新、产品公告

## 支持的写作语气

- `professional`
  - 适合正式发布、内部制度、运营公告
- `friendly`
  - 适合知识科普、轻阅读内容
- `direct`
  - 适合结论优先、执行导向的文章

## 推荐用法

1. 如果只想快速验证一键链路：
   - 传 `--topic`
   - 传 `--category-name`
2. 如果想控制风格：
   - 补充 `--article-type`
   - 补充 `--tone`
   - 补充 `--keywords`
3. 如果想先看结果再决定是否发布：
   - 先加 `--print-html`
   - 或使用 `--preview-html`

## 使用边界

- 当前脚本内置的生成逻辑只是兜底能力，重点是稳定、可测、可快速扩展。
- 如果后续接入真正的大模型写作，建议保留现在这条发布链路，只替换生成环节。
