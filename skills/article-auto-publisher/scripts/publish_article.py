#!/usr/bin/env python3
"""本地 MVP 辅助脚本：自动写作并发布，或直接发布 HTML 文章。"""

from __future__ import annotations

import argparse
import html
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request


DEFAULT_BASE_URL = "http://localhost:8000/api"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "Xasz@202604"
DEFAULT_AUTHOR = "AI 内容助手"

ARTICLE_TYPES = {
    "insight": "行业洞察",
    "guide": "实操指南",
    "announcement": "产品公告",
}

TONES = {
    "professional": "专业稳健",
    "friendly": "轻松清晰",
    "direct": "直接高效",
}


@dataclass
class GeneratedArticle:
    title: str
    content: str
    summary: str


@dataclass
class PublishPayload:
    title: str
    content: str
    summary: str
    category_id: int | None = None
    category_name: str | None = None
    cover_image: str = ""
    sort_order: int = 0
    is_published: bool = True
    is_active: bool = True


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    return read_json(req)


def get_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    req = request.Request(url, method="GET")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    return read_json(req)


def read_json(req: request.Request) -> dict[str, Any]:
    try:
        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP 错误 {exc.code} {exc.reason}: {body}") from exc
    except error.URLError as exc:
        raise SystemExit(f"网络错误: {exc.reason}") from exc


def login(base_url: str, username: str, password: str) -> tuple[str, dict[str, Any]]:
    response = post_json(
        f"{base_url}/v1/auth/login",
        {"username": username, "password": password},
    )
    token = ((response.get("result") or {}).get("access_token"))
    if not token:
        raise SystemExit(f"登录失败: {json.dumps(response, ensure_ascii=False)}")
    return token, response


def list_categories(base_url: str, token: str) -> list[dict[str, Any]]:
    query = parse.urlencode({"page": 1, "size": 100})
    response = get_json(
        f"{base_url}/v1/articles/categories?{query}",
        {"Authorization": f"Bearer {token}"},
    )
    items = ((response.get("result") or {}).get("items") or [])
    if not isinstance(items, list):
        raise SystemExit(f"分类接口返回格式异常: {json.dumps(response, ensure_ascii=False)}")
    return items


def resolve_category(categories: list[dict[str, Any]], category_id: int | None, category_name: str | None) -> tuple[int, str]:
    if category_id is not None:
        for item in categories:
            if int(item.get("id")) == category_id:
                return category_id, str(item.get("name", ""))
        available = ", ".join(f'{item.get("id")}:{item.get("name")}' for item in categories)
        raise SystemExit(f"未找到分类 ID {category_id}。当前可用分类: {available}")

    if category_name:
        normalized = category_name.strip().lower()
        for item in categories:
            name = str(item.get("name", "")).strip()
            if name.lower() == normalized:
                return int(item["id"]), name
        available = ", ".join(f'{item.get("id")}:{item.get("name")}' for item in categories)
        raise SystemExit(f'未找到分类“{category_name}”。当前可用分类: {available}')

    raise SystemExit("请提供 --category-id 或 --category-name。")


def read_content(args: argparse.Namespace) -> str | None:
    if args.content:
        return args.content
    if args.content_file:
        return Path(args.content_file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        stdin_text = sys.stdin.read()
        if stdin_text.strip():
            return stdin_text
    return None


def read_payload(args: argparse.Namespace) -> PublishPayload | None:
    raw_text: str | None = None

    if args.payload:
        raw_text = args.payload
    elif args.payload_file:
        raw_text = Path(args.payload_file).read_text(encoding="utf-8")
    elif args.payload_stdin:
        raw_text = sys.stdin.read()

    if not raw_text:
        return None

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"发布载荷不是合法 JSON: {exc}") from exc

    title = str(data.get("title", "")).strip()
    content = str(data.get("content", "")).strip()
    if not title:
        raise SystemExit("发布载荷缺少 title。")
    if not content:
        raise SystemExit("发布载荷缺少 content。")

    category_id = data.get("category_id")
    category_name = data.get("category_name")
    if category_id is not None:
        category_id = int(category_id)
    elif category_name is not None:
        category_name = str(category_name).strip()

    return PublishPayload(
        title=title,
        content=content,
        summary=str(data.get("summary", "")).strip(),
        category_id=category_id,
        category_name=category_name,
        cover_image=str(data.get("cover_image", "")),
        sort_order=int(data.get("sort_order", 0)),
        is_published=bool(data.get("is_published", True)),
        is_active=bool(data.get("is_active", True)),
    )


def split_keywords(raw_keywords: str | None) -> list[str]:
    if not raw_keywords:
        return []
    parts = [item.strip() for item in raw_keywords.replace("，", ",").split(",")]
    return [item for item in parts if item]


def make_title(topic: str, article_type: str) -> str:
    if article_type == "guide":
        return f"{topic}实操指南：从理解到落地的关键步骤"
    if article_type == "announcement":
        return f"{topic}发布说明：重点变化与使用建议"
    return f"{topic}趋势观察：值得关注的机会与实践方向"


def paragraph(text: str) -> str:
    return f"<p>{html.escape(text)}</p>"


def bullet_list(items: list[str]) -> str:
    rendered = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    return f"<ul>{rendered}</ul>"


def generate_article_html(
    *,
    topic: str,
    category_name: str,
    article_type: str,
    tone: str,
    audience: str,
    keywords: list[str],
    custom_summary: str | None,
    title: str | None,
    author: str,
) -> GeneratedArticle:
    resolved_title = title or make_title(topic, article_type)
    article_label = ARTICLE_TYPES[article_type]
    tone_label = TONES[tone]
    today = datetime.now().strftime("%Y-%m-%d")

    lead = custom_summary or (
        f"围绕“{topic}”这一主题，本文从业务价值、落地重点与执行建议三个角度展开，"
        f"帮助{audience}快速形成可执行的判断。"
    )

    keywords = keywords or [topic, category_name, article_label]

    value_points = [
        f"帮助{audience}快速理解“{topic}”在当前阶段的核心价值。",
        f"结合“{category_name}”栏目定位，输出更适合后台内容运营的表达方式。",
        f"以{tone_label}的语气组织内容，兼顾可读性与直接发布的稳定性。",
    ]

    action_points = [
        f"先明确“{topic}”面向的业务场景，再确定内容重点与目标读者。",
        f"围绕关键词 { '、'.join(keywords[:4]) } 组织段落，保证文章信息密度。",
        "在结尾增加可执行建议，便于读者继续跟进或落地。",
    ]

    risk_points = [
        "避免只堆砌概念，应尽量给出可操作的判断和动作建议。",
        "避免标题过大而正文过空，段落之间要有明确递进关系。",
        "发布前确认分类、封面图和发布状态，减少后台人工返工。",
    ]

    html_parts = [
        f"<h1>{html.escape(resolved_title)}</h1>",
        f"<p><strong>发布时间：</strong>{today}</p>",
        f"<p><strong>栏目分类：</strong>{html.escape(category_name)}</p>",
        f"<p><strong>文章类型：</strong>{html.escape(article_label)}</p>",
        f"<p><strong>目标读者：</strong>{html.escape(audience)}</p>",
        paragraph(lead),
        "<h2>一、为什么这个主题值得现在写</h2>",
        paragraph(
            f"在当前内容运营场景中，“{topic}”不仅是一个热点词，更是能够连接业务表达、用户沟通与系统能力展示的重要主题。"
            f"如果文章能用{tone_label}的方式讲清楚背景、价值和路径，就更容易在后台内容模块中形成稳定的可复用资产。"
        ),
        "<h2>二、这篇文章应该传递哪些核心信息</h2>",
        bullet_list(value_points),
        "<h2>三、落地写作时建议怎么组织内容</h2>",
        paragraph(
            f"建议先用一个简洁的开场说明“{topic}”与业务目标之间的关系，再用两到三个小节拆开讲清楚关键动作。"
            f"这样既方便读者扫描，也便于后续继续扩写为专题文章、产品说明或运营素材。"
        ),
        bullet_list(action_points),
        "<h2>四、发布前需要避免哪些常见问题</h2>",
        bullet_list(risk_points),
        "<h2>五、结语</h2>",
        paragraph(
            f"如果把“{topic}”作为一次内容产品化实践来看，这篇文章的意义不只是完成发布，"
            "更是沉淀一套从选题、写作到接口投递的标准流程。后续只要复用这套流程，就能持续稳定地产出可发布内容。"
        ),
        f"<p><em>作者：{html.escape(author)}</em></p>",
    ]

    return GeneratedArticle(
        title=resolved_title,
        content="\n".join(html_parts),
        summary=lead,
    )


def publish_article(
    base_url: str,
    token: str,
    *,
    title: str,
    category_id: int,
    content: str,
    cover_image: str,
    is_published: bool,
    is_active: bool,
    sort_order: int,
) -> dict[str, Any]:
    payload = {
        "title": title,
        "category_id": category_id,
        "cover_image": cover_image,
        "content": content,
        "is_published": is_published,
        "is_active": is_active,
        "sort_order": sort_order,
    }
    return post_json(
        f"{base_url}/v1/articles/posts",
        payload,
        {"Authorization": f"Bearer {token}"},
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="一键生成并发布文章，或直接发布现成 HTML。")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API 基础地址，默认: %(default)s")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="登录用户名")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="登录密码")
    parser.add_argument("--title", help="文章标题。未提供时可根据主题自动生成")
    parser.add_argument("--topic", help="文章主题。未提供 HTML 内容时，脚本会根据主题自动写作")
    parser.add_argument("--category-id", type=int, help="文章分类 ID")
    parser.add_argument("--category-name", help="文章分类名称")
    parser.add_argument("--content", help="直接传入 HTML 内容")
    parser.add_argument("--content-file", help="HTML 文件路径")
    parser.add_argument("--payload", help="直接传入 JSON 发布载荷，适合大模型输出后直接发布")
    parser.add_argument("--payload-file", help="JSON 发布载荷文件路径")
    parser.add_argument("--payload-stdin", action="store_true", help="从标准输入读取 JSON 发布载荷")
    parser.add_argument("--cover-image", default="", help="封面图 URL")
    parser.add_argument("--sort-order", type=int, default=0, help="排序值")
    parser.add_argument("--draft", action="store_true", help="创建为草稿，不立即发布")
    parser.add_argument("--inactive", action="store_true", help="创建为禁用状态")
    parser.add_argument("--list-categories", action="store_true", help="输出文章分类后退出")
    parser.add_argument(
        "--article-type",
        choices=sorted(ARTICLE_TYPES),
        default="insight",
        help="文章类型：insight=行业洞察，guide=实操指南，announcement=产品公告",
    )
    parser.add_argument(
        "--tone",
        choices=sorted(TONES),
        default="professional",
        help="写作语气：professional=专业稳健，friendly=轻松清晰，direct=直接高效",
    )
    parser.add_argument("--audience", default="产品、运营与管理人员", help="目标读者")
    parser.add_argument("--keywords", help="补充关键词，多个关键词用英文逗号或中文逗号分隔")
    parser.add_argument("--summary", help="自定义导语摘要")
    parser.add_argument("--author", default=DEFAULT_AUTHOR, help="文章作者展示名")
    parser.add_argument("--preview-html", help="把最终 HTML 预览输出到指定文件")
    parser.add_argument("--print-html", action="store_true", help="只打印生成后的 HTML，不调用发布接口")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    token, login_response = login(args.base_url, args.username, args.password)
    categories = list_categories(args.base_url, token)

    if args.list_categories:
        output = {
            "login": {
                "username": ((login_response.get("result") or {}).get("username")),
                "tenant_id": ((login_response.get("result") or {}).get("tenant_id")),
            },
            "categories": [
                {"id": item.get("id"), "name": item.get("name"), "code": item.get("code")}
                for item in categories
            ],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    payload = read_payload(args)
    content = read_content(args)

    if payload:
        category_id, category_name = resolve_category(categories, payload.category_id, payload.category_name)
        generated = GeneratedArticle(
            title=payload.title,
            content=payload.content,
            summary=payload.summary,
        )
        cover_image = payload.cover_image
        sort_order = payload.sort_order
        is_published = payload.is_published
        is_active = payload.is_active
    else:
        category_id, category_name = resolve_category(categories, args.category_id, args.category_name)

        if content:
            final_title = args.title
            if not final_title:
                raise SystemExit("直接发布现成 HTML 时，必须提供 --title。")
            generated = GeneratedArticle(title=final_title, content=content, summary=args.summary or "")
        else:
            if not args.topic:
                raise SystemExit("未提供 HTML 内容时，必须提供 --topic 以自动生成文章。")
            generated = generate_article_html(
                topic=args.topic,
                category_name=category_name,
                article_type=args.article_type,
                tone=args.tone,
                audience=args.audience,
                keywords=split_keywords(args.keywords),
                custom_summary=args.summary,
                title=args.title,
                author=args.author,
            )

        cover_image = args.cover_image
        sort_order = args.sort_order
        is_published = not args.draft
        is_active = not args.inactive

    if args.preview_html:
        Path(args.preview_html).write_text(generated.content, encoding="utf-8")

    if args.print_html:
        print(generated.content)
        return

    response = publish_article(
        args.base_url,
        token,
        title=generated.title,
        category_id=category_id,
        content=generated.content,
        cover_image=cover_image,
        is_published=is_published,
        is_active=is_active,
        sort_order=sort_order,
    )
    output = {
        "login": {
            "username": ((login_response.get("result") or {}).get("username")),
            "tenant_id": ((login_response.get("result") or {}).get("tenant_id")),
        },
        "generated": {
            "title": generated.title,
            "summary": generated.summary,
            "preview_html": args.preview_html,
        },
        "publish_result": response,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
