"""端到端流水线：原始 TXT/XLSX -> 中间结果 -> 各节点 DOCX/XLSX/PNG。

用法：
    python run.py --input <数据目录> --output <输出目录> [--stage prelim|semifinal] [--nodes 2025.5.10 ...]
"""
from __future__ import annotations

import argparse
import json
import logging
import time
import zipfile
from dataclasses import asdict
from pathlib import Path

from . import charts, lexicon as L
from .extract import extract_mentions, parse_day, read_day_docs
from .fusion import Event, conflict_summary, link_day
from .radar import load_radar
from .report import FIG_NAMES, cn_date, write_docx, write_xlsx
from .tracking import build_mainline

NODES = {
    "prelim": ["2025.5.10", "2025.5.18", "2025.5.30", "2025.6.9", "2025.6.17", "2025.6.29", "2025.7.9", "2025.7.17"],
    "semifinal": ["2025.7.27", "2025.8.6", "2025.8.18", "2025.8.26", "2025.9.5", "2025.9.17", "2025.9.27"],
}
STAGE_START = {"prelim": "2025.5.1", "semifinal": "2025.7.20"}
SECTIONS = ["当日活动总览", "一、重要军事动向", "二、重点态势分析", "三、外（台）机舰活动情况", "四、美重要武器平台部署情况",
            "五、次日关注重点"]

log = logging.getLogger("bdci")


def process_day(day_dir: Path) -> tuple[list[Event], dict]:
    day = day_dir.name
    docs = read_day_docs(day_dir)
    mentions = [m for d in docs for m in extract_mentions(d)]
    xlsx = next(day_dir.glob("*.xlsx"), None)
    tracks = load_radar(xlsx, day) if xlsx else []
    events = link_day(day, tracks, mentions)
    return events, {"docs": docs, "mentions": mentions, "tracks": tracks}


def event_record(e: Event) -> dict:
    def mention(m):
        if m is None:
            return None
        return {"doc_id": m.doc_id, "mention_id": m.mention_id, "title": m.evidence, "country": m.country,
                "platform": m.platform or list(m.candidates) or list(m.fuzzy_cats), "count": m.count, "region": m.region,
                "start": m.start, "end": m.end, "task": m.task, "action": m.action}
    t = e.track
    track = None
    if t is not None:
        a = t.alts[e.alt_index]
        track = {"sheet": t.sheet, "batch": t.batch, "country": t.country, "platform": t.platform, "task": t.task,
                 "count": t.count, "start": a.start, "end": a.end, "region": a.region,
                 "lonlat": [round(a.lon, 4), round(a.lat, 4)] if a.lon is not None else None,
                 "excel_rows": a.rows, "alternatives": [{"region": x.region, "rows": x.rows} for x in t.alts],
                 "base": t.base, "hull": t.hull}
    return {
        "event_id": e.event_id, "day": e.day, "kind": e.kind, "status": e.status, "in_core": e.in_core,
        "sources": e.sources, "link_scores": e.link_scores,
        "fields": {k: {"value": f.value, "support": f.support, "conflicts": f.conflicts, "note": f.note}
                   for k, f in e.fields.items()},
        "conflict_handling": conflict_summary(e), "radar_anomalies": e.anomalies, "exclude_reasons": e.reasons,
        "radar": track, "open_source": mention(e.o), "public_opinion": mention(e.p),
    }


def dump_intermediate(day: str, events: list[Event], extra: dict, out: Path) -> None:
    d = out / "中间结果" / day
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "events.jsonl", "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(event_record(e), ensure_ascii=False, default=str) + "\n")
    with open(d / "mentions.jsonl", "w", encoding="utf-8") as f:
        docs = {doc.doc_id: doc.path for doc in extra["docs"]}
        for m in extra["mentions"]:
            r = asdict(m)
            r["path"] = docs.get(m.doc_id, "")
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    with open(d / "tracks.jsonl", "w", encoding="utf-8") as f:
        for t in extra["tracks"]:
            f.write(json.dumps(asdict(t), ensure_ascii=False, default=str) + "\n")


def build_node(node: str, events_by_day: dict[str, list[Event]], out: Path) -> dict:
    events = events_by_day[node]
    core = [e for e in events if e.in_core]
    node_dir = out / node / "日报"
    fig_dir = node_dir / "附件图表"
    fig_dir.mkdir(parents=True, exist_ok=True)
    md = cn_date(node)
    charts.hourly_curve(core, f"图1 {md}舰机侦巡数量曲线图（三海方向，按小时）", fig_dir / FIG_NAMES[0])
    charts.activity_map([e for e in core if e.get("country") == "中国"], f"图2 {md}中国主要机舰活动示意图",
                        fig_dir / FIG_NAMES[1])
    charts.activity_map([e for e in core if e.get("country") == "美国"], f"图3 {md}美国主要机舰活动示意图",
                        fig_dir / FIG_NAMES[2])
    charts.activity_map([e for e in core if e.get("country") not in ("中国", "美国")],
                        f"图4 {md}其他国家（地区）主要机舰活动示意图", fig_dir / FIG_NAMES[3], color_by_country=True)
    ml = build_mainline(node, {d: evs for d, evs in events_by_day.items() if parse_day(d) <= parse_day(node)})
    write_xlsx(node, core, node_dir / f"{node}机舰活动明细.xlsx")
    write_docx(node, core, events, ml, fig_dir, node_dir / f"{node}日报.docx")
    mainline = None
    if ml:
        mainline = {"country": ml.country, "platform": ml.platform, "pattern": ml.pattern, "judgement": ml.judgement,
                    "dates": [str(d) for d in ml.days],
                    "phases": [{"start": str(p.start), "end": str(p.end), "dates": [str(d) for d in p.days],
                                "regions": p.regions, "events": [e.event_id for e in p.events]} for p in ml.phases]}
    with open(out / node / "mainline.json", "w", encoding="utf-8") as f:
        json.dump(mainline, f, ensure_ascii=False, indent=2)
    with zipfile.ZipFile(out / node / f"{node}日报.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(node_dir.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(out / node))
    return {"node": node, "core_events": len(core), "air": sum(e.kind == "飞机" for e in core),
            "ship": sum(e.kind != "飞机" for e in core), "excluded": sum(not e.credible for e in events),
            "mainline": f"{ml.country}{ml.platform}" if ml else None}


def validate_node(node: str, out: Path) -> dict:
    from docx import Document
    from openpyxl import load_workbook
    from PIL import Image

    from .report import AIR_COLS, SHIP_COLS
    node_dir = out / node / "日报"
    res = {"node": node, "ok": True, "checks": []}

    def check(name, cond, detail=""):
        res["checks"].append({"check": name, "pass": bool(cond), "detail": detail})
        res["ok"] &= bool(cond)

    docx_p = node_dir / f"{node}日报.docx"
    try:
        doc = Document(docx_p)
        text = [p.text for p in doc.paragraphs]
        check("docx标题", text and text[0] == f"{cn_date(node)}飞机舰船活动情况", text[0] if text else "")
        for s in SECTIONS:
            check(f"docx章节:{s}", s in text)
        body = "\n".join(text)
        for i in range(1, 5):
            check(f"docx引用附图{i}", f"附图{i}" in body or f"图{i}" in body)
    except Exception as ex:  # noqa: BLE001
        check("docx可打开", False, repr(ex))
    try:
        wb = load_workbook(node_dir / f"{node}机舰活动明细.xlsx")
        check("xlsx工作表", wb.sheetnames == ["飞机", "舰艇"], str(wb.sheetnames))
        check("飞机表字段", [c.value for c in wb["飞机"][1]] == AIR_COLS)
        check("舰艇表字段", [c.value for c in wb["舰艇"][1]] == SHIP_COLS)
    except Exception as ex:  # noqa: BLE001
        check("xlsx可打开", False, repr(ex))
    for fn in FIG_NAMES:
        p = node_dir / "附件图表" / fn
        try:
            with Image.open(p) as im:
                im.verify()
            check(f"png:{fn}", True)
        except Exception as ex:  # noqa: BLE001
            check(f"png:{fn}", False, repr(ex))
    check("png数量", len(list((node_dir / "附件图表").glob("*.png"))) == 4)
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="多模态融合的知识组织与决策生成 · 节点日报生成")
    ap.add_argument("--input", required=True, help="数据目录（包含 2025.5.1 等日期子目录）")
    ap.add_argument("--output", default="output", help="输出目录")
    ap.add_argument("--stage", default="prelim", choices=list(NODES))
    ap.add_argument("--nodes", nargs="*", help="指定节点（默认使用赛段全部节点）")
    args = ap.parse_args(argv)

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(out / "run.log", encoding="utf-8", mode="w"), logging.StreamHandler()])
    data = Path(args.input)
    nodes = args.nodes or NODES[args.stage]
    start = parse_day(STAGE_START[args.stage])
    last = max(parse_day(n) for n in nodes)
    day_dirs = sorted((p for p in data.iterdir() if p.is_dir() and p.name.count(".") == 2), key=lambda p: parse_day(p.name))
    day_dirs = [p for p in day_dirs if start <= parse_day(p.name) <= last]
    t0 = time.time()
    events_by_day: dict[str, list[Event]] = {}
    for p in day_dirs:
        try:
            events, extra = process_day(p)
        except Exception:  # noqa: BLE001
            log.exception("处理 %s 失败，跳过该日", p.name)
            continue
        events_by_day[p.name] = events
        dump_intermediate(p.name, events, extra, out)
        core = sum(e.in_core for e in events)
        log.info("%s 候选事件%d 可信%d 三海可信%d", p.name, len(events), sum(e.credible for e in events), core)
    summary, validation = [], []
    for n in nodes:
        if n not in events_by_day:
            log.error("节点 %s 无数据", n)
            continue
        summary.append(build_node(n, events_by_day, out))
        validation.append(validate_node(n, out))
        log.info("节点 %s 完成：%s", n, summary[-1])
    with open(out / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(out / "validation.json", "w", encoding="utf-8") as f:
        json.dump(validation, f, ensure_ascii=False, indent=2)
    log.info("全部完成，用时 %.1fs；交付自检 %s", time.time() - t0,
             "全部通过" if all(v["ok"] for v in validation) else "存在未通过项，见 validation.json")
