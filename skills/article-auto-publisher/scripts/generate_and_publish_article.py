#!/usr/bin/env python3
"""主题 -> 大模型生成 -> 自动发布文章。"""

from __future__ import annotations

import argparse
import json
import os
import socket
import time
from pathlib import Path
from typing import Any
from urllib import error, request

from publish_article import main as publish_main


DEFAULT_LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    os.getenv("OPENAI_BASE_URL", "https://api.minimaxi.com/v1"),
)
DEFAULT_LLM_API_KEY = os.getenv(
    "LLM_API_KEY",
    os.getenv("OPENAI_API_KEY", "sk-api-QLurOWidiU395CdhYDWxw1cJx6LutY96U12ZEQOnMZ7MZUYJ807KyNlyp8iVrur4ol0dAV1UAhneoF0n7NBKCVVd4QdDe4NVyMjHZ1WMjls9R58UF1fkiHQ"),
)
DEFAULT_LLM_MODEL = os.getenv(
    "LLM_MODEL",
    os.getenv("OPENAI_MODEL", "MiniMax-M2.7"),
)
DEFAULT_RETRY_TIMES = 3
DEFAULT_RETRY_DELAY = 2.0
DEFAULT_LLM_TIMEOUT = 60.0
_REQUEST_CONTEXT_TIMEOUT = DEFAULT_LLM_TIMEOUT


def normalize_base_url(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    if cleaned.endswith("/chat/completions"):
        return cleaned
    if cleaned.endswith("/v1"):
        return f"{cleaned}/chat/completions"
    return f"{cleaned}/v1/chat/completions"


def extract_json_candidate(text: str) -> str:
    stripped = strip_code_fence(text)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]
    return stripped


def extract_json_text(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        raise SystemExit(f"模型返回缺少 choices: {json.dumps(response, ensure_ascii=False)}")

    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        if text_parts:
            return "".join(text_parts)
    raise SystemExit(f"模型返回中找不到文本内容: {json.dumps(response, ensure_ascii=False)}")


def strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def build_messages(args: argparse.Namespace) -> list[dict[str, str]]:
    requirements = [
        "你是一个中文内容写作助手。",
        "请围绕给定主题，生成一篇可以直接发布到后台系统的文章。",
        "你必须只输出 JSON 对象，不要输出解释，不要输出 Markdown 代码块。",
        "JSON 必须包含字段：title、summary、category_name、content、is_published、is_active、sort_order。",
        "content 必须是 HTML 片段，不是 Markdown，至少包含 h1、p、h2、ul。",
        f"category_name 默认使用“{args.category_name}”。",
        f"is_published 固定为 {str(not args.draft).lower()}。",
        f"is_active 固定为 {str(not args.inactive).lower()}。",
        f"sort_order 固定为 {args.sort_order}。",
        "title 要简洁自然，适合后台文章标题。",
        "summary 用 1 到 2 句话概括文章内容。",
    ]

    if args.extra_requirements:
        requirements.append(f"额外要求：{args.extra_requirements}")

    user_prompt = "\n".join(
        [
            f"主题：{args.topic}",
            f"目标分类：{args.category_name}",
            f"目标读者：{args.audience}",
            f"写作语气：{args.tone}",
            f"文章类型：{args.article_type}",
            f"关键词：{args.keywords or '无'}",
            "请直接返回 JSON。",
        ]
    )

    return [
        {"role": "system", "content": "\n".join(requirements)},
        {"role": "user", "content": user_prompt},
    ]


def post_llm_request(endpoint: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with request.urlopen(req, timeout=_REQUEST_CONTEXT_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"模型请求失败 HTTP {exc.code} {exc.reason}: {body}") from exc
    except error.URLError as exc:
        raise SystemExit(f"模型请求网络错误: {exc.reason}") from exc
    except TimeoutError as exc:
        raise SystemExit(f"模型请求超时，超过 {int(_REQUEST_CONTEXT_TIMEOUT)} 秒仍未返回。") from exc
    except socket.timeout as exc:
        raise SystemExit(f"模型请求超时，超过 {int(_REQUEST_CONTEXT_TIMEOUT)} 秒仍未返回。") from exc


def call_llm(args: argparse.Namespace, messages: list[dict[str, str]]) -> dict[str, Any]:
    if not args.llm_base_url:
        raise SystemExit("缺少 --llm-base-url，或环境变量 LLM_BASE_URL / OPENAI_BASE_URL。")
    if not args.llm_api_key:
        raise SystemExit("缺少 --llm-api-key，或环境变量 LLM_API_KEY / OPENAI_API_KEY。")
    if not args.llm_model:
        raise SystemExit("缺少 --llm-model，或环境变量 LLM_MODEL / OPENAI_MODEL。")

    payload = {
        "model": args.llm_model,
        "messages": messages,
        "temperature": args.temperature,
        "response_format": {"type": "json_object"},
    }
    if args.max_tokens is not None:
        payload["max_tokens"] = args.max_tokens

    endpoint = normalize_base_url(args.llm_base_url)
    last_error: Exception | None = None

    for attempt in range(1, args.retry_times + 1):
        try:
            return post_llm_request(endpoint, args.llm_api_key, payload)
        except SystemExit as exc:
            last_error = exc
            if attempt >= args.retry_times:
                raise
            time.sleep(args.retry_delay)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = SystemExit(f"模型请求失败 HTTP {exc.code} {exc.reason}: {body}")
            if attempt >= args.retry_times:
                raise last_error
            time.sleep(args.retry_delay)

    if last_error:
        raise last_error
    raise SystemExit("模型请求失败，且没有拿到可用错误信息。")


def repair_payload_with_llm(args: argparse.Namespace, raw_output: str, parse_error: str) -> dict[str, Any]:
    endpoint = normalize_base_url(args.llm_base_url)
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个 JSON 修复助手。"
                "请把用户提供的内容修复成合法 JSON。"
                "你必须只输出 JSON 对象，不要输出解释，不要输出 Markdown 代码块。"
                "JSON 必须包含字段：title、summary、category_name、content、is_published、is_active、sort_order。"
                "content 必须保持为 HTML 字符串。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"下面是模型原始输出，请修复为合法 JSON。\n"
                f"解析错误：{parse_error}\n"
                f"原始输出：\n{raw_output}"
            ),
        },
    ]
    payload = {
        "model": args.llm_model,
        "messages": messages,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    response = post_llm_request(endpoint, args.llm_api_key, payload)
    repaired_text = extract_json_candidate(extract_json_text(response))
    try:
        return json.loads(repaired_text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"JSON 修复失败: {exc}\n修复输出:\n{repaired_text}") from exc


def parse_model_payload(args: argparse.Namespace, response: dict[str, Any]) -> dict[str, Any]:
    raw_text = extract_json_text(response)
    text = extract_json_candidate(raw_text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return repair_payload_with_llm(args=args, raw_output=raw_text, parse_error=str(exc))

    required = ["title", "summary", "category_name", "content", "is_published", "is_active", "sort_order"]
    missing = [key for key in required if key not in payload]
    if missing:
        return repair_payload_with_llm(
            args=args,
            raw_output=raw_text,
            parse_error=f"缺少字段: {', '.join(missing)}",
        )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="根据主题调用大模型生成文章，再自动发布。")
    parser.add_argument("--topic", required=True, help="文章主题")
    parser.add_argument("--category-name", default="科技", help="目标分类名称，默认: %(default)s")
    parser.add_argument("--audience", default="产品、运营与管理人员", help="目标读者")
    parser.add_argument("--tone", default="专业、清晰、可直接发布", help="写作语气")
    parser.add_argument("--article-type", default="行业洞察", help="文章类型描述")
    parser.add_argument("--keywords", help="补充关键词，多个关键词用逗号分隔")
    parser.add_argument("--extra-requirements", help="附加写作要求")
    parser.add_argument("--temperature", type=float, default=0.7, help="模型温度，默认: %(default)s")
    parser.add_argument("--max-tokens", type=int, help="模型输出 token 上限")
    parser.add_argument("--llm-base-url", default=DEFAULT_LLM_BASE_URL, help="OpenAI 兼容接口基础地址")
    parser.add_argument("--llm-api-key", default=DEFAULT_LLM_API_KEY, help="模型 API Key")
    parser.add_argument("--llm-model", default=DEFAULT_LLM_MODEL, help="模型名称")
    parser.add_argument("--save-payload", help="把模型生成的 JSON 保存到文件")
    parser.add_argument("--dry-run", action="store_true", help="只输出将发送给模型的请求，不实际调用模型或发布")
    parser.add_argument("--retry-times", type=int, default=DEFAULT_RETRY_TIMES, help="模型请求失败后的重试次数")
    parser.add_argument("--retry-delay", type=float, default=DEFAULT_RETRY_DELAY, help="每次重试前等待秒数")
    parser.add_argument("--llm-timeout", type=float, default=DEFAULT_LLM_TIMEOUT, help="单次模型请求超时时间，单位秒")
    parser.add_argument("--draft", action="store_true", help="生成草稿，不直接发布")
    parser.add_argument("--inactive", action="store_true", help="生成禁用状态文章")
    parser.add_argument("--sort-order", type=int, default=0, help="文章排序值")
    parser.add_argument("--cover-image", default="", help="封面图 URL")
    parser.add_argument("--preview-html", help="把模型返回的 HTML 正文保存到文件")
    parser.add_argument("--publish-args", help="额外透传给发布脚本的参数，原样追加")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    global _REQUEST_CONTEXT_TIMEOUT
    _REQUEST_CONTEXT_TIMEOUT = args.llm_timeout
    messages = build_messages(args)

    if args.dry_run:
        output = {
            "endpoint": normalize_base_url(args.llm_base_url) if args.llm_base_url else None,
            "model": args.llm_model,
            "messages": messages,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    response = call_llm(args, messages)
    payload = parse_model_payload(args, response)
    payload["category_name"] = payload.get("category_name") or args.category_name
    payload["is_published"] = not args.draft
    payload["is_active"] = not args.inactive
    payload["sort_order"] = payload.get("sort_order", args.sort_order)
    payload["cover_image"] = payload.get("cover_image", args.cover_image)

    if args.save_payload:
        Path(args.save_payload).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.preview_html:
        Path(args.preview_html).write_text(str(payload["content"]), encoding="utf-8")

    publish_argv = [
        "publish_article.py",
        "--payload",
        json.dumps(payload, ensure_ascii=False),
    ]
    if args.publish_args:
        publish_argv.extend(args.publish_args.split())

    original_argv = list(os.sys.argv)
    try:
        os.sys.argv = publish_argv
        publish_main()
    finally:
        os.sys.argv = original_argv


if __name__ == "__main__":
    main()
