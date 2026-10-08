from __future__ import annotations

import json
import time
import uuid
from .common import append_json, dumps


class BudgetExceeded(RuntimeError):
    pass


def tool(name, description, properties, required=None):
    return {"name": name, "description": description, "parameters": {
        "type": "object", "properties": properties, "required": required or [], "additionalProperties": False}}


def run_agent(provider, settings, system, task, specs, handlers, trace_path, task_id, stop_when=None):
    task_run_id = uuid.uuid4().hex
    started = time.monotonic()
    previous_audit = getattr(provider, "audit", None)
    def record(event):
        append_json(trace_path, {"task": task_id, "task_run_id": task_run_id, "role": task_id.split(":", 1)[0],
                                 "provider": provider.config.get("model"), **event})
    provider.audit = record
    record({"stage": "start", "system": system, "input": task, "tools": specs,
            "budgets": {k: settings[k] for k in ("max_turns", "max_tool_calls", "max_output_tokens", "max_context_chars")}})
    try:
        result = _run(provider, settings, system, task, specs, handlers, record, stop_when)
        record({"stage": "task_end", "status": "returned", "latency_seconds": time.monotonic() - started})
        return result
    except Exception as exc:
        record({"stage": "task_end", "status": "failed", "error_type": type(exc).__name__, "error": str(exc),
                "latency_seconds": time.monotonic() - started})
        raise
    finally:
        provider.audit = previous_audit


def _run(provider, settings, system, task, specs, handlers, record, stop_when=None):
    from .validation import validate_schema
    messages = [{"role": "user", "content": task}]
    schemas = {t["name"]: t["parameters"] for t in specs}
    calls_used = 0
    for turn in range(settings["max_turns"]):
        if len(system) + len(dumps(messages)) > settings["max_context_chars"]:
            raise BudgetExceeded("上下文预算已到；保留已提交结果，剩余记录待审")
        started = time.monotonic()
        record({"stage": "model_request", "turn": turn, "messages": messages})
        reply = provider.complete(system, messages, specs)
        record({"stage": "model_response", "turn": turn, "assistant": reply["message"], "usage": reply["usage"],
                "request_sequence": getattr(provider, "request_sequence", None), "latency_seconds": time.monotonic() - started})
        messages.append(reply["message"])
        if not reply["calls"]:
            return reply["text"]
        results = []
        for call in reply["calls"]:
            tool_started = time.monotonic()
            calls_used += 1
            if calls_used > settings["max_tool_calls"]:
                raise BudgetExceeded("工具调用预算已到；未完成内容待审")
            try:
                args = json.loads(call["arguments"]) if isinstance(call["arguments"], str) else call["arguments"]
                if not isinstance(args, dict):
                    raise ValueError("工具参数必须为对象")
                if call["name"] not in handlers:
                    raise ValueError("未授权的工具")
                validate_schema(args, schemas[call["name"]])
                result = handlers[call["name"]](**args)
            except (ValueError, TypeError, KeyError) as exc:
                result = {"error": str(exc)}
            if not isinstance(result, dict):
                result = {"data": result}
            results.append({"id": call["id"], "result": result})
            record({"stage": "tool_result", "turn": turn, "call_id": call["id"], "tool": call["name"],
                    "arguments": call["arguments"], "result": result, "latency_seconds": time.monotonic() - tool_started})
        provider.add_results(messages, results)
        if stop_when is not None and stop_when():
            return reply["text"]
    raise BudgetExceeded("模型轮数预算已到；未完成内容待审")
