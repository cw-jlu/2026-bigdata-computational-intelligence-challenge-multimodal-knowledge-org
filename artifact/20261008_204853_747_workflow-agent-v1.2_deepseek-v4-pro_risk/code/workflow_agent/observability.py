from __future__ import annotations

import json
import platform
import re
import shutil
import uuid
from collections import Counter, defaultdict
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from .common import VERSION, now, write_json


def experiment_directory(config, artifact_root):
    names = {config["providers"][provider]["model"] for role, provider in config["roles"].items()
             if config["providers"][provider].get("model") and (config["trust_mode"] == "debate" or role not in {"critic", "support", "judge"})}
    model = "-".join(sorted(names)) or "model-unconfigured"
    label = re.sub(r"[^A-Za-z0-9_.-]+", "-", f"{VERSION}_{model}_{config['trust_mode']}")
    stamp = now().split("+", 1)[0].replace("-", "").replace(":", "").replace("T", "_").replace(".", "_")
    return Path(artifact_root).resolve() / f"{stamp}_{label}"


def snapshot_code(out):
    root = Path(__file__).resolve().parents[1]
    files = list((root / "workflow_agent").glob("*.py")) + list((root / "tests").glob("*.py"))
    files += [root / name for name in ("run.py", "requirements.txt", "README.md", "config.example.json")]
    for file in files:
        target = Path(out) / "code" / file.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(file, target)


def invocation_metadata(args):
    packages = {}
    for name in ("openpyxl", "python-docx", "matplotlib"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = "not-installed"
    return {"invocation_id": uuid.uuid4().hex, "started_at": now(), "status": "running", "version": VERSION,
            "input": str(Path(args.input).resolve()), "stage": args.stage, "start": args.start, "node": args.node,
            "max_seeds": args.max_seeds, "python": platform.python_version(), "platform": platform.platform(), "packages": packages}


def summarize_trace(out):
    path = Path(out) / "traces.jsonl"
    calls, failures, tools, tool_errors, retries = Counter(), Counter(), Counter(), Counter(), 0
    tokens, latency = defaultdict(Counter), defaultdict(list)
    usage_seen = set()
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                role = e.get("role", "unknown")
                if e.get("stage") in {"provider_response", "model_response"}:
                    identity = (e.get("task_run_id"), e.get("request_sequence") if e.get("request_sequence") is not None else e.get("turn"))
                    usage = e.get("body", {}).get("usage", {}) if e["stage"] == "provider_response" else e.get("usage", {})
                    if usage and identity not in usage_seen:
                        usage_seen.add(identity)
                        tokens[role]["input_tokens"] += usage.get("prompt_tokens", usage.get("input_tokens", 0))
                        tokens[role]["output_tokens"] += usage.get("completion_tokens", usage.get("output_tokens", 0))
                        tokens[role]["cache_hit_tokens"] += usage.get("prompt_cache_hit_tokens", usage.get("cache_read_input_tokens", 0))
                        tokens[role]["cache_creation_tokens"] += usage.get("cache_creation_input_tokens", 0)
                if e.get("stage") == "model_response":
                    calls[role] += 1
                    latency[role].append(e.get("latency_seconds", 0))
                elif e.get("stage") == "task_end" and e.get("status") == "failed":
                    failures[e.get("error_type", "unknown")] += 1
                elif e.get("stage") == "tool_result":
                    tools[e["tool"]] += 1
                    if e.get("result", {}).get("error"):
                        tool_errors[e["tool"]] += 1
                elif e.get("stage") == "http_attempt" and e.get("attempt", 1) > 1:
                    retries += 1
    data = {"model_calls_by_role": dict(calls), "tokens_by_role": {r: dict(v) for r, v in tokens.items()},
            "tool_calls": dict(tools), "tool_errors": dict(tool_errors), "failed_tasks": dict(failures), "http_retries": retries,
            "mean_model_latency_seconds": {r: sum(v) / len(v) for r, v in latency.items()},
            "usage_limits": "包含已返回 usage 的截断响应；超时且未返回 usage 的请求用量未知",
            "pricing": "未填价格，仅记录用量，不估算费用"}
    write_json(Path(out) / "trace_summary.json", data)
    return data
