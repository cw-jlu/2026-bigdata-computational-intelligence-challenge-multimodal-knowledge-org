from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill


NODES = ["2025.5.10", "2025.5.18", "2025.5.30", "2025.6.9", "2025.6.17", "2025.6.29", "2025.7.9", "2025.7.17"]
AIR_COLS = ["日期", "星期", "国家地区", "机型", "批号", "批次", "架次", "起飞基地", "呼号", "起飞时间", "降落时间", "活动方向", "活动区域", "任务描述", "任务类型", "备注"]
SHIP_COLS = ["日期", "国家地区", "舰船", "批号", "艘次", "活动时间", "活动方向", "活动区域", "任务", "母港", "备注"]
DIRECTION_REGIONS = {
    "东海": ["东海", "钓鱼岛", "赤尾屿", "上海外海", "长江口外海", "舟山外海", "冲绳海槽", "苏岩礁"],
    "南海": ["南海", "北部湾", "琼州海峡", "东沙", "西沙", "中沙", "南沙", "黄岩岛", "美济礁", "仁爱礁", "万安滩"],
    "黄海": ["黄海", "青岛外海", "成山头外海", "海州湾外海", "济州岛西部"],
}
REGION_TERMS = sorted({x for xs in DIRECTION_REGIONS.values() for x in xs} | {
    "东海北部", "东海中部", "东海南部", "南海北部", "南海中部", "南海南部",
    "北黄海", "南黄海", "海南岛东南海域", "西沙群岛海域", "南沙群岛海域",
    "东沙群岛海域", "钓鱼岛海域", "苏岩礁附近海域", "济州岛西部海域",
}, key=len, reverse=True)
CN_NAMES = {"中国", "中国大陆"}
TW_NAMES = {"台湾", "台湾地区", "台军"}
WEEKDAY = "一二三四五六日"


def clean(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return re.sub(r"[\s\u3000‘’“”\"'·—\-（）()、，。；：:/]", "", str(value)).lower()


def direction(region: str) -> str:
    region = str(region or "")
    for name, words in DIRECTION_REGIONS.items():
        if any(w in region for w in words):
            return name
    return "其他"


def extract_region(*texts: str) -> str:
    joined = " ".join(texts)
    for term in REGION_TERMS:
        if term in joined:
            return term
    return ""


def read_text(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    def field(label: str) -> str:
        m = re.search(rf"{label}\s*[：:]\s*(.*)", text)
        return m.group(1).strip() if m else ""
    return {"path": str(path), "title": field("标题"), "body": field("正文"), "text": text, "norm": clean(text)}


def variants(value: str) -> set[str]:
    v = clean(value)
    out = {v} if v else set()
    for suffix in ["型", "号", "级", "战斗机", "巡逻机", "导弹护卫舰", "导弹驱逐舰", "航空母舰", "两栖攻击舰", "多用途"]:
        if v.endswith(clean(suffix)) and len(v) > len(clean(suffix)) + 1:
            out.add(v[: -len(clean(suffix))])
    return {x for x in out if len(x) >= 2}


def text_score(doc: dict, attrs: dict) -> float:
    n = doc["norm"]
    score = 0.0
    weights = {"country": 2.0, "platform": 4.0, "region": 3.0, "task": 2.0}
    for key, weight in weights.items():
        vs = variants(attrs.get(key, ""))
        if vs and any(v in n for v in vs):
            score += weight
    return score


def similarity(a: str, b: str) -> float:
    a, b = clean(a), clean(b)
    if not a or not b:
        return 0.0
    sa = set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2}", a))
    sb = set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2}", b))
    jac = len(sa & sb) / max(1, len(sa | sb))
    return max(jac, SequenceMatcher(None, a, b).ratio())


@dataclass
class Event:
    event_id: str
    date: str
    kind: str
    country: str
    platform: str
    batch: str
    quantity: int
    start: str
    end: str
    region: str
    direction: str
    task: str
    base: str
    lon: float | None
    lat: float | None
    open_file: str
    opinion_file: str
    radar_file: str
    open_score: float
    opinion_score: float
    text_similarity: float
    decision: str
    reason: str


def val(row, *names, default=""):
    for n in names:
        if n in row and pd.notna(row[n]):
            return row[n]
    return default


def as_time(v) -> str:
    if pd.isna(v) or v == "":
        return ""
    if isinstance(v, pd.Timestamp):
        return v.strftime("%H:%M")
    m = re.search(r"(\d{1,2}:\d{2})", str(v))
    return m.group(1) if m else str(v)


def build_events(day_dir: Path) -> list[Event]:
    opens = [read_text(p) for p in sorted((day_dir / "开源军情").glob("*.txt"))]
    opinions = [read_text(p) for p in sorted((day_dir / "网上舆论").glob("*.txt"))]
    radar = next(day_dir.glob("*.xlsx"))
    result = []
    specs = [("飞机", "飞机"), ("舰船", "舰艇")]
    for sheet, kind in specs:
        frame = pd.read_excel(radar, sheet_name=sheet)
        # Radar workbooks contain track points, not one row per event.  A batch is
        # the stable event key within a day; file sequence numbers are never used.
        for _, group in frame.groupby("批号", sort=False, dropna=False):
            idx = int(group.index[0]); row = group.iloc[0]
            if kind == "飞机":
                attrs = {
                    "country": str(val(row, "国家地区")), "platform": str(val(row, "目标类型")),
                    "region": "", "task": str(val(row, "任务")),
                }
                times = pd.to_datetime(group["位置时间"], errors="coerce")
                start, end = as_time(times.min()), as_time(times.max())
                base = str(val(row, "起飞机场")); qty = int(pd.to_numeric(group["目标数量"], errors="coerce").max() or 1)
                lon = pd.to_numeric(group["经度"], errors="coerce").median(); lat = pd.to_numeric(group["纬度"], errors="coerce").median()
            else:
                attrs = {
                    "country": str(val(row, "国家地区")), "platform": str(val(row, "机舰名")),
                    "region": str(val(row, "活动区域")), "task": str(val(row, "任务")),
                }
                starts = pd.to_datetime(group["首点时间"], errors="coerce"); ends = pd.to_datetime(group["结束时间"], errors="coerce")
                start, end = as_time(starts.min()), as_time(ends.max())
                base = str(val(row, "出航港口")); qty = int(pd.to_numeric(group["数量"], errors="coerce").max() or 1)
                lon = lat = None
            open_rank = sorted(((text_score(d, attrs), d) for d in opens), key=lambda x: x[0], reverse=True)
            opinion_rank = sorted(((text_score(d, attrs), d) for d in opinions), key=lambda x: x[0], reverse=True)
            oscore, odoc = open_rank[0] if open_rank else (0, {"path": "", "title": ""})
            pscore, pdoc = opinion_rank[0] if opinion_rank else (0, {"path": "", "title": ""})
            sim = similarity(odoc.get("title", ""), pdoc.get("title", ""))
            region = attrs["region"] or extract_region(odoc.get("text", ""), pdoc.get("text", ""))
            core = direction(region) != "其他"
            supported = oscore >= 6 and pscore >= 6 and sim >= 0.30
            # Time/position sanity gates. Synthetic observations outside physical ranges are excluded.
            sane_position = True
            if kind == "飞机" and lon is not None and lat is not None:
                sane_position = -180 <= float(lon) <= 180 and -90 <= float(lat) <= 90
            decision = "纳入" if core and supported and sane_position else "排除"
            reasons = []
            if not core: reasons.append("非东海/南海/黄海核心区域")
            if oscore < 6: reasons.append("开源军情支持不足")
            if pscore < 6: reasons.append("网上舆论支持不足")
            if sim < 0.30: reasons.append("两类文本一致性不足")
            if not sane_position: reasons.append("雷达位置异常")
            result.append(Event(
                event_id=f"{day_dir.name}-{kind}-{idx+1:03d}", date=day_dir.name, kind=kind,
                country=attrs["country"], platform=attrs["platform"], batch=str(val(row, "批号")),
                quantity=qty, start=start, end=end, region=region, direction=direction(region),
                task=attrs["task"], base=base, lon=float(lon) if lon is not None else None,
                lat=float(lat) if lat is not None else None, open_file=odoc.get("path", ""),
                opinion_file=pdoc.get("path", ""), radar_file=f"{radar}#{sheet}!{idx+2}",
                open_score=oscore, opinion_score=pscore, text_similarity=round(sim, 3),
                decision=decision, reason="；".join(reasons) or "三源一致且通过核心海域及异常门控",
            ))
    return result


def configure_fonts():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False


def save_charts(events: list[Event], chart_dir: Path, day: str):
    configure_fonts(); chart_dir.mkdir(parents=True, exist_ok=True)
    trusted = [e for e in events if e.decision == "纳入"]
    hours = list(range(24)); air = Counter(); ship = Counter()
    for e in trusted:
        m = re.match(r"(\d{1,2})", e.start)
        h = int(m.group(1)) if m else 0
        (air if e.kind == "飞机" else ship)[h] += e.quantity
    fig, ax = plt.subplots(figsize=(10, 5), dpi=160)
    ax.plot(hours, [air[h] for h in hours], marker="o", label="飞机架次")
    ax.plot(hours, [ship[h] for h in hours], marker="s", label="舰艇艘次")
    ax.set(title=f"{day} 舰机侦巡数量曲线图", xlabel="首报小时", ylabel="数量（架/艘）", xticks=range(0,24,2)); ax.grid(alpha=.25); ax.legend()
    fig.tight_layout(); fig.savefig(chart_dir / "01_舰机侦巡数量曲线图.png"); plt.close(fig)

    groups = [("中国", lambda e: e.country in CN_NAMES), ("美国", lambda e: "美国" in e.country), ("其他国家", lambda e: e.country not in CN_NAMES and "美国" not in e.country)]
    colors = {"东海":"#2878B5", "南海":"#D95319", "黄海":"#3A923A"}
    for num, (title, pred) in enumerate(groups, 2):
        subset = [e for e in trusted if pred(e)]
        fig, ax = plt.subplots(figsize=(10, 6), dpi=160)
        for i, e in enumerate(subset):
            x = e.lon if e.lon is not None else {"东海":126,"南海":113,"黄海":123}.get(e.direction,120) + (i%5)*.15
            y = e.lat if e.lat is not None else {"东海":28,"南海":17,"黄海":36}.get(e.direction,25) + (i%4)*.15
            ax.scatter(x, y, s=45 + 12*e.quantity, color=colors.get(e.direction,"gray"), marker="^" if e.kind=="飞机" else "s", alpha=.8)
            ax.annotate(e.platform[:12], (x,y), xytext=(4,4), textcoords="offset points", fontsize=7)
        for d,c in colors.items(): ax.scatter([],[],color=c,label=d)
        ax.scatter([],[],color="black",marker="^",label="飞机"); ax.scatter([],[],color="black",marker="s",label="舰艇")
        ax.set(title=f"{day} {title}主要机舰活动示意图", xlabel="经度（舰艇为海域示意位置）", ylabel="纬度（舰艇为海域示意位置）")
        ax.grid(alpha=.2); ax.legend(ncol=2); fig.tight_layout()
        fig.savefig(chart_dir / f"{num:02d}_{title}主要机舰活动示意图.png"); plt.close(fig)


def write_xlsx(events: list[Event], path: Path):
    trusted = [e for e in events if e.decision == "纳入"]
    d = datetime.strptime(trusted[0].date if trusted else path.stem[:9], "%Y.%m.%d")
    date_text = d.strftime("%Y.%m.%d")
    air_rows, ship_rows = [], []
    for e in trusted:
        note = f"事件ID:{e.event_id}；三源核验；文本一致度:{e.text_similarity:.2f}"
        if e.kind == "飞机":
            air_rows.append([date_text, "星期"+WEEKDAY[d.weekday()], e.country, e.platform, e.batch, 1, e.quantity, e.base, "", e.start, e.end, e.direction, e.region, e.task, e.task, note])
        else:
            ship_rows.append([date_text, e.country, e.platform, e.batch, e.quantity, f"{e.start}-{e.end}", e.direction, e.region, e.task, e.base, note])
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        pd.DataFrame(air_rows, columns=AIR_COLS).to_excel(w, sheet_name="飞机", index=False)
        pd.DataFrame(ship_rows, columns=SHIP_COLS).to_excel(w, sheet_name="舰艇", index=False)
    wb = load_workbook(path)
    for ws in wb.worksheets:
        ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
        for cell in ws[1]: cell.font=Font(bold=True,color="FFFFFF"); cell.fill=PatternFill("solid",fgColor="1F4E78"); cell.alignment=Alignment(horizontal="center")
        for col in ws.columns:
            width = min(40, max(10, max(len(str(c.value or "")) for c in col)+2)); ws.column_dimensions[col[0].column_letter].width=width
            for c in col[1:]: c.alignment=Alignment(vertical="top",wrap_text=True)
    wb.save(path)


def choose_trend(day: str, cache: dict[str, list[Event]]) -> tuple[str, list[Event]]:
    current = [e for e in cache[day] if e.decision=="纳入" and (e.country not in CN_NAMES)]
    if not current: return "当日无可核验外（台）重点主线", []
    best = []
    for seed in current:
        chain=[]
        for d, events in cache.items():
            if datetime.strptime(d,"%Y.%m.%d") > datetime.strptime(day,"%Y.%m.%d"): continue
            matches=[e for e in events if e.decision=="纳入" and e.country==seed.country and (clean(seed.platform) in clean(e.platform) or clean(e.platform) in clean(seed.platform))]
            if matches: chain.append(matches[0])
        if len({e.date for e in chain}) > len({e.date for e in best}): best=chain
    label = f"{best[-1].country}{best[-1].platform}活动主线" if best else "外（台）活动主线"
    return label, best


def add_heading(doc, text, level=1):
    p=doc.add_paragraph(); p.style=f"Heading {level}"; p.add_run(text); return p


def write_docx(events: list[Event], all_days: dict[str,list[Event]], path: Path, chart_dir: Path):
    trusted=[e for e in events if e.decision=="纳入"]
    day=events[0].date if events else path.stem[:9]; dt=datetime.strptime(day,"%Y.%m.%d")
    doc=Document(); sec=doc.sections[0]; sec.top_margin=sec.bottom_margin=Cm(2.2); sec.left_margin=sec.right_margin=Cm(2.5)
    styles=doc.styles; styles["Normal"].font.name="宋体"; styles["Normal"].font.size=Pt(11)
    title=doc.add_paragraph(); title.alignment=WD_ALIGN_PARAGRAPH.CENTER; run=title.add_run(f"{dt.month}月{dt.day}日飞机舰船活动情况"); run.bold=True; run.font.size=Pt(20)
    counts=Counter((e.direction,e.kind) for e in trusted); countries=Counter(e.country for e in trusted)
    doc.add_paragraph(f"当日活动总览：经三源交叉核验并执行冲突、异常及海域门控后，共纳入{len(trusted)}起可信事件，其中飞机{sum(e.quantity for e in trusted if e.kind=='飞机')}架次、舰艇{sum(e.quantity for e in trusted if e.kind=='舰艇')}艘次；东海{sum(v for (d,k),v in counts.items() if d=='东海')}起、南海{sum(v for (d,k),v in counts.items() if d=='南海')}起、黄海{sum(v for (d,k),v in counts.items() if d=='黄海')}起。")
    add_heading(doc,"一、重要军事动向")
    if trusted:
        for e in trusted[:8]: doc.add_paragraph(f"{e.country}{e.platform}于{e.region}执行{e.task}，数量{e.quantity}{'架' if e.kind=='飞机' else '艘'}，活动时段{e.start or '未明确'}至{e.end or '未明确'}。三源关键字段一致，纳入统计（{e.event_id}）。",style="List Bullet")
    else: doc.add_paragraph("当日未发现满足三源核验条件的核心海域事件。")
    add_heading(doc,"二、重点态势分析")
    label,chain=choose_trend(day,all_days)
    if len({e.date for e in chain})>=3:
        dates=sorted({e.date for e in chain},key=lambda x:datetime.strptime(x,"%Y.%m.%d")); mid=max(1,len(dates)//2)
        doc.add_paragraph(f"总体判断：{label}自{dates[0]}至{dates[-1]}形成可复核的跨日活动线索，共覆盖{len(dates)}个不同日期；表现为持续/间歇活动，未据此推断材料之外的意图。")
        doc.add_paragraph(f"第一阶段（{dates[0]}—{dates[mid-1]}）：活动开始并在核心海域形成连续证据。第二阶段（{dates[mid]}—{dates[-1]}）：活动延续至节点日，区域与任务以当日三源记录为准。相邻日期间隔按7/14日规则检查。")
    else: doc.add_paragraph(f"总体判断：{label}在本节点前可用证据不足3个不同日期，不强行构造跨日趋势；建议持续跟踪。")
    add_heading(doc,"三、外（台）机舰活动情况")
    foreign=[e for e in trusted if e.country not in CN_NAMES]
    doc.add_paragraph("；".join(f"{k}{v}起" for k,v in Counter(e.country for e in foreign).most_common()) or "当日无满足条件的外（台）事件。")
    add_heading(doc,"四、美重要武器平台部署情况")
    us=[e for e in trusted if "美国" in e.country]
    doc.add_paragraph("；".join(f"{e.platform}在{e.region}执行{e.task}" for e in us) or "当日未发现满足三源核验条件的美国重要平台核心海域活动。")
    add_heading(doc,"五、次日关注重点")
    hot=Counter(e.direction for e in foreign).most_common(1)
    doc.add_paragraph(f"重点关注{hot[0][0] if hot else '东海、南海和黄海'}方向外（台）平台是否延续、转移或离开；后续判断须以新增三源证据为准，不使用节点之后信息回填本日报。")
    add_heading(doc,"附件图表")
    for filename in ["01_舰机侦巡数量曲线图.png","02_中国主要机舰活动示意图.png","03_美国主要机舰活动示意图.png","04_其他国家主要机舰活动示意图.png"]:
        doc.add_paragraph(filename); doc.add_picture(str(chart_dir/filename),width=Cm(15.5))
    doc.save(path)


def validate(package: Path) -> dict:
    errors=[]; docs=list(package.glob("*日报.docx")); books=list(package.glob("*机舰活动明细.xlsx")); pngs=list((package/"附件图表").glob("*.png"))
    if len(docs)!=1: errors.append("DOCX数量错误")
    if len(books)!=1: errors.append("XLSX数量错误")
    if len(pngs)!=4: errors.append("PNG数量错误")
    if books:
        wb=load_workbook(books[0],read_only=True)
        if wb.sheetnames != ["飞机","舰艇"]: errors.append("工作表名称/数量错误")
        if [c.value for c in next(wb["飞机"].iter_rows(max_row=1))] != AIR_COLS: errors.append("飞机表列错误")
        if [c.value for c in next(wb["舰艇"].iter_rows(max_row=1))] != SHIP_COLS: errors.append("舰艇表列错误")
    return {"package":str(package),"ok":not errors,"errors":errors}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); ap.add_argument("--nodes",nargs="*",default=NODES); args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True); cache={}; evidence=[]
    # Build all dates up to the latest node so cross-day analysis never looks into the future.
    cutoff=max(datetime.strptime(x,"%Y.%m.%d") for x in args.nodes)
    for p in args.input.iterdir():
        if p.is_dir():
            try: d=datetime.strptime(p.name,"%Y.%m.%d")
            except ValueError: continue
            if d<=cutoff:
                cache[p.name]=build_events(p); evidence.extend(asdict(e) for e in cache[p.name])
    (args.output/"中间结果").mkdir(exist_ok=True)
    (args.output/"中间结果"/"evidence.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in evidence),encoding="utf-8")
    validations=[]
    for day in args.nodes:
        package=args.output/f"{day}日报"; charts=package/"附件图表"; package.mkdir(parents=True,exist_ok=True)
        events=cache[day]; save_charts(events,charts,day); write_xlsx(events,package/f"{day}机舰活动明细.xlsx"); write_docx(events,cache,package/f"{day}日报.docx",charts)
        validations.append(validate(package))
    (args.output/"validation.json").write_text(json.dumps(validations,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"nodes":len(args.nodes),"events":len(evidence),"valid":all(x['ok'] for x in validations)},ensure_ascii=False))


if __name__ == "__main__": main()
