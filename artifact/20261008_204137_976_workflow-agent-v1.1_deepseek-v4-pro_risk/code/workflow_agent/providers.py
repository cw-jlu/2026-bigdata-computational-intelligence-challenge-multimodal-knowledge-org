"""Small HTTP adapters. Credentials are read only from named environment variables."""
from __future__ import annotations

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from .common import register_secret


class ProviderError(RuntimeError):
    pass


class Provider:
    def __init__(self, config, settings, transport=None):
        self.config = config
        self.settings = settings
        self.transport = transport or self._post
        self.protocol = config.get("protocol")
        if self.protocol not in {"openai", "anthropic"}:
            raise ValueError("provider protocol 必须是 openai 或 anthropic")
        parsed = urlsplit(config.get("base_url", ""))
        if not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
            raise ValueError("请配置不含凭证或查询参数的 API base_url（包含 /v1 时保留）")
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            raise ValueError("API 地址必须使用 HTTPS，本地测试服务除外")
        if not config.get("model"):
            raise ValueError("请配置实际 model 名称")
        self.key = os.environ.get(config["api_key_env"], "")
        if not self.key:
            raise ValueError(f"缺少环境变量 {config['api_key_env']}")
        register_secret(self.key)
        self.audit = None
        self.request_sequence = 0

    def emit(self, event):
        if self.audit:
            self.audit(event)

    def _post(self, url, headers, body):
        for attempt in range(self.settings.get("retries", 2) + 1):
            started = time.monotonic()
            self.emit({"stage": "http_attempt", "attempt": attempt + 1, "endpoint": url})
            try:
                req = Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
                with urlopen(req, timeout=self.settings.get("timeout_seconds", 90)) as response:
                    data = json.load(response)
                    self.emit({"stage": "http_success", "attempt": attempt + 1, "latency_seconds": time.monotonic() - started,
                               "http_status": response.status, "request_id": response.headers.get("x-request-id")})
                    return data
            except HTTPError as exc:
                self.emit({"stage": "http_error", "attempt": attempt + 1, "http_status": exc.code, "latency_seconds": time.monotonic() - started})
                # Never persist response bodies: gateways may echo credentials.
                if exc.code not in {429, 500, 502, 503, 504} or attempt == self.settings.get("retries", 2):
                    raise ProviderError(f"API HTTP {exc.code}；请核对协议、模型和参数") from None
            except (URLError, TimeoutError):
                self.emit({"stage": "http_error", "attempt": attempt + 1, "error": "connection_or_timeout", "latency_seconds": time.monotonic() - started})
                if attempt == self.settings.get("retries", 2):
                    raise ProviderError("API 网络超时或连接失败") from None
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.emit({"stage": "http_error", "attempt": attempt + 1, "error": "invalid_json", "latency_seconds": time.monotonic() - started})
                raise ProviderError("API 没有返回有效 JSON；请核对网关地址与协议") from None
            time.sleep(min(2 ** attempt, 4))
        raise ProviderError("API 重试失败")

    def request_payload(self, system, messages, tools):
        body = {"model": self.config["model"]}
        if self.protocol == "openai":
            body.update(messages=[{"role": "system", "content": system}] + messages,
                        max_completion_tokens=self.settings["max_output_tokens"])
            if tools:
                body["tools"] = [{"type": "function", "function": t} for t in tools]
                body["tool_choice"] = "auto"
        else:
            body.update(system=system, messages=messages, max_tokens=self.settings["max_output_tokens"])
            if tools:
                body["tools"] = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools]
        extra = self.config.get("extra_body", {})
        if any(k in extra for k in {"model", "messages", "system", "tools", "tool_choice", "stream"}):
            raise ValueError("extra_body 不能覆盖模型、消息、工具或流式协议")
        body.update(extra)
        if self.protocol == "openai" and "max_tokens" in extra:
            body.pop("max_completion_tokens", None)
        return body

    def complete(self, system, messages, tools):
        try:
            return self._complete(system, messages, tools)
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"API 响应结构与配置协议不符（{type(exc).__name__}）") from None

    def _complete(self, system, messages, tools):
        self.request_sequence += 1
        body = self.request_payload(system, messages, tools)
        self.emit({"stage": "provider_request", "request_sequence": self.request_sequence, "protocol": self.protocol, "body": body})
        headers = {"Content-Type": "application/json"}
        base = self.config["base_url"].rstrip("/")
        if self.protocol == "openai":
            headers["Authorization"] = "Bearer " + self.key
            raw = self.transport(base + "/chat/completions", headers, body)
            self.emit({"stage": "provider_response", "request_sequence": self.request_sequence, "body": raw})
            choice = raw["choices"][0]
            msg = dict(choice["message"])
            if not self.config.get("preserve_reasoning_content", False):
                msg.pop("reasoning_content", None)
            calls = [{"id": c["id"], "name": c["function"]["name"], "arguments": c["function"]["arguments"]}
                     for c in msg.get("tool_calls", [])]
            text = msg.get("content") or ""
            truncated = choice.get("finish_reason") == "length"
        else:
            headers.update({"x-api-key": self.key, "anthropic-version": "2023-06-01"})
            raw = self.transport(base + "/messages", headers, body)
            self.emit({"stage": "provider_response", "request_sequence": self.request_sequence, "body": raw})
            msg = {"role": "assistant", "content": raw["content"]}
            calls = [{"id": c["id"], "name": c["name"], "arguments": c["input"]}
                     for c in raw["content"] if c["type"] == "tool_use"]
            text = "\n".join(c["text"] for c in raw["content"] if c["type"] == "text")
            truncated = raw.get("stop_reason") == "max_tokens"
        if truncated:
            raise ProviderError("模型输出被截断；提高输出预算或缩小任务")
        return {"message": msg, "calls": calls, "text": text, "usage": raw.get("usage", {})}

    def add_results(self, messages, results):
        if self.protocol == "openai":
            messages.extend({"role": "tool", "tool_call_id": r["id"], "content": json.dumps(r["result"], ensure_ascii=False)} for r in results)
        else:
            messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": r["id"], "content": json.dumps(r["result"], ensure_ascii=False),
                 "is_error": bool(r["result"].get("error"))} for r in results]})
