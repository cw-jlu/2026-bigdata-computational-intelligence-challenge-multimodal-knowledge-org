from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path
from .analysis import analyze_seed
from .common import VERSION, append_json, day, digest, load_config, now, write_json
from .observability import experiment_directory, invocation_metadata, snapshot_code, summarize_trace
from .preprocess import preprocess
from .providers import Provider, ProviderError
from .report import create_narrative, deliver, report_packet
from .store import EvidenceTools, Store
from .trust import rank_events, review_event

LOG = logging.getLogger("workflow_agent")


def load_env(path):
    if not path:
        return
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError("环境文件必须使用 NAME=value")
        name, value = line.split("=", 1)
        name = name.strip()
        if not name or not all(c.isalnum() or c == "_" for c in name):
            raise ValueError("环境变量名不合法")
        os.environ.setdefault(name, value.strip().strip('"').strip("'"))


def export_state(store, out):
    for bucket in ("events", "coverage", "reviews", "event_revisions"):
        data = store.all(bucket)
        temp = Path(out) / (bucket + ".jsonl.tmp")
        with temp.open("w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        temp.replace(Path(out) / (bucket + ".jsonl"))


def execute(args):
    config = load_config(args.config)
    if args.trust_mode:
        config["trust_mode"] = args.trust_mode
    if not args.output:
        args.output = str(experiment_directory(config, getattr(args, "artifact_root", None) or Path(__file__).resolve().parents[2]))
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    snapshot_code(out)
    metadata = invocation_metadata(args)
    started = time.monotonic()
    write_json(out / "run_status.json", metadata)
    append_json(out / "invocations.jsonl", {"stage": "invocation_start", **metadata})
    handler = logging.FileHandler(out / "run.log", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s+08:00 %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    formatter.converter = lambda value: time.gmtime(value + 8 * 3600)
    handler.setFormatter(formatter)
    LOG.addHandler(handler)
    LOG.warning("本次结果目录：%s", out)
    try:
        result = _execute(args)
        metadata.update(status="completed", result=result)
        return result
    except Exception as exc:
        metadata.update(status="missing_input" if isinstance(exc, ValueError) and "数据目录不存在" in str(exc) else "failed",
                        error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        metadata.update(ended_at=now(), elapsed_seconds=time.monotonic() - started)
        write_json(out / "run_status.json", metadata)
        append_json(out / "invocations.jsonl", {"stage": "invocation_end", **metadata})
        summarize_trace(out)
        LOG.removeHandler(handler)
        handler.close()


def _execute(args):
    config = load_config(args.config)
    load_env(args.env_file)
    start, node = day(args.start).isoformat(), day(args.node).isoformat()
    if start > node:
        raise ValueError("start 不能晚于 node")
    if args.trust_mode:
        config["trust_mode"] = args.trust_mode
    if args.max_seeds is not None and args.max_seeds <= 0:
        raise ValueError("max-seeds 必须为正整数")
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    code = sorted(Path(__file__).parent.glob("*.py"))
    run_signature = digest([VERSION, config, start, node, [(p.name, digest(p.read_text(encoding="utf-8"))) for p in code]])
    meta_path = out / "run_config.json"
    if meta_path.exists():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        if old["signature"] != run_signature:
            raise ValueError("代码、配置或判定路线已改变，请指定新的输出目录做对照")
    write_json(meta_path, {"version": VERSION, "signature": run_signature, "config": config, "start": start, "node": node})
    db = Store(out / "state.sqlite")
    try:
        manifest = preprocess(args.input, db, start, node, out, config)
        LOG.info("预处理完成：%d条记录，%d组轨迹，%d项文件质量问题", manifest["records"], manifest["tracks"], len(manifest["issues"]))
        if args.stage == "prepare":
            return {"stage": "prepare", "records": manifest["records"], "issues": len(manifest["issues"])}
        evidence = EvidenceTools(db, start, node)
        trace = out / "traces.jsonl"
        required_roles = set()
        if args.stage in {"all", "analyze"}:
            required_roles.add("analysis")
        if args.stage in {"all", "review"}:
            required_roles |= {"risk"} if config["trust_mode"] == "risk" else {"support", "critic", "judge"}
        if args.stage in {"all", "report"}:
            required_roles.add("writer")
        providers = {role: Provider(config["providers"][config["roles"][role]], config) for role in required_roles}
        if args.stage in {"all", "analyze"}:
            processed = 0
            records = evidence.records()
            by_id = {r["id"]: r for r in records}
            seeds = [dict(r) for r in records if r["kind"] == "text" or not config.get("group_radar_seeds", True)]
            if config.get("group_radar_seeds", True):
                for track in db.all("tracks"):
                    ids = [rid for rid in track["record_ids"] if rid in by_id]
                    if ids:
                        seeds.append({**by_id[ids[0]], "group_record_ids": ids})
            LOG.info("本轮 %d 条输入安排为 %d 个调查任务，节点日优先", len(records), len(seeds))
            for seed in sorted(seeds, key=lambda r: (r["day"] != node, r["day"], r["id"])):
                if all(db.has("coverage", rid) and db.get("coverage", rid).get("complete") for rid in seed.get("group_record_ids", [seed["id"]])):
                    continue
                if args.max_seeds is not None and processed >= args.max_seeds:
                    break
                LOG.info("分析 %s %s", seed["day"], seed["id"])
                analyze_seed(providers["analysis"], config, evidence, seed, trace)
                processed += 1
                export_state(db, out)
        if args.stage in {"all", "review"}:
            for event in db.all("events"):
                LOG.info("可信判定 %s：%s", config["trust_mode"], event["event_id"])
                review_event(providers, config, evidence, event, trace)
                export_state(db, out)
            if config["trust_mode"] == "risk":
                for d in sorted({e["day"] for e in db.all("events")}):
                    ranked = rank_events(providers["risk"], config, evidence, [e for e in db.all("events") if e["day"] == d], trace)
                    write_json(out / "ranking" / f"{d}.json", ranked)
        coverage = {c["record_id"]: c for c in db.all("coverage")}
        uncovered = [r["id"] for r in evidence.records() if not coverage.get(r["id"], {}).get("complete")]
        events = db.all("events")
        counts = {status: sum(e.get("status") == status for e in events) for status in ("trusted", "pending", "excluded")}
        summary = {"stage": args.stage, "node": node, "records": manifest["records"], "events": counts,
                   "uncovered_records": uncovered, "quality_issues": len(manifest["issues"]), "report_generated": False}
        write_json(out / "summary.json", summary)
        if args.stage in {"all", "report"}:
            if uncovered:
                raise ValueError(f"尚有 {len(uncovered)} 条记录未完成调查；已保存检查点，可先续跑 analyze，再 review/report")
            if manifest["issues"]:
                raise ValueError("文件缺失或解析问题尚未解决，不能声称完整日报；见 quality.json")
            packet = report_packet(events, node)
            write_json(out / "report_packet.json", packet)
            narrative = create_narrative(providers["writer"], config, packet, trace)
            write_json(out / "narrative.json", narrative)
            deliver(packet, narrative, out)
            summary["report_generated"] = True
            write_json(out / "summary.json", summary)
        return summary
    finally:
        export_state(db, out)
        db.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Workflow + Agent 多源调查与日报生成")
    ap.add_argument("--input", required=True, help="原始数据根目录，含日期子目录")
    ap.add_argument("--start", required=True, help="允许读取的起始日期")
    ap.add_argument("--node", required=True, help="报告节点日期")
    ap.add_argument("--output", help="指定目录以续跑；默认 artifact/时间戳_方案版本_模型_可信路线")
    ap.add_argument("--artifact-root", help="自动命名目录的父目录，默认仓库 artifact")
    root = Path(__file__).resolve().parents[1]
    local = root / "config.local.json"
    ap.add_argument("--config", default=str(local if local.exists() else root / "config.example.json"))
    ap.add_argument("--env-file", default=str(root / ".env") if (root / ".env").exists() else None, help="可选本地 .env，不写入日志")
    ap.add_argument("--stage", choices=["prepare", "analyze", "review", "report", "all"], default="all")
    ap.add_argument("--trust-mode", choices=["risk", "debate"])
    ap.add_argument("--max-seeds", type=int, help="开发时限制本次调查记录数，未覆盖记录不冒充完整报告")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        result = execute(args)
    except (ValueError, ProviderError, KeyError) as exc:
        # Config errors contain no API values. Provider failures are sanitized.
        ap.exit(2, f"未完成：{exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
