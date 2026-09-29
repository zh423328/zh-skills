# 自动写作发布文章 Skill 使用文档

## 1. 功能概述

`article-auto-publisher` 是一个面向本地测试和后台内容初始化的文章发布 skill，当前已经支持：

- 自动登录本地系统
- 查询文章分类
- 接收大模型生成的标题和 HTML 文章
- 根据主题做本地模板化 HTML 生成
- 一键调用文章发布接口
- 输出发布结果
- 预览或导出生成后的 HTML

这个 skill 适合以下场景：

- 验证文章模块接口链路是否打通
- 快速初始化后台文章数据
- 做内部内容运营流程演示
- 搭建“主题 -> 大模型写作 -> 自动发布”的基础能力

## 2. Skill 目录结构

目录位置：

- [article-auto-publisher](/Users/zhenghui/zh-work/vue-fastapi-pgsql-admin/.agents/skills/article-auto-publisher)

主要文件：

- [SKILL.md](/Users/zhenghui/zh-work/vue-fastapi-pgsql-admin/.agents/skills/article-auto-publisher/SKILL.md)
  - skill 主说明
- [api.md](/Users/zhenghui/zh-work/vue-fastapi-pgsql-admin/.agents/skills/article-auto-publisher/references/api.md)
  - 接口说明
- [writing-guide.md](/Users/zhenghui/zh-work/vue-fastapi-pgsql-admin/.agents/skills/article-auto-publisher/references/writing-guide.md)
  - 自动写作规则
- [publish_article.py](/Users/zhenghui/zh-work/vue-fastapi-pgsql-admin/.agents/skills/article-auto-publisher/scripts/publish_article.py)
  - 发布入口脚本
- [generate_and_publish_article.py](/Users/zhenghui/zh-work/vue-fastapi-pgsql-admin/.agents/skills/article-auto-publisher/scripts/generate_and_publish_article.py)
  - 主题到大模型再到发布的一键入口
- [sample-article.html](/Users/zhenghui/zh-work/vue-fastapi-pgsql-admin/.agents/skills/article-auto-publisher/assets/sample-article.html)
  - 固定 HTML 测试样例

## 3. 默认配置

当前脚本默认配置如下：

- API 地址：`http://localhost:8000/api`
- 登录用户名：`admin`
- 登录密码：`Xasz@202604`
- 默认作者名：`AI 内容助手`
- 默认模型接口：`https://api.minimaxi.com/v1`
- 默认模型 API Key：`sk-api-QLurOWidiU395CdhYDWxw1cJx6LutY96U12ZEQOnMZ7MZUYJ807KyNlyp8iVrur4ol0dAV1UAhneoF0n7NBKCVVd4QdDe4NVyMjHZ1WMjls9R58UF1fkiHQ`
- 默认模型名称：`MiniMax-M2.7`

如果你的本地环境不同，可以通过命令参数覆盖。

## 4. 最终推荐实现方式

你最想要的流程，建议这样设计：

1. 你只输入一个主题。
2. 大模型根据这个主题生成一份 JSON。
3. JSON 里带上：
   - `title`
   - `summary`
   - `category_name` 或 `category_id`
   - `content`
4. `content` 必须是 HTML。
5. skill 的脚本负责登录、校验分类、调用文章发布接口。

这是最推荐的原因：

- 生成和发布彻底解耦
- 后续换模型不影响发布能力
- 后续可以加审核、改写、人工确认
- 更容易接自动化或工作流系统

## 5. 最终一键入口

现在脚本里已经帮你写好了默认模型配置，所以最推荐直接用这个命令：

```bash
python3 .agents/skills/article-auto-publisher/scripts/generate_and_publish_article.py \
  --topic "AI BI 在企业运营中的应用" \
  --category-name 科技
```

这个入口会自动完成：

1. 调用大模型生成标题、摘要、HTML 正文
2. 生成标准 JSON
3. 自动调用发布脚本
4. 返回文章 ID 和发布结果

如果你要先看发给模型的请求，不实际调用模型：

```bash
python3 .agents/skills/article-auto-publisher/scripts/generate_and_publish_article.py \
  --topic "AI BI 在企业运营中的应用" \
  --dry-run
```

如果你后面想切换到别的模型服务，也可以覆盖默认值：

```bash
export LLM_BASE_URL="你的模型地址"
export LLM_API_KEY="你的模型密钥"
export LLM_MODEL="你的模型名"
```

## 6. 基础命令

查看分类：

```bash
python3 .agents/skills/article-auto-publisher/scripts/publish_article.py --list-categories
```

大模型输出 JSON 后，直接通过 stdin 发布：

```bash
cat /tmp/article.json | python3 .agents/skills/article-auto-publisher/scripts/publish_article.py --payload-stdin
```

从 JSON 文件发布：

```bash
python3 .agents/skills/article-auto-publisher/scripts/publish_article.py --payload-file /tmp/article.json
```

根据主题自动生成并发布文章：

```bash
python3 .agents/skills/article-auto-publisher/scripts/publish_article.py \
  --topic "AI BI 在企业运营中的应用" \
  --category-name 科技
```

指定标题、风格和关键词后生成并发布：

```bash
python3 .agents/skills/article-auto-publisher/scripts/publish_article.py \
  --topic "AI BI 在企业运营中的应用" \
  --title "AI BI 在企业运营中的应用价值与落地建议" \
  --category-name 科技 \
  --article-type insight \
  --tone professional \
  --keywords "数据分析,运营效率,智能报表"
```

只生成 HTML，不发布：

```bash
python3 .agents/skills/article-auto-publisher/scripts/publish_article.py \
  --topic "后台系统内容自动化" \
  --category-name 科技 \
  --print-html
```

生成 HTML 并保存预览文件，再发布：

```bash
python3 .agents/skills/article-auto-publisher/scripts/publish_article.py \
  --topic "内容中台建设思路" \
  --category-name 科技 \
  --preview-html /tmp/article-preview.html
```

直接发布现成 HTML：

```bash
python3 .agents/skills/article-auto-publisher/scripts/publish_article.py \
  --title "固定 HTML 测试文章" \
  --category-name 科技 \
  --content-file .agents/skills/article-auto-publisher/assets/sample-article.html
```

## 7. 大模型输出格式建议

推荐让大模型直接输出下面这种 JSON：

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

如果你用 Codex 或其他大模型，最关键的是要求它：

- 只输出 JSON
- 不要带 Markdown 代码块
- `content` 必须是 HTML
- `category_name` 默认输出“科技”

## 8. 常用参数说明

- `--topic`
  - 文章主题。未提供 JSON 或 HTML 内容时必填。
- `--title`
  - 文章标题。可选，不传时会自动生成。
- `--payload`
  - 直接传入 JSON 发布载荷。
- `--payload-file`
  - 从 JSON 文件读取发布载荷。
- `--payload-stdin`
  - 从标准输入读取 JSON 发布载荷。
- `--llm-base-url`
  - 大模型 OpenAI 兼容接口地址。
- `--llm-api-key`
  - 大模型 API Key。
- `--llm-model`
  - 大模型名称。
- `--retry-times`
  - 模型请求失败后的重试次数，默认 `3`。
- `--retry-delay`
  - 每次重试前等待秒数，默认 `2`。
- `--llm-timeout`
  - 单次模型请求超时时间，默认 `60` 秒。
- `--category-id`
  - 按分类 ID 发布。
- `--category-name`
  - 按分类名称发布。
- `--article-type`
  - 文章类型，可选值：
    - `insight`
    - `guide`
    - `announcement`
- `--tone`
  - 写作语气，可选值：
    - `professional`
    - `friendly`
    - `direct`
- `--keywords`
  - 补充关键词，多个值用逗号分隔。
- `--summary`
  - 自定义导语摘要。
- `--preview-html`
  - 把生成后的 HTML 另存到本地文件。
- `--print-html`
  - 只打印 HTML，不调用发布接口。
- `--draft`
  - 创建为草稿。
- `--inactive`
  - 创建为禁用状态。

## 9. 推荐工作流

推荐你在本地这样使用：

1. 先执行 `--list-categories`，确认目标分类。
2. 直接用 `generate_and_publish_article.py` 输入主题，走完整链路。
3. 如果模型偶发失败，脚本会自动重试。
4. 如果模型输出 JSON 不规范，脚本会自动尝试修复。
5. 如果要检查 HTML，先加 `--preview-html` 或 `--dry-run`。

## 10. 你该怎么搞

如果你要实现“我给一个主题，大模型生成标题和文章，然后 skill 自动发布”，最实用的落地方式是：

1. 把 skill 分成两段。
   - 第一段：大模型生成 JSON
   - 第二段：脚本发布 JSON
2. 大模型输出固定结构：
   - `title`
   - `summary`
   - `category_name`
   - `content`
3. 脚本统一负责：
   - 登录
   - 分类校验
   - 发布
   - 返回结果
4. 现在这个 skill 已经把这两段都准备好了：
   - `generate_and_publish_article.py` 负责调模型
   - `publish_article.py` 负责发布
5. 如果后续你要接别的模型 API，只需要改第一段，发布脚本不用重写。
6. 目前你要求的这组模型参数，已经直接内置在脚本默认配置里了，可以直接开跑。

## 11. 当前实现边界

当前版本的“自动写作”是模板化自动生成，优势是：

- 无需额外依赖
- 本地即可运行
- 输出结构稳定
- 易于调试和扩展

但它不是通用大模型写作引擎，所以在以下方面仍可继续增强：

- 更细的行业语料
- 更丰富的文章模板
- 更强的标题与摘要生成
- 增加发布前审核或人工确认

## 12. 后续建议

如果你下一步继续升级，我建议按这个顺序演进：

1. 增加多种文章模板，例如“科技资讯”“产品公告”“活动宣传”“教程说明”。
2. 增加封面图自动选择或上传能力。
3. 增加发布前审核模式，例如只生成草稿，不直接发布。
4. 接入大模型生成正文，但继续复用现在的登录、分类和发布链路。
