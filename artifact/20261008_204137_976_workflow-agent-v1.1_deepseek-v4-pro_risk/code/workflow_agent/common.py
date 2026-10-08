from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

VERSION = "workflow-agent-v1.1"
SOURCES = {"开源军情", "网上舆论", "雷达信息"}
RISKS = {"low", "medium", "high", "unknown"}
CORE = {"东海", "南海", "黄海"}
_SECRETS = set()


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="milliseconds")


def register_secret(value):
    if value:
        _SECRETS.add(value)


def redact(value):
    secrets = _SECRETS | {v for k, v in os.environ.items() if k.endswith("API_KEY") and v}
    if isinstance(value, str):
        for secret in sorted(secrets, key=len, reverse=True):
            value = value.replace(secret, "[REDACTED]")
        return value
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def dumps(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def digest(value):
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()


def day(value):
    return date.fromisoformat(str(value).replace(".", "-")) if "-" in str(value) else date(*map(int, str(value).split(".")))


def timestamp(value):
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value or "").strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text).isoformat()
    except ValueError:
        return None


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(redact(value), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def append_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(dumps(redact({"timestamp": now(), **value})) + "\n")


def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    def check_no_secrets(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if k.casefold() in {"api_key", "apikey", "authorization", "x-api-key", "access_token"}:
                    raise ValueError("配置文件不得放密钥；使用 api_key_env 和本地环境变量")
                check_no_secrets(v)
        elif isinstance(value, list):
            for item in value:
                check_no_secrets(item)
    check_no_secrets(cfg)
    if cfg["trust_mode"] not in {"risk", "debate"}:
        raise ValueError("trust_mode 必须是 risk 或 debate")
    for key in ("max_turns", "max_tool_calls", "max_output_tokens", "max_context_chars"):
        if not isinstance(cfg[key], int) or cfg[key] <= 0:
            raise ValueError(f"{key} 必须是正整数")
    if not cfg.get("required_fields") or set(cfg["required_fields"]) - {"country", "platform", "count", "start", "end", "region", "direction", "task"}:
        raise ValueError("required_fields 必须为已定义的关键字段列表")
    return cfg
