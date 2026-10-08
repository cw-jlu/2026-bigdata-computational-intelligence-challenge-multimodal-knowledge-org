"""Structural and evidence gates; these do not prove semantic correctness."""
from __future__ import annotations

from datetime import datetime
from .common import CORE, RISKS, SOURCES, day

REF_SCHEMA = {"type": "object", "properties": {"record_id": {"type": "string"}, "quote": {"type": "string"}},
              "required": ["record_id", "quote"], "additionalProperties": False}
FIELD_SCHEMA = {"type": "object", "properties": {
    "value": {"type": ["string", "integer", "number", "null"]}, "risk": {"type": "string", "enum": sorted(RISKS)},
    "supports": {"type": "array", "items": REF_SCHEMA},
    "conflicts": {"type": "array", "items": {"type": "object", "properties": {
        "record_id": {"type": "string"}, "quote": {"type": "string"}, "resolved": {"type": "boolean"},
        "reason": {"type": "string"}, "resolution_refs": {"type": "array", "items": REF_SCHEMA}},
        "required": ["record_id", "quote", "resolved", "reason", "resolution_refs"], "additionalProperties": False}},
    "reason": {"type": "string"}}, "required": ["value", "risk", "supports", "conflicts", "reason"], "additionalProperties": False}
FIELDS = ["country", "platform", "count", "start", "end", "region", "direction", "task", "action", "base", "callsign", "batch", "longitude", "latitude"]
EVENT_SCHEMA = {"type": "object", "properties": {
    "event_id": {"type": "string"}, "day": {"type": "string", "description": "活动日期 YYYY-MM-DD"},
    "kind": {"type": "string", "enum": ["飞机", "舰船"]},
    "source_links": {"type": "array", "items": {"type": "object", "properties": {
        "record_id": {"type": "string"}, "reason": {"type": "string"}}, "required": ["record_id", "reason"], "additionalProperties": False}},
    "fields": {"type": "object", "properties": {k: FIELD_SCHEMA for k in FIELDS}, "additionalProperties": False},
    "unresolved_issues": {"type": "array", "items": {"type": "string"}},
    "anomaly_handling": {"type": "array", "items": {"type": "object", "properties": {
        "record_id": {"type": "string"}, "flag": {"type": "string"}, "reason": {"type": "string"},
        "resolution_refs": {"type": "array", "items": REF_SCHEMA}},
        "required": ["record_id", "flag", "reason", "resolution_refs"], "additionalProperties": False}},
    "boundary_reason": {"type": "string", "description": "说明同一事件关联及与已有事件的合并/拆分边界"}},
    "required": ["day", "kind", "source_links", "fields", "unresolved_issues", "anomaly_handling", "boundary_reason"], "additionalProperties": False}


def validate_schema(value, schema, path="input"):
    types = schema.get("type")
    choices = types if isinstance(types, list) else [types]
    matches = {"object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str),
               "integer": isinstance(value, int) and not isinstance(value, bool),
               "number": isinstance(value, (int, float)) and not isinstance(value, bool),
               "boolean": isinstance(value, bool), "null": value is None}
    if types and not any(matches.get(t, False) for t in choices):
        raise ValueError(f"{path}: 类型必须为 {types}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: 值不在允许集合")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        missing = set(schema.get("required", [])) - value.keys()
        if missing:
            raise ValueError(f"{path}: 缺少 {sorted(missing)}")
        if schema.get("additionalProperties") is False and value.keys() - properties.keys():
            raise ValueError(f"{path}: 存在未知字段 {sorted(value.keys() - properties.keys())}")
        for k, v in value.items():
            if k in properties:
                validate_schema(v, properties[k], path + "." + k)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            validate_schema(item, schema.get("items", {}), f"{path}[{i}]")


def evidence_record(ref, tools):
    r = tools.store.get("records", ref["record_id"])
    if not tools.start <= r["day"] <= tools.node:
        raise ValueError("证据超出时间边界")
    quote = ref.get("quote", "")
    if not quote.strip() or quote not in r["raw"]:
        raise ValueError(f"{r['id']}: 引文不在原始记录中")
    return r


def check_event(event, tools, config, reviewed=False):
    validate_schema(event, EVENT_SCHEMA)
    if not tools.start <= event["day"] <= tools.node or day(event["day"]).isoformat() != event["day"]:
        raise ValueError("事件活动日期超出边界或格式不合法")
    links = event["source_links"]
    if not links or not event["boundary_reason"].strip() or any(not x["reason"].strip() for x in links):
        raise ValueError("必须说明来源关联与事件边界")
    linked = {}
    for link in links:
        r = tools.store.get("records", link["record_id"])
        if not tools.start <= r["day"] <= tools.node:
            raise ValueError("来源关联越界")
        linked[r["id"]] = r
    def refcheck(ref):
        r = evidence_record(ref, tools)
        if r["id"] not in linked:
            raise ValueError("字段证据必须在 source_links 中")
        return r
    issues = []
    fields = event["fields"]
    for name, field in fields.items():
        for ref in field["supports"]:
            refcheck(ref)
        for conflict in field["conflicts"]:
            refcheck(conflict)
            for ref in conflict["resolution_refs"]:
                refcheck(ref)
            if not conflict["resolved"]:
                issues.append(f"{name}: 未解决冲突")
            elif not conflict["reason"].strip() or not conflict["resolution_refs"]:
                issues.append(f"{name}: 冲突消解缺少依据")
    handled = {}
    for item in event["anomaly_handling"]:
        if item["record_id"] not in linked:
            raise ValueError("异常记录必须在 source_links 中")
        for ref in item["resolution_refs"]:
            refcheck(ref)
        if item["reason"].strip() and item["resolution_refs"]:
            handled[(item["record_id"], item["flag"])] = item
    for rid, r in linked.items():
        flags = list(r.get("flags", []))
        if r.get("track_id"):
            flags += tools.store.get("tracks", r["track_id"]).get("flags", [])
        for flag in flags:
            if (rid, flag) not in handled:
                issues.append(f"{rid}: 异常待解释 {flag}")
    if {r["source"] for r in linked.values()} != SOURCES:
        issues.append("三类来源未齐全")
    for name in config["required_fields"]:
        field = fields.get(name)
        if not field or field.get("value") in (None, ""):
            issues.append(f"{name}: 关键字段缺失")
            continue
        supports = [refcheck(ref) for ref in field["supports"]]
        if len({r["source"] for r in supports}) < 2 or len({r["duplicate_group"] for r in supports}) < 2:
            issues.append(f"{name}: 不足两类且非精确复制的来源支持")
        if field["risk"] != "low":
            issues.append(f"{name}: 风险未降至 low")
    count = fields.get("count", {}).get("value")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        issues.append("数量不是正整数精确值")
    try:
        start = datetime.fromisoformat(str(fields.get("start", {}).get("value")))
        end = datetime.fromisoformat(str(fields.get("end", {}).get("value")))
        if start.date().isoformat() != event["day"] or end < start:
            issues.append("活动时间与日期不一致或逆序")
        if end.date().isoformat() > tools.node:
            issues.append("结束时间越过节点")
    except (ValueError, TypeError):
        issues.append("活动时间缺少完整日期或时区不一致")
    if fields.get("direction", {}).get("value") not in CORE:
        issues.append("非三海方向或方向未确定")
    issues.extend(event["unresolved_issues"])
    if not reviewed:
        issues.append("尚未完成可信判定")
    return {"eligible": not issues, "issues": sorted(set(issues)), "semantic_verification": "model_judgement_requires_evaluation"}
